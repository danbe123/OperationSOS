# api/sos/evalrun.py
"""AI evaluation runner behind `sos eval [--retrieval-only] [--out FILE] [--questions FILE]` (spec section 12).

Retrieval-only mode needs kiwix-serve and an indexed sos.db; full mode also needs llama-server (it is
enabled if it is not already running). Results go to tools/eval/runs/<date>-<model>.jsonl: one row per
question and a final {"summary": ...} row. Exit status is 1 when a gate fails.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable, Optional
from urllib.parse import unquote

from sos import ai
from sos.ai import REFUSAL_TEXT, LlamaClient
from sos.ai_runtime import AiRuntime, enable_ai, model_stem, shutdown
from sos.config import Settings, get_settings
from sos.db import connect
from sos.kiwix import KiwixClient

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUESTIONS = REPO_ROOT / "tools" / "eval" / "questions.jsonl"
RUNS_DIR = REPO_ROOT / "tools" / "eval" / "runs"
KINDS = ("answer", "refuse", "health")
GATES = {"retrieval_at_3": 0.80, "refusal_rate": 0.90, "verbatim_rate": 0.90}
REGRESSION_POINTS = 0.05
AUTHORED_URLS = {"playbook": "/s/{}", "module": "/m/{}", "card": "/medical/card/{}", "page": "/p/{}"}
EventsFn = Callable[[str], AsyncIterator[tuple[str, dict]]]


@dataclass(frozen=True)
class Expected:
    item: str
    path: str = ""


@dataclass
class Question:
    id: str
    question: str
    kind: str
    expected: list[Expected]
    notes: str = ""


def load_questions(path: Path) -> list[Question]:
    out: list[Question] = []
    ids: set[str] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("kind") not in KINDS:
            raise ValueError(f"{path}:{lineno}: kind must be one of {KINDS}")
        if obj["id"] in ids:
            raise ValueError(f"{path}:{lineno}: duplicate id {obj['id']!r}")
        if obj["kind"] != "refuse" and not obj.get("expected"):
            raise ValueError(f"{path}:{lineno}: {obj['kind']} questions need at least one expected entry")
        ids.add(obj["id"])
        out.append(Question(id=obj["id"], question=obj["question"], kind=obj["kind"],
                            expected=[Expected(e["item"], e.get("path", "")) for e in obj.get("expected", [])],
                            notes=obj.get("notes", "")))
    return out


def questions_path(settings: Settings, override: Optional[str]) -> Path:
    if override:
        return Path(override)
    if DEFAULT_QUESTIONS.exists():
        return DEFAULT_QUESTIONS
    return Path(settings.state) / "eval" / "questions.jsonl"        # the box has no repo checkout


def runs_dir(settings: Settings) -> Path:
    return RUNS_DIR if (REPO_ROOT / "tools" / "eval").is_dir() else Path(settings.state) / "eval" / "runs"


# --- expected targets --------------------------------------------------------

def item_kind(conn: sqlite3.Connection, item: str) -> Optional[str]:
    row = conn.execute("SELECT kind FROM library_items WHERE id = ? OR resolved_name = ? ORDER BY id = ? DESC LIMIT 1",
                       (item, item, item)).fetchone()
    return row[0] if row else None


def expected_url(e: Expected, conn: sqlite3.Connection) -> Optional[str]:
    """The overview's URL for an expected target, or None when the item is not in this library at all."""
    prefix, _, slug = e.item.partition(":")
    if prefix in AUTHORED_URLS and slug:
        return AUTHORED_URLS[prefix].format(slug)
    kind = item_kind(conn, e.item)
    if kind is None:
        return None
    item = conn.execute("SELECT id FROM library_items WHERE id = ? OR resolved_name = ? ORDER BY id = ? DESC LIMIT 1",
                        (e.item, e.item, e.item)).fetchone()[0]
    if kind in ("pdf", "epub"):
        m = re.fullmatch(r"p(\d+)", e.path)
        return f"/doc/{item}#page={m.group(1)}" if m else f"/doc/{item}"
    return f"/read/{item}/{e.path}" if e.path else f"/read/{item}"


def normalise_url(url: str) -> str:
    return unquote(url).rstrip("/")


def url_matches(candidate: str, expected: str) -> bool:
    """Exact, or the expected URL is a prefix at a path or fragment boundary (sub-pages, any PDF page)."""
    c, e = normalise_url(candidate), normalise_url(expected)
    return c == e or c.startswith(e + "/") or c.startswith(e + "#")


def is_applicable(q: Question, conn: sqlite3.Connection) -> bool:
    """A question counts only when at least one expected target exists in this library."""
    if q.kind == "refuse":
        return True
    for e in q.expected:
        prefix, _, slug = e.item.partition(":")
        if prefix in AUTHORED_URLS and slug:
            url = AUTHORED_URLS[prefix].format(slug)
            if conn.execute(
                "SELECT 1 FROM fts_docs WHERE url = ? OR substr(url, 1, length(?) + 1) = ? || '#' LIMIT 1",
                (url, url, url),
            ).fetchone():
                return True
        elif conn.execute("SELECT 1 FROM library_items WHERE (id = ? OR resolved_name = ?) AND available = 1",
                          (e.item, e.item)).fetchone():
            return True
    return False


# --- running -----------------------------------------------------------------

@dataclass
class EvalContext:
    conn: sqlite3.Connection
    events: EventsFn
    retrieval_only: bool
    model: str
    count_tokens: Callable[[str], Awaitable[int]]
    peak_rss: Callable[[], Optional[float]]
    close: Optional[Callable[[], Awaitable[None]]] = None


async def run_question(q: Question, ctx: EvalContext) -> dict:
    row: dict = {"id": q.id, "kind": q.kind, "question": q.question, "applicable": is_applicable(q, ctx.conn),
                 "passages": [], "verbatim_url": None, "answer": None, "grounded": None, "citations": [],
                 "error": None, "ttft_s": None, "tok_s": None, "peak_rss_mb": None,
                 "hit": None, "verbatim_hit": None, "refused": None}
    t0 = time.monotonic()
    first: Optional[float] = None
    try:
        async for name, data in ctx.events(q.question):
            if name == "verbatim":
                row["verbatim_url"] = data["url"]
            elif name == "retrieving":
                row["passages"] = [{"n": p["n"], "title": p["title"], "url": p["url"]} for p in data["passages"]]
            elif name == "token":
                first = first or time.monotonic()
            elif name == "done":
                row["answer"], row["grounded"] = data["answer"], data["grounded"]
                row["citations"] = [c["n"] for c in data["citations"]]
            elif name == "error":
                row["error"] = data["code"]
    except Exception as exc:                       # one bad question must not abort a two-hour run
        row["error"] = f"exception: {exc}"
    end = time.monotonic()
    if first is not None:
        row["ttft_s"] = round(first - t0, 2)
        if row["answer"]:
            n = await ctx.count_tokens(row["answer"])
            row["tok_s"] = round(n / max(end - first, 1e-3), 1)
    row["peak_rss_mb"] = ctx.peak_rss()
    expected = [u for u in (expected_url(e, ctx.conn) for e in q.expected) if u]
    if q.kind in ("answer", "health"):
        row["hit"] = any(url_matches(p["url"], u) for p in row["passages"][:3] for u in expected)
    if q.kind == "health":
        row["verbatim_hit"] = row["verbatim_url"] is not None and (
            not expected or any(url_matches(row["verbatim_url"], u) for u in expected))
    if q.kind == "refuse":
        if ctx.retrieval_only:
            row["refused"] = len(row["passages"]) == 0
        else:
            row["refused"] = row["answer"] is not None and (
                row["answer"].startswith(REFUSAL_TEXT) or not row["grounded"])
    return row


def _flag(row: dict) -> str:
    if not row["applicable"]:
        return "skip"
    if row["error"]:
        return "ERROR"
    if row["kind"] == "refuse":
        return "refused" if row["refused"] else "ANSWERED"
    if row["kind"] == "health":
        return ("hit" if row["hit"] else "MISS") + ("+verb" if row["verbatim_hit"] else "-verb")
    return "hit" if row["hit"] else "MISS"


async def run_questions(questions: list[Question], ctx: EvalContext) -> list[dict]:
    rows: list[dict] = []
    for i, q in enumerate(questions, 1):
        row = await run_question(q, ctx)
        rows.append(row)
        print(f"[{i:3d}/{len(questions)}] {q.id:<6} {_flag(row):<10} {q.question[:60]}", file=sys.stderr)
    return rows


# --- metrics and gates --------------------------------------------------------

def summarise(rows: list[dict], retrieval_only: bool) -> dict:
    def rate(num: int, den: int) -> Optional[float]:
        return round(num / den, 3) if den else None

    applicable = [r for r in rows if r["applicable"]]
    retrievable = [r for r in applicable if r["kind"] in ("answer", "health")]
    health = [r for r in applicable if r["kind"] == "health"]
    answers = [r for r in applicable if r["kind"] == "answer"]
    refuse = [r for r in rows if r["kind"] == "refuse"]
    summary = {
        "questions": len(rows), "applicable": len(applicable),
        "skipped": [r["id"] for r in rows if not r["applicable"]],
        "retrieval_at_3": rate(sum(1 for r in retrievable if r["hit"]), len(retrievable)),
        "verbatim_rate": rate(sum(1 for r in health if r["verbatim_hit"]), len(health)),
        "refusal_rate": rate(sum(1 for r in refuse if r["refused"]), len(refuse)),
        "grounded_rate": None if retrieval_only else rate(sum(1 for r in answers if r["grounded"]), len(answers)),
        "errors": sum(1 for r in rows if r["error"]),
    }
    if not retrieval_only:
        ttft = [r["ttft_s"] for r in rows if r["ttft_s"] is not None]
        toks = [r["tok_s"] for r in rows if r["tok_s"]]
        rss = [r["peak_rss_mb"] for r in rows if r["peak_rss_mb"]]
        summary["median_ttft_s"] = round(statistics.median(ttft), 1) if ttft else None
        summary["mean_tok_s"] = round(statistics.mean(toks), 1) if toks else None
        summary["peak_rss_mb"] = max(rss) if rss else None
    return summary


def check_gates(summary: dict, previous: Optional[dict], retrieval_only: bool) -> list[str]:
    """Spec gates; the refusal gate needs a model, so retrieval-only mode reports it without gating."""
    gated = ["retrieval_at_3", "verbatim_rate"] + ([] if retrieval_only else ["refusal_rate"])
    regression = gated + ([] if retrieval_only else ["grounded_rate"])
    failures: list[str] = []
    for name in gated:
        value = summary.get(name)
        if value is not None and value < GATES[name]:
            failures.append(f"{name} {value:.2f} is below the gate {GATES[name]:.2f}")
    for name in regression:
        value, prev = summary.get(name), (previous or {}).get(name)
        if value is not None and prev is not None and value < prev - REGRESSION_POINTS:
            failures.append(f"{name} {value:.2f} is more than {REGRESSION_POINTS:.2f} below the previous run ({prev:.2f})")
    return failures


# --- run files ----------------------------------------------------------------

def run_path(runs: Path, model: str, out: Optional[str]) -> Path:
    if out:
        return Path(out)
    runs.mkdir(parents=True, exist_ok=True)
    base = runs / f"{date.today().isoformat()}-{model}.jsonl"
    path, n = base, 2
    while path.exists():
        path = base.with_name(f"{base.stem}-{n}.jsonl")
        n += 1
    return path


def previous_summary(runs: Path, model: str, exclude: Path) -> Optional[dict]:
    if not runs.is_dir():
        return None
    files = sorted(f for f in runs.glob(f"*-{model}*.jsonl") if f.resolve() != exclude.resolve())
    for f in reversed(files):
        for line in reversed(f.read_text(encoding="utf-8").splitlines()):
            if line.strip():
                return json.loads(line).get("summary")
    return None


def write_run(path: Path, rows: list[dict], summary: dict, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.write(json.dumps({"summary": summary, **meta}, ensure_ascii=False) + "\n")


def print_summary(summary: dict, failures: list[str], path: Path, retrieval_only: bool) -> None:
    def fmt(v: Optional[float]) -> str:
        return "n/a" if v is None else f"{v:.2f}"

    mode = "retrieval-only" if retrieval_only else "full"
    print(f"sos eval ({mode}): {summary['questions']} questions, {summary['applicable']} applicable, "
          f"{len(summary['skipped'])} skipped, {summary['errors']} errors")
    print(f"  retrieval@3    {fmt(summary['retrieval_at_3'])}  (gate {GATES['retrieval_at_3']:.2f})")
    print(f"  verbatim rate  {fmt(summary['verbatim_rate'])}  (gate {GATES['verbatim_rate']:.2f})")
    note = "(informational in retrieval-only mode)" if retrieval_only else f"(gate {GATES['refusal_rate']:.2f})"
    print(f"  refusal rate   {fmt(summary['refusal_rate'])}  {note}")
    print(f"  grounded rate  {fmt(summary['grounded_rate'])}")
    if not retrieval_only:
        print(f"  median TTFT    {summary['median_ttft_s']} s   mean {summary['mean_tok_s']} tok/s   "
              f"peak RSS {summary['peak_rss_mb']} MB")
    if summary["skipped"]:
        print("  skipped (not in this library): " + ", ".join(summary["skipped"]))
    for failure in failures:
        print(f"  FAIL {failure}")
    print("GATES: " + ("PASS" if not failures else "FAIL"))
    print(f"run written to {path}")


# --- contexts -----------------------------------------------------------------

def retrieval_only_events(conn: sqlite3.Connection, kiwix: KiwixClient, settings: Settings) -> EventsFn:
    async def events(question: str) -> AsyncIterator[tuple[str, dict]]:
        tokens = ai.reduce_query(question)
        query = " ".join(tokens)
        verbatim = await ai.verbatim_block(query, conn, kiwix) if tokens else None
        if verbatim is not None:
            yield "verbatim", asdict(verbatim)
        passages = await ai.retrieve(tokens, conn, kiwix, settings) if tokens else []
        passages = await ai.prefer_health_source(passages, verbatim, tokens, conn, kiwix)
        yield "retrieving", {"query": query, "passages": [asdict(p) for p in passages]}

    return events


def peak_rss_mb(pid: Optional[int]) -> Optional[float]:
    if not pid:
        return None
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmHWM:"):
                return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError, IndexError):
        return None
    return None


def llama_pid(rt: Optional[AiRuntime]) -> Optional[int]:
    if rt is not None and rt.process is not None:
        return rt.process.pid
    try:
        out = subprocess.run(["pgrep", "-x", "llama-server"], capture_output=True, text=True, timeout=5).stdout.split()
        return int(out[0]) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


async def build_context(settings: Settings, retrieval_only: bool) -> EvalContext:
    conn = connect(Path(settings.state) / "sos.db")
    kiwix = KiwixClient(settings.kiwix_url)
    async def close_retrieval():
        await kiwix.aclose()
        conn.close()

    if retrieval_only:
        async def estimate(text: str) -> int:
            return ai.estimate_tokens(text)

        return EvalContext(conn=conn, events=retrieval_only_events(conn, kiwix, settings), retrieval_only=True,
                           model="retrieval-only", count_tokens=estimate, peak_rss=lambda: None, close=close_retrieval)
    llama = LlamaClient(settings.llama_url)
    rt = AiRuntime(settings=settings, llama=llama)
    if await llama.health():
        rt.state = "ready"
    else:
        await enable_ai(rt, conn, wait=True)
        if rt.state != "ready":
            raise SystemExit(f"sos eval: the AI is not ready: {rt.message}")
    model = await llama.model_name() or model_stem(settings)

    def events(question: str) -> AsyncIterator[tuple[str, dict]]:
        return ai.answer_events(question, [], conn, kiwix, llama, settings)

    async def close_full():
        await shutdown(rt)
        await close_retrieval()

    return EvalContext(conn=conn, events=events, retrieval_only=False, model=model, count_tokens=llama.tokenize,
                       peak_rss=lambda: peak_rss_mb(llama_pid(rt)), close=close_full)


async def run(questions_file: Optional[str], retrieval_only: bool, out: Optional[str]) -> int:
    settings = get_settings()
    questions = load_questions(questions_path(settings, questions_file))
    ctx = await build_context(settings, retrieval_only)
    try:
        rows = await run_questions(questions, ctx)
    finally:
        if ctx.close is not None:
            await ctx.close()
    summary = summarise(rows, retrieval_only)
    path = run_path(runs_dir(settings), ctx.model, out)
    previous = previous_summary(path.parent, ctx.model, path)
    failures = check_gates(summary, previous, retrieval_only)
    write_run(path, rows, summary, {"mode": "retrieval-only" if retrieval_only else "full", "model": ctx.model,
                                    "date": date.today().isoformat(), "failures": failures, "previous": previous})
    print_summary(summary, failures, path, retrieval_only)
    return 1 if failures else 0


def run_from_namespace(args: argparse.Namespace) -> int:
    return asyncio.run(run(getattr(args, "questions", None), bool(getattr(args, "retrieval_only", False)),
                           getattr(args, "out", None)))


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sos eval", description="Run the AI evaluation question set.")
    parser.add_argument("--retrieval-only", action="store_true", help="no model: retrieval@3 and verbatim rate only")
    parser.add_argument("--out", help="write the run file here instead of tools/eval/runs/<date>-<model>.jsonl")
    parser.add_argument("--questions", help="question file (default tools/eval/questions.jsonl)")
    return run_from_namespace(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(run_cli())
