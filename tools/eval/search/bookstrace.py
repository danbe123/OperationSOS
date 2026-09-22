#!/usr/bin/env python3
"""Where does the right book get lost between the vector index and the page? (task 22, 2026-09-21)

    PYTHONPATH=api python tools/eval/search/bookstrace.py --replay DIR [--sets books books-extra] [--json out.json]
        [--show N]

For every book query of the gold sets, from a recording (no service): the rank and cosine of the first acceptable
book in the recorded household list (`vec_rank`, `cos`), whether the search asked for it (`vec_rank <= SEMANTIC_K`),
whether it passed the floors, the position and score it has among the rows `search()` returns for limit 100
(`page_pos`, `score`), the score of the rows at page places 3 and 10 (`s3`, `s10`), and what stood above it. The
`stage` is the first place the book is lost:

    not-in-index-top100   the acceptable book is not among the nearest 100 books
    beyond-asked-k        nearer than 100 but not among the SEMANTIC_K asked for
    under-min             cosine below SEMANTIC_MIN, the household floor: never a row
    under-floor           cosine below HOUSEHOLD_FLOOR of a row the words did not find: never a row
    outscored             a row, and on the page below place 10 (the loss the fusion is responsible for)
    cut                   a row inside the result cap that the page still does not show (cap or group)
    ok                    on the page in the first ten
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "api"))

from sos import search, searcheval as se, searchreplay      # noqa: E402
from sos.books import content_url                             # noqa: E402
from sos.config import get_settings                           # noqa: E402
from sos.evalrun import url_matches                           # noqa: E402

BOOK_SETS = ("books", "books-extra")


def household_url(key: str) -> str | None:
    zim, _, book_id = key.partition(":")
    if zim == "gutenberg_en_all" and book_id:
        return f"/book/gutenberg/{book_id}"
    if zim == search.SURVIVOR_ZIM and book_id:
        return content_url(search.SURVIVOR_ZIM, f"www.survivorlibrary.com/library/{book_id}.pdf")
    return None


def _first(urls, expected) -> int | None:
    for i, url in enumerate(urls, 1):
        if any(url_matches(url or "", e) for e in expected):
            return i
    return None


async def trace(rows, replay_dir: Path, limit: int = 100) -> list[dict]:
    settings = get_settings()
    conn = se.open_readonly(Path(settings.db_path))
    replay = searchreplay.Replay(Path(replay_dir))
    kiwix, semantic = searchreplay.ReplayKiwix(replay), searchreplay.ReplaySemantic(replay)
    out = []
    for row in rows:
        expected = [u for e in row.expected for u in se.resolve_urls(e, conn)]
        kiwix.query = row.query
        near = await semantic.query_household(row.query, searchreplay.RECORD_K)
        urls = [household_url(k) for k, _ in near]
        vec_rank = _first(urls, expected)
        cos = near[vec_rank - 1][1] if vec_rank else None
        payload = await search.search(conn, settings, kiwix, row.query, None, limit, use_cache=False, semantic=semantic)
        results = payload["results"]
        page_pos = _first((r["url"] for r in results), expected)
        rec = {"id": row.id, "set": row.set, "group": row.group, "query": row.query, "vec_rank": vec_rank, "cos": cos,
               "top_cos": near[0][1] if near else None, "k_cos": near[search.SEMANTIC_K - 1][1] if len(near) >= search.SEMANTIC_K else None,
               "page_pos": page_pos, "n_results": len(results),
               "s3": results[2]["score"] if len(results) > 2 else None, "s10": results[9]["score"] if len(results) > 9 else None}
        if page_pos:
            hit = results[page_pos - 1]
            rec.update(score=hit["score"], via=hit.get("via", ""), source=hit["source"],
                       above=[r["source"] for r in results[:page_pos - 1]])
        if page_pos is not None and page_pos <= 10:
            rec["stage"] = "ok"
        elif vec_rank is None:
            rec["stage"] = "not-in-index-top100"
        elif vec_rank > search.SEMANTIC_K:
            rec["stage"] = "beyond-asked-k"
        elif cos < search.SEMANTIC_MIN:
            rec["stage"] = "under-min"
        elif page_pos is None:
            rec["stage"] = "under-floor" if cos < min(search.HOUSEHOLD_FLOOR.values()) + 0.06 else "not-a-row"
        else:
            rec["stage"] = "outscored"
        out.append(rec)
    conn.close()
    return out


def summarise(records: list[dict]) -> str:
    stages = ("ok", "not-in-index-top100", "beyond-asked-k", "under-min", "under-floor", "not-a-row", "outscored")
    lines = [f"{'group':<22}{'n':>4}  " + "  ".join(f"{s:>19}" for s in stages)]
    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(f"{r['set']}/{r['group']}", []).append(r)
    groups["ALL"] = records
    for name, recs in groups.items():
        lines.append(f"{name:<22}{len(recs):>4}  " + "  ".join(f"{sum(r['stage'] == s for r in recs):>19}" for s in stages))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--sets", nargs="*", default=list(BOOK_SETS))
    ap.add_argument("--json")
    ap.add_argument("--show", type=int, default=0, help="print this many failing rows in full")
    args = ap.parse_args(argv)
    rows, problems = se.load_gold(se.DEFAULT_GOLD_DIR, args.sets)
    assert not problems, problems
    records = asyncio.run(trace(rows, Path(args.replay)))
    print(summarise(records))
    failing = [r for r in records if r["stage"] != "ok"]
    for r in failing[: args.show]:
        print(json.dumps(r, ensure_ascii=False))
    if args.json:
        Path(args.json).write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
