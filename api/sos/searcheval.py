# api/sos/searcheval.py
"""Search-quality benchmark behind `sos eval-search` and `sos eval-compare`.

The gold sets live in tools/eval/search/*.jsonl (schema in that folder's README). Each query is run through
`sos.search.search()` -- the very call the API makes -- straight from Python, in keyword-only mode
(`semantic=None`), with the meaning layer on (the `Semantic` object main.py builds), or both, and scored
against the acceptable pages. Nothing here writes to the database: it is opened read-only and immutable, and
the results cache is never used.

Metrics are for one page per query. The `expected` entries of a row are alternatives (any one answers the
question), so the first result that matches any of them is the relevant one; a later result matching another
alternative is neither rewarded nor penalised:

    hit@k      1 when the first match is in the top k
    MRR@10     1 / rank of the first match, 0 when it is not in the top 10
    nDCG@10    1 / log2(rank + 1) of the first match, 0 when it is not in the top 10 (binary relevance,
               the ideal ranking being the match at rank 1)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sqlite3
import statistics
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote

from sos import evalrun
from sos.books import content_url, reader_url
from sos.evalrun import Expected, url_matches

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD_DIR = REPO_ROOT / "tools" / "eval" / "search"
SURVIVOR_ZIM = "survivorlibrary.com_en_all"
GUTENBERG_ZIM = "gutenberg_en_all"
TOP = 10                       # the depth every metric and every recorded ranking stops at
KS = (1, 3, 5, 10)
MODES = ("off", "on")          # keyword only, meaning layer on
ALL = "ALL"
MAX_ATTEMPTS = 3               # a search that timed out (partial) or lost its embedding is asked again
RETRY_PAUSE_S = 1.0
STUCK_AFTER = 3                # this many queries in a row still partial after retries: the partial is the
                               # environment's (a Kiwix class that always errors), and asking again is pointless
REQUIRED = ("id", "query", "expected", "set")
SEARCH_UNINDEXED_OK = (SURVIVOR_ZIM, GUTENBERG_ZIM)   # found through the meaning collections, not the keyword search
EXPECTED_KEYS = ("url", "item", "gutenberg", "survivor")

SearchFn = Callable[[str, str], Awaitable[dict]]     # (query, mode) -> the payload search() returns


# --- metrics -------------------------------------------------------------------------------------------------

def first_rank(urls: Iterable[str], expected: Iterable[str]) -> Optional[int]:
    """The 1-based position of the first result that is any of the expected pages, or None when none is."""
    wanted = [e for e in expected if e]
    for position, url in enumerate(urls, 1):
        if any(url_matches(url or "", e) for e in wanted):
            return position
    return None


def hit_at(rank: Optional[int], k: int) -> float:
    return 1.0 if rank is not None and rank <= k else 0.0


def reciprocal_rank(rank: Optional[int], depth: int = TOP) -> float:
    return 1.0 / rank if rank is not None and rank <= depth else 0.0


def ndcg(rank: Optional[int], depth: int = TOP) -> float:
    """Binary-relevance nDCG@depth of a ranking whose one relevant result is at `rank`."""
    return 1.0 / math.log2(rank + 1) if rank is not None and rank <= depth else 0.0


def percentile(values: list[float], pct: float) -> Optional[float]:
    """Nearest-rank percentile: deterministic, and always a value that was really measured."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(pct / 100.0 * len(ordered)) - 1)
    return ordered[min(index, len(ordered) - 1)]


def metrics(records: list[dict]) -> dict:
    """The metrics of a group of per-query records (each has `rank` and `latency_ms`)."""
    n = len(records)
    out: dict[str, Any] = {"n": n}
    if not n:
        return out
    ranks = [r.get("rank") for r in records]
    for k in KS:
        out[f"hit@{k}"] = sum(hit_at(r, k) for r in ranks) / n
    out["mrr@10"] = sum(reciprocal_rank(r) for r in ranks) / n
    out["ndcg@10"] = sum(ndcg(r) for r in ranks) / n
    lat = [float(r["latency_ms"]) for r in records if r.get("latency_ms") is not None]
    out["lat_median_ms"] = statistics.median(lat) if lat else None
    out["lat_p95_ms"] = percentile(lat, 95)
    return out


def bucket(rank: Optional[int]) -> str:
    """The outcome a searcher experiences: first, the top three, the first page, or nothing."""
    if rank is None or rank > TOP:
        return "miss"
    return "top1" if rank == 1 else "top3" if rank <= 3 else "top10"


def summarise_records(queries: dict[str, dict], records: dict[str, dict]) -> dict[str, dict]:
    """Metrics per set, per set/group (when a set has groups) and overall, for one mode's records."""
    groups: dict[str, list[dict]] = {}
    for qid, rec in records.items():
        meta = queries.get(qid, {})
        name = meta.get("set", "?")
        groups.setdefault(name, []).append(rec)
        if meta.get("group"):
            groups.setdefault(f"{name}/{meta['group']}", []).append(rec)
        groups.setdefault(ALL, []).append(rec)
    return {name: metrics(recs) for name, recs in sorted(groups.items(), key=lambda kv: (kv[0] == ALL, kv[0]))}


def rescued_and_regressed(queries: dict[str, dict], off: dict[str, dict], on: dict[str, dict]) -> dict[str, list[dict]]:
    """Queries the meaning layer newly put in the top ten (rescued) or newly lost from it (regressed)."""
    rescued: list[dict] = []
    regressed: list[dict] = []
    for qid in sorted(set(off) & set(on)):
        was, now = hit_at(off[qid].get("rank"), TOP), hit_at(on[qid].get("rank"), TOP)
        row = {"id": qid, "set": queries.get(qid, {}).get("set"), "query": queries.get(qid, {}).get("query"),
               "rank_off": off[qid].get("rank"), "rank_on": on[qid].get("rank")}
        if now and not was:
            rescued.append(row)
        elif was and not now:
            regressed.append(row)
    return {"rescued": rescued, "regressed": regressed}


# --- gold files ------------------------------------------------------------------------------------------------

@dataclass
class GoldRow:
    id: str
    query: str
    expected: list[dict]
    set: str
    group: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    source: str = ""            # the file:line it came from, for messages


def gold_files(gold_dir: Path) -> list[Path]:
    return sorted(Path(gold_dir).glob("*.jsonl"))


def load_gold_file(path: Path) -> tuple[list[GoldRow], list[str]]:
    """The rows of one gold file and every problem with its shape. Shape only: whether the expected pages
    exist is `check_expected`'s question, which needs the real data."""
    rows: list[GoldRow] = []
    problems: list[str] = []
    seen: set[str] = set()
    name = path.stem
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        where = f"{path.name}:{lineno}"
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"{where}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(obj, dict):
            problems.append(f"{where}: a row must be a JSON object")
            continue
        missing = [k for k in REQUIRED if k not in obj]
        if missing:
            problems.append(f"{where}: missing {', '.join(missing)}")
            continue
        rid, query, expected = obj["id"], obj["query"], obj["expected"]
        if not isinstance(rid, str) or not rid.strip():
            problems.append(f"{where}: id must be a non-empty string")
            continue
        if not isinstance(query, str) or not query.strip():
            problems.append(f"{where}: {rid}: query must be a non-empty string")
            continue
        if obj["set"] != name:
            problems.append(f"{where}: {rid}: set is {obj['set']!r} but the file is {name}.jsonl")
        if rid in seen:
            problems.append(f"{where}: duplicate id {rid!r}")
            continue
        seen.add(rid)
        if not isinstance(expected, list) or not expected:
            problems.append(f"{where}: {rid}: expected must be a non-empty list")
            continue
        bad = [e for e in expected if not isinstance(e, dict) or sum(k in e for k in EXPECTED_KEYS) != 1]
        if bad:
            problems.append(f"{where}: {rid}: each expected entry needs exactly one of {', '.join(EXPECTED_KEYS)}: {bad[0]!r}")
            continue
        tags = obj.get("tags") or []
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            problems.append(f"{where}: {rid}: tags must be a list of strings")
            tags = []
        rows.append(GoldRow(id=rid, query=query, expected=expected, set=str(obj["set"]), group=str(obj.get("group") or ""),
                            tags=tags, notes=str(obj.get("notes") or ""), source=where))
    return rows, problems


def load_gold(gold_dir: Path, names: Optional[list[str]] = None) -> tuple[list[GoldRow], list[str]]:
    """Every row of the named sets (all when none are named), ids unique across the whole folder."""
    files = gold_files(gold_dir)
    available = [f.stem for f in files]
    problems: list[str] = []
    for name in names or []:
        if name not in available:
            problems.append(f"no gold set named {name!r} in {gold_dir} (have: {', '.join(available) or 'none'})")
    rows: list[GoldRow] = []
    ids: dict[str, str] = {}
    for f in files:
        if names and f.stem not in names:
            continue
        got, bad = load_gold_file(f)
        problems.extend(bad)
        for row in got:
            if row.id in ids:
                problems.append(f"{row.source}: duplicate id {row.id!r} (also {ids[row.id]})")
                continue
            ids[row.id] = row.source
            rows.append(row)
    return rows, problems


def resolve_expected(entry: dict, conn: sqlite3.Connection) -> Optional[str]:
    """The URL an expected entry stands for, or None when its item is not in this library at all."""
    if "url" in entry:
        return str(entry["url"])
    if "gutenberg" in entry:
        return f"/book/gutenberg/{int(entry['gutenberg'])}"
    if "survivor" in entry:
        return content_url(SURVIVOR_ZIM, f"www.survivorlibrary.com/library/{entry['survivor']}.pdf")
    return evalrun.expected_url(Expected(str(entry["item"]), str(entry.get("path", ""))), conn)


def resolve_urls(entry: dict, conn: sqlite3.Connection) -> list[str]:
    """Every URL search() may give for an expected entry. A Survivor Library book is one PDF that the meaning
    layer links through the Kiwix content route and a keyword hit would link through the reader route."""
    url = resolve_expected(entry, conn)
    if url is None:
        return []
    if "survivor" in entry:
        return [url, reader_url(SURVIVOR_ZIM, f"www.survivorlibrary.com/library/{entry['survivor']}.pdf")]
    return [url]


# --- checking the gold against the real data -------------------------------------------------------------------

class ZimChecker:
    """Does a ZIM have this entry, is it the article itself rather than a redirect to it, and does search()
    look in that ZIM at all? One open archive per ZIM."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._archives: dict[str, Any] = {}

    def _archive(self, zim: str):
        if zim not in self._archives:
            row = self.conn.execute("SELECT local_path FROM library_items WHERE id=? AND available=1", (zim,)).fetchone()
            if row is None or not row[0]:
                self._archives[zim] = None
            else:
                from libzim.reader import Archive
                try:
                    self._archives[zim] = Archive(str(row[0]))
                except (OSError, RuntimeError):
                    self._archives[zim] = None
        return self._archives[zim]

    def check(self, zim: str, path: str) -> Optional[str]:
        """`path` empty means the ZIM as a whole (any page of it is a hit)."""
        archive = self._archive(zim)
        if archive is None:
            return f"{zim} is not an available ZIM in this library"
        if zim not in SEARCH_UNINDEXED_OK:
            row = self.conn.execute("SELECT fts FROM library_items WHERE id=?", (zim,)).fetchone()
            if row is not None and not row[0]:
                return f"{zim} has no full-text index (fts=0): search() never looks in it, so it can never be a hit"
        if not path:
            return None
        if not archive.has_entry_by_path(path):
            return f"{zim} has no entry {path!r}"
        entry = archive.get_entry_by_path(path)
        if entry.is_redirect:
            return f"{zim}:{path!r} is a redirect to {entry.get_redirect_entry().path!r}; expect the article itself"
        return None


class DocUrls:
    """The url column of fts_docs, read once: an authored page or a document page exists when a row has its URL
    or its URL with a #fragment."""

    def __init__(self, conn: sqlite3.Connection):
        self.urls = {r[0] for r in conn.execute("SELECT url FROM fts_docs")}
        self.bases = {u.split("#", 1)[0] for u in self.urls}

    def has(self, url: str) -> bool:
        return url in self.urls or url in self.bases


def check_expected(entry: dict, conn: sqlite3.Connection, docs: DocUrls, zims: Any) -> Optional[str]:
    """None when the expected page is really in this library, otherwise what is wrong with it. `zims` is a
    ZimChecker (or anything with .check(zim, path))."""
    if "gutenberg" in entry:
        row = conn.execute("SELECT title, author FROM books WHERE zim=? AND id=?", (GUTENBERG_ZIM, entry["gutenberg"])).fetchone()
        if row is None:
            return f"Gutenberg id {entry['gutenberg']} is not in the books table"
        if entry.get("title") is not None and entry["title"] != row[0]:
            return f"Gutenberg {entry['gutenberg']} is titled {row[0]!r}, not {entry['title']!r}"
        return None
    if "survivor" in entry:
        return zims.check(SURVIVOR_ZIM, f"www.survivorlibrary.com/library/{entry['survivor']}.pdf")
    url = resolve_expected(entry, conn)
    if url is None:
        return f"{entry.get('item')!r} is not a known item in this library"
    if url.startswith(("/p/", "/m/", "/medical/card/", "/s/")):
        return None if docs.has(url) else f"no authored page at {url}"
    if url.startswith("/doc/"):
        return None if docs.has(url) else f"no converted document at {url}"
    match = re.fullmatch(r"/book/gutenberg/(\d+)", url)
    if match:
        return None if conn.execute("SELECT 1 FROM books WHERE zim=? AND id=?", (GUTENBERG_ZIM, int(match.group(1)))).fetchone() \
            else f"Gutenberg id {match.group(1)} is not in the books table"
    match = re.fullmatch(r"/read/([^/]+)(?:/(.+))?", url)
    if match:
        return zims.check(match.group(1), unquote(match.group(2) or ""))
    return f"cannot check {url!r} (unrecognised URL shape)"


def validate_gold(gold_dir: Path, conn: sqlite3.Connection, zims: Any = None, names: Optional[list[str]] = None) -> tuple[list[GoldRow], list[str]]:
    """Every gold row loaded and every problem found: bad JSON or shape, duplicate ids or queries, and any
    expected page that is not in the real database or ZIM."""
    rows, problems = load_gold(gold_dir, names)
    docs = DocUrls(conn)
    zims = zims if zims is not None else ZimChecker(conn)
    queries: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row.set, " ".join(row.query.lower().split()))
        if key in queries:
            problems.append(f"{row.source}: {row.id}: same query as {queries[key]} in {row.set}")
        queries[key] = row.id
        for entry in row.expected:
            bad = check_expected(entry, conn, docs, zims)
            if bad:
                problems.append(f"{row.source}: {row.id}: {bad}")
    return rows, problems


# --- running ---------------------------------------------------------------------------------------------------

def top_rows(payload: dict, depth: int = TOP) -> list[dict]:
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "source": r.get("source", ""), "via": r.get("via", "")}
            for r in (payload.get("results") or [])[:depth]]


async def run_one(row: GoldRow, expected_urls: list[str], mode: str, search_fn: SearchFn,
                  clock: Callable[[], float] = time.perf_counter, pause: float = RETRY_PAUSE_S,
                  retry_partial: bool = True) -> dict:
    """One query in one mode. A search that came back partial (a Kiwix class timed out) or with its meaning
    layer silently dark (the embedding call failed) is a measurement of the machine, not of the search: it is
    asked again, up to MAX_ATTEMPTS times, and the record says how many retries it took and whether it ended
    clean. `retry_partial` is off when partial answers are known to be permanent here (see run_rows)."""
    attempts = 0
    while True:
        attempts += 1
        started = clock()
        payload = await search_fn(row.query, mode)
        elapsed = (clock() - started) * 1000.0
        partial = bool(payload.get("partial"))
        semantic_ok = payload.get("semantic_ok", True) if mode == "on" else None
        clean = (not partial or not retry_partial) and semantic_ok is not False
        if clean or attempts >= MAX_ATTEMPTS:
            break
        if pause:
            await asyncio.sleep(pause)
    results = payload.get("results") or []
    return {"rank": first_rank((r.get("url", "") for r in results), expected_urls), "latency_ms": round(elapsed, 1),
            "partial": partial, "retries": attempts - 1, "semantic_ok": semantic_ok, "n_results": len(results),
            "top10": top_rows(payload)}


async def run_rows(rows: list[GoldRow], expected: dict[str, list[str]], modes: list[str], search_fn: SearchFn, *,
                   clock: Callable[[], float] = time.perf_counter, pause: float = RETRY_PAUSE_S,
                   progress: Optional[Callable[[int, int, GoldRow, dict], None]] = None) -> dict[str, dict[str, dict]]:
    """{mode: {id: record}}. With two modes the order alternates query by query, so neither mode is always the
    one that finds Kiwix's caches cold or warm. When STUCK_AFTER queries in a row stay partial after their
    retries, a Kiwix class is failing for good on this machine (the baseline meets one: a multilingual ZIM
    makes its whole class answer HTTP 400), so partial answers stop being retried; the records still say partial."""
    out: dict[str, dict[str, dict]] = {m: {} for m in modes}
    stuck = {m: 0 for m in modes}
    for i, row in enumerate(rows):
        order = modes if i % 2 == 0 else list(reversed(modes))
        for mode in order:
            rec = await run_one(row, expected[row.id], mode, search_fn, clock, pause, retry_partial=stuck[mode] < STUCK_AFTER)
            stuck[mode] = stuck[mode] + 1 if rec["partial"] else 0
            out[mode][row.id] = rec
            if progress:
                progress(i + 1, len(rows), row, {"mode": mode, **rec})
    return out


def build_document(rows: list[GoldRow], expected: dict[str, list[str]], runs: dict[str, dict[str, dict]], meta: dict) -> dict:
    queries = {r.id: {"set": r.set, "group": r.group, "query": r.query, "expected": expected[r.id], "tags": r.tags}
               for r in rows}
    summary = {mode: summarise_records(queries, recs) for mode, recs in runs.items()}
    doc: dict[str, Any] = {"meta": meta, "queries": queries, "runs": runs, "summary": summary}
    if "off" in runs and "on" in runs:
        doc["changes"] = rescued_and_regressed(queries, runs["off"], runs["on"])
    return doc


def git_state() -> dict:
    try:
        head = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", "api/sos"], capture_output=True,
                                    text=True, timeout=10).stdout.strip())
        return {"commit": head, "code_dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {}


def write_json(path: Path, doc: dict) -> None:
    """Whole file or nothing: written beside the target and renamed, so an interrupted run leaves no half file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)


def compact(doc: dict, keep_hit: int = 3, keep: int = 5) -> dict:
    """The same document with each ranking cut short, for a run file that has to stay small: a query found at
    rank 1 keeps its first `keep_hit` rows, any other its first `keep` rows plus the matching row when it sits
    lower in the top ten. What matters when reading a run later is what was returned instead of the answer."""
    for recs in doc.get("runs", {}).values():
        for rec in recs.values():
            top, rank = rec["top10"], rec.get("rank")
            if rank == 1:
                rec["top10"] = top[:keep_hit]
            else:
                rec["top10"] = top[:keep] + ([top[rank - 1]] if rank and keep < rank <= len(top) else [])
    doc.setdefault("meta", {})["compact"] = {"keep_hit": keep_hit, "keep": keep}
    return doc


# --- reports ---------------------------------------------------------------------------------------------------

COLUMNS = (("n", "n", "{:d}"), ("hit@1", "hit@1", "{:.3f}"), ("hit@3", "hit@3", "{:.3f}"), ("hit@5", "hit@5", "{:.3f}"),
           ("hit@10", "hit@10", "{:.3f}"), ("mrr@10", "MRR", "{:.3f}"), ("ndcg@10", "nDCG", "{:.3f}"),
           ("lat_median_ms", "p50 ms", "{:.0f}"), ("lat_p95_ms", "p95 ms", "{:.0f}"))


def _cell(value: Any, fmt: str) -> str:
    return "-" if value is None else fmt.format(value)


def format_table(summary: dict[str, dict]) -> str:
    head = ["set"] + [c[1] for c in COLUMNS]
    body = [[name] + [_cell(m.get(key), fmt) for key, _label, fmt in COLUMNS] for name, m in summary.items()]
    widths = [max(len(r[i]) for r in [head] + body) for i in range(len(head))]
    lines = ["  ".join(c.ljust(widths[i]) if i == 0 else c.rjust(widths[i]) for i, c in enumerate(r)) for r in [head] + body]
    return "\n".join([lines[0], "  ".join("-" * w for w in widths)] + lines[1:])


def format_report(doc: dict) -> str:
    out: list[str] = []
    for mode, summary in doc["summary"].items():
        label = "keyword only (semantic off)" if mode == "off" else "meaning layer on"
        out.append(f"== {label} ==")
        out.append(format_table(summary))
        out.append("")
    changes = doc.get("changes")
    if changes:
        out.append(f"meaning layer: rescued {len(changes['rescued'])} (newly in the top {TOP}), regressed {len(changes['regressed'])} (newly out of it)")
        for kind in ("rescued", "regressed"):
            for c in changes[kind]:
                out.append(f"  {kind:<9} {c['id']:<28} off={c['rank_off']} on={c['rank_on']}  {c['query']}")
    unclean = [(mode, qid) for mode, recs in doc["runs"].items() for qid, r in recs.items()
               if r.get("partial") or r.get("semantic_ok") is False]
    if unclean:
        out.append(f"warning: {len(unclean)} run(s) stayed partial or lost the meaning layer after {MAX_ATTEMPTS} attempts: "
                   + ", ".join(f"{q} [{m}]" for m, q in unclean[:10]))
    return "\n".join(out)


def format_compare(a: dict, b: dict, name_a: str = "A", name_b: str = "B") -> str:
    """Per mode, per set and metric: a, b and b - a; then the queries whose outcome bucket changed."""
    out: list[str] = []
    for mode in [m for m in MODES if m in a["runs"] and m in b["runs"]]:
        sa, sb = a["summary"][mode], b["summary"][mode]
        out.append(f"== mode {mode}: {name_a} -> {name_b} ==")
        cols = [c for c in COLUMNS if c[0] != "n"]
        head = ["set", "n"] + [c[1] for c in cols]
        rows = []
        for name in [s for s in sb if s in sa]:
            ma, mb = sa[name], sb[name]
            cells = [name, str(mb["n"]) if ma["n"] == mb["n"] else f"{ma['n']}->{mb['n']}"]
            for key, _label, fmt in cols:
                x, y = ma.get(key), mb.get(key)
                if x is None or y is None:
                    cells.append("-")
                else:
                    d = y - x
                    cells.append(f"{fmt.format(y)} ({'+' if d >= 0 else '-'}{fmt.format(abs(d))})")
            rows.append(cells)
        widths = [max(len(r[i]) for r in [head] + rows) for i in range(len(head))]
        for r in [head, ["-" * w for w in widths]] + rows:
            out.append("  ".join(c.ljust(widths[i]) if i == 0 else c.rjust(widths[i]) for i, c in enumerate(r)))
        shared = sorted(set(a["runs"][mode]) & set(b["runs"][mode]))
        moved = [(q, a["runs"][mode][q].get("rank"), b["runs"][mode][q].get("rank")) for q in shared
                 if bucket(a["runs"][mode][q].get("rank")) != bucket(b["runs"][mode][q].get("rank"))]
        better = [m for m in moved if _score(m[2]) > _score(m[1])]
        worse = [m for m in moved if _score(m[2]) < _score(m[1])]
        out.append(f"  outcome changed for {len(moved)} of {len(shared)} shared queries: {len(better)} better, {len(worse)} worse")
        queries = {**a["queries"], **b["queries"]}
        for label, group in (("better", better), ("worse ", worse)):
            for q, ra, rb in group:
                out.append(f"    {label} {q:<28} {ra if ra else '-'} -> {rb if rb else '-'}  {queries.get(q, {}).get('query', '')}")
        only_a = sorted(set(a["runs"][mode]) - set(b["runs"][mode]))
        only_b = sorted(set(b["runs"][mode]) - set(a["runs"][mode]))
        if only_a or only_b:
            out.append(f"  queries only in {name_a}: {len(only_a)}; only in {name_b}: {len(only_b)}")
        out.append("")
    if not out:
        out.append("the two files have no mode in common")
    return "\n".join(out)


def _score(rank: Optional[int]) -> int:
    return {"top1": 4, "top3": 3, "top10": 2, "miss": 1}[bucket(rank)]


# --- the real thing --------------------------------------------------------------------------------------------

def open_readonly(path: Path) -> sqlite3.Connection:
    """The database opened so that it cannot be written to, and so that not even a -wal or -shm file is created
    beside it (mode=ro alone still makes those for a WAL database). Immutable is right for a benchmark: nobody
    is writing to the copy being measured. The one exception is a database with unmerged changes in a -wal file,
    which immutable would silently ignore: that is opened plain read-only so they are read."""
    wal = Path(f"{path}-wal")
    unmerged = wal.exists() and wal.stat().st_size > 0
    conn = sqlite3.connect(f"file:{path}?mode=ro{'' if unmerged else '&immutable=1'}", uri=True, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def semantic_sizes(semantic) -> dict:
    sizes: dict[str, Optional[int]] = {}
    for name, getter in (("docs", "index"), ("household", "household_index"), ("wikipedia", "wikipedia_store")):
        try:
            store = getattr(semantic, getter)()
            sizes[name] = len(store) if store is not None else None
        except Exception:
            sizes[name] = None
    return sizes


async def run_real(rows: list[GoldRow], modes: list[str], settings, limit: int, db_path: Path, gold_dir: Path,
                   quiet: bool = False) -> dict:
    from sos.embeddings import Semantic
    from sos.kiwix import KiwixClient
    from sos import search as search_mod

    conn = open_readonly(db_path)
    kiwix = KiwixClient(settings.kiwix_url)
    semantic = Semantic(settings) if "on" in modes else None
    expected = {r.id: [u for e in r.expected for u in resolve_urls(e, conn)] for r in rows}

    async def search_fn(query: str, mode: str) -> dict:
        sem = semantic if mode == "on" else None
        payload = await search_mod.search(conn, settings, kiwix, query, None, limit, use_cache=False, semantic=sem)
        if sem is not None:
            remembered = sem._vectors.get(query.strip())    # the embedding call answers None when it failed or timed out
            payload["semantic_ok"] = remembered is not None and remembered[0] is not None
        return payload

    def progress(i: int, n: int, row: GoldRow, rec: dict) -> None:
        if not quiet:
            print(f"[{i:3d}/{n}] {rec['mode']:<3} {row.id:<32} rank={rec['rank'] or '-':<3} {rec['latency_ms']:>7.0f} ms"
                  f"{' retries=' + str(rec['retries']) if rec['retries'] else ''}", file=sys.stderr)

    try:
        # Warm-up, untimed and unrecorded: the first query pays for loading the indexes and for Kiwix's cold caches.
        for word in ("water", "bleeding", "power cut", "iodine tablets"):
            for mode in modes:
                await search_fn(word, mode)
        meta = {"date": date.today().isoformat(), **git_state(), "modes": modes, "limit": limit, "db": str(db_path),
                "gold_dir": str(gold_dir), "queries": len(rows), "sets": _count_sets(rows),
                "semantic": semantic_sizes(semantic) if semantic is not None else None,
                "embed_model": settings.embed_model}
        runs = await run_rows(rows, expected, modes, search_fn, progress=progress)
    finally:
        await kiwix.aclose()
        conn.close()
    return build_document(rows, expected, runs, meta)


def _count_sets(rows: list[GoldRow]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r.set] = out.get(r.set, 0) + 1
    return dict(sorted(out.items()))


def modes_for(semantic: str) -> list[str]:
    return {"off": ["off"], "on": ["on"], "both": ["off", "on"]}[semantic]


def cmd_validate(gold_dir: Path, db_path: Path, names: Optional[list[str]]) -> int:
    conn = open_readonly(db_path)
    try:
        rows, problems = validate_gold(gold_dir, conn, names=names or None)
    finally:
        conn.close()
    counts = _count_sets(rows)
    for p in problems:
        print(p)
    print(f"{len(rows)} gold rows in {len(counts)} sets ({', '.join(f'{k} {v}' for k, v in counts.items())}); "
          f"{len(problems)} problem{'s' if len(problems) != 1 else ''}")
    return 1 if problems else 0


def run_from_namespace(args: argparse.Namespace) -> int:
    from sos.config import get_settings

    settings = get_settings()
    gold_dir = Path(getattr(args, "gold_dir", None) or DEFAULT_GOLD_DIR)
    db_path = Path(getattr(args, "db", None) or settings.db_path)
    names = list(getattr(args, "sets", None) or [])
    if getattr(args, "validate", False):
        return cmd_validate(gold_dir, db_path, names)
    rows, problems = load_gold(gold_dir, names)
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        print("fix the gold files first (sos eval-search --validate)", file=sys.stderr)
        return 1
    if not rows:
        print(f"no gold rows in {gold_dir}", file=sys.stderr)
        return 1
    modes = modes_for(getattr(args, "semantic", "both"))
    doc = asyncio.run(run_real(rows, modes, settings, int(getattr(args, "limit", 40) or 40), db_path, gold_dir))
    if getattr(args, "compact", False):
        compact(doc)
    print(format_report(doc))
    if getattr(args, "json", None):
        write_json(Path(args.json), doc)
        print(f"run written to {args.json}")
    return 0


def compare_from_namespace(args: argparse.Namespace) -> int:
    docs = []
    for path in (args.a, args.b):
        try:
            docs.append(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot read {path}: {exc}", file=sys.stderr)
            return 1
    for path, doc in zip((args.a, args.b), docs):
        if not isinstance(doc, dict) or "runs" not in doc or "queries" not in doc:
            print(f"{path} is not an eval-search run file", file=sys.stderr)
            return 1
        # recomputed from the records, so a file with its summary edited or trimmed compares honestly
        doc["summary"] = {mode: summarise_records(doc["queries"], recs) for mode, recs in doc["runs"].items()}
    print(format_compare(docs[0], docs[1], Path(args.a).stem, Path(args.b).stem))
    return 0
