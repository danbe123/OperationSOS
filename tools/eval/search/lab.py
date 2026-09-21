#!/usr/bin/env python3
"""The search tuning lab: fusion experiments as replays of a recorded live run (task 19, 2026-09-21).

    PYTHONPATH=api python tools/eval/search/lab.py --replay .dev/search-recordings/clean-2026-09-21 \
        [--exp NAME ...] [--json out.json] [--diff A B] [--jobs 6]

Every experiment is a set of overrides on `sos.search` (module constants) applied around a meaning-on replay of the whole gold set; the keyword-only control is the replay
with `semantic=None`. No service is needed. Read `sos.searchreplay` for what a recording holds.

The table reports, per experiment: own-library (and its health group), paraphrase, safety (plain / hard),
wikipedia and books as hit@1, hit@3 and MRR, and the median compute time of the replayed search. `--halves`
adds the fixed alternating split (within each set, rows sorted by id: even positions are the TUNE half, odd
the CHECK half) for the sets tuning is judged on.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "api"))

from sos import search, searcheval as se, searchreplay   # noqa: E402
from sos.config import get_settings                       # noqa: E402

# name -> overrides: constants of sos.search (DENSE_WEIGHT, CARD_COS, CARDS_KEPT, WIKIPEDIA_LIFT, ...).
# The task-19 experiments (fusion by rank or normalised score, per-class floors, title and card protection,
# five ways of reranking Wikipedia) ran on switches that are gone from the code; they are in this file's history
# at commit c39a441, with the two grids that tuned them, and their table is in docs/reviews/2026-09-21-search-tuning.md.
EXPERIMENTS: dict[str, dict] = {
    "control": {},                                    # the adopted values
    "dense-weight-1": {"DENSE_WEIGHT": 1.0},
    "dense-weight-3": {"DENSE_WEIGHT": 3.0},
    "no-cards-kept": {"CARD_COS": 2.0},               # the nearest cards are not kept (the words' first card still is)
    "wikipedia-lift-0": {"WIKIPEDIA_LIFT": 0.0},
    "medicine-top-5": {"MEDICINE_TOP": 5},            # promote an NHS page the words ranked fourth or fifth too
    "no-medicine-rule": {"MEDICINE_TOP": 0},           # the fusion as it stood before the medicine rule
    "no-cards-kept": {"CARD_COS": 2.0},               # the nearest cards are not kept (the words' first card still is)
    "wikipedia-lift-0": {"WIKIPEDIA_LIFT": 0.0},
    "medicine-top-5": {"MEDICINE_TOP": 5},            # promote an NHS page the words ranked fourth or fifth too
    "no-medicine-rule": {"MEDICINE_TOP": 0},           # the fusion as it stood before the medicine rule
    "cards-kept-1": {"CARDS_KEPT": 1},
    "card-cos-.66": {"CARD_COS": 0.66},
    "kept-top-2": {"KEPT_TOP": 2},
    "floors-own-.66": {"SEMANTIC_FLOOR": {(True, False): 0.63, (True, True): 0.66, (False, False): 0.66, (False, True): 0.74}},
    "floors-found-.60": {"SEMANTIC_FLOOR": {(True, False): 0.60, (True, True): 0.66, (False, False): 0.69, (False, True): 0.74}},
    "floors-old": {"SEMANTIC_FLOOR": {(True, False): 0.60, (True, True): 0.66, (False, False): 0.66, (False, True): 0.74}},
}

SHOW = (("own-library", "own"), ("own-library/health", "health"), ("paraphrase", "para"), ("safety", "safety"),
        ("safety/plain", "plain"), ("safety/hard", "hard"), ("wikipedia", "wiki"), ("books", "books"), ("ALL", "ALL"))
HALVES_OF = ("paraphrase", "safety", "own-library")


@contextlib.contextmanager
def applied(overrides: dict):
    """Overrides in force for the block: constants of the search module, restored afterwards."""
    saved = []
    try:
        for name, value in overrides.items():
            saved.append((name, getattr(search, name)))
            setattr(search, name, value)
        yield
    finally:
        for name, value in reversed(saved):
            setattr(search, name, value)


_state: dict = {}


SETS: list[str] = []      # the gold sets replayed (all when empty); set from --sets before the workers fork


def _prepare(replay_dir: str):
    if "rows" not in _state:
        settings = get_settings()
        rows, problems = se.load_gold(se.DEFAULT_GOLD_DIR, SETS or None)
        assert not problems, problems
        _state.update(settings=settings, rows=rows, replay=searchreplay.Replay(Path(replay_dir)),
                      db=Path(settings.db_path))
    return _state


def run_experiment(args) -> dict:
    """(name, overrides, replay_dir, mode) -> {"name", "records": {id: record}, "misses"}. One process per job."""
    name, overrides, replay_dir, mode = args
    st = _prepare(replay_dir)
    with applied(overrides):
        doc = asyncio.run(se.run_replay(st["rows"], [mode], st["settings"], 40, st["db"], se.DEFAULT_GOLD_DIR, st["replay"]))
    return {"name": name, "overrides": {k: repr(v) for k, v in overrides.items()}, "records": doc["runs"][mode],
            "queries": doc["queries"], "misses": doc["meta"]["replay_misses"]}


def summarise(result: dict, only: set[str] | None = None) -> dict:
    records = result["records"] if only is None else {k: v for k, v in result["records"].items() if k in only}
    return se.summarise_records(result["queries"], records)


def halves(queries: dict) -> tuple[set[str], set[str]]:
    """The fixed alternating split: within each set, ids sorted, even positions tune, odd positions check."""
    tune, check = set(), set()
    by_set: dict[str, list[str]] = {}
    for qid, meta in queries.items():
        by_set.setdefault(meta["set"], []).append(qid)
    for ids in by_set.values():
        for i, qid in enumerate(sorted(ids)):
            (tune if i % 2 == 0 else check).add(qid)
    return tune, check


def _cells(summary: dict) -> list[str]:
    out = []
    for key, _label in SHOW:
        m = summary.get(key)
        if m is None:
            out.append("      -      ")
        elif key in ("wikipedia", "books", "ALL") or key == "own-library/health":
            out.append(f"{m['hit@1']:.3f} {m['hit@3']:.3f} {m['mrr@10']:.3f}")
        else:
            out.append(f"{m['hit@1']:.3f} {m['hit@3']:.3f} {m['mrr@10']:.3f}")
    return out


def table(results: list[dict], title: str = "", only: set[str] | None = None) -> str:
    head = ["experiment"] + [f"{label} h1 h3 mrr" for _k, label in SHOW] + ["p50ms"]
    rows = [head]
    for r in results:
        s = summarise(r, only)
        rows.append([r["name"]] + _cells(s) + [f"{s['ALL']['lat_median_ms']:.0f}"])
    widths = [max(len(row[i]) for row in rows) for i in range(len(head))]
    lines = ["  ".join(c.ljust(widths[i]) if i == 0 else c.rjust(widths[i]) for i, c in enumerate(row)) for row in rows]
    return "\n".join(([title] if title else []) + [lines[0], "  ".join("-" * w for w in widths)] + lines[1:])


def safety_guard(result: dict) -> dict:
    """The guard rows: how many of safety/plain and safety/hard are in the top three, and which hard ones are not."""
    q = result["queries"]
    out = {"plain_top3": 0, "plain_n": 0, "hard_top3": 0, "hard_n": 0, "hard_missing": []}
    for qid, rec in result["records"].items():
        meta = q[qid]
        if meta["set"] != "safety":
            continue
        kind = "plain" if meta["group"] == "plain" else "hard"
        out[f"{kind}_n"] += 1
        ok = rec["rank"] is not None and rec["rank"] <= 3
        out[f"{kind}_top3"] += ok
        if kind == "hard" and not ok:
            out["hard_missing"].append(f"{qid}:{rec['rank']}")
    return out


def diff(a: dict, b: dict, sets: tuple[str, ...] | None = None) -> str:
    """Queries whose outcome bucket moved between two experiments (b relative to a)."""
    lines = []
    for qid in sorted(a["records"]):
        meta = a["queries"][qid]
        if sets and meta["set"] not in sets:
            continue
        ra, rb = a["records"][qid]["rank"], b["records"][qid]["rank"]
        if ra != rb and (se.bucket(ra) != se.bucket(rb) or min(ra or 99, rb or 99) <= 3):
            lines.append(f"  {qid:<36} {ra or '-':>3} -> {rb or '-':<3} {meta['query']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--exp", nargs="*", help="experiment names (default: all)")
    ap.add_argument("--json")
    ap.add_argument("--halves", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--diff", nargs=2, metavar=("A", "B"))
    ap.add_argument("--diff-sets", nargs="*")
    ap.add_argument("--guard", action="store_true")
    ap.add_argument("--sets", nargs="*", help="replay only these gold sets (books are 40 per cent of the cost)")
    args = ap.parse_args(argv)
    SETS[:] = args.sets or []
    names = args.exp or list(EXPERIMENTS)
    if args.diff:
        names = list(dict.fromkeys([*names, *args.diff])) if args.exp else list(args.diff)
    jobs = [("keyword", {}, args.replay, "off")] + [(n, EXPERIMENTS[n], args.replay, "on") for n in names]
    with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(run_experiment, jobs))
    by_name = {r["name"]: r for r in results}
    print(table(results))
    bad = [(r["name"], r["misses"]) for r in results if any(r["misses"].values())]
    if bad:
        print("\nwarning: the recording could not answer some questions (results not comparable):", bad)
    if args.halves:
        tune, check = halves(results[0]["queries"])
        for label, subset in (("TUNE half", tune), ("CHECK half", check)):
            keep = {q for q in subset if results[0]["queries"][q]["set"] in HALVES_OF}
            print("\n" + table(results, f"-- {label} (sets: {', '.join(HALVES_OF)}) --", keep))
    if args.guard:
        print()
        for r in results:
            g = safety_guard(r)
            print(f"{r['name']:<28} plain {g['plain_top3']}/{g['plain_n']}  hard {g['hard_top3']}/{g['hard_n']}  missing: {', '.join(g['hard_missing'])}")
    if args.diff:
        a, b = by_name[args.diff[0]], by_name[args.diff[1]]
        print(f"\nqueries whose ranking moved, {args.diff[0]} -> {args.diff[1]}:")
        print(diff(a, b, tuple(args.diff_sets) if args.diff_sets else None))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
