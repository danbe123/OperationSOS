#!/usr/bin/env python3
"""Why is the box's own quick card missing for a plain-English injury description? (task 24, 2026-09-22)

    PYTHONPATH=api SOS_STATE=/home/dan/OperationSOS/.dev/state \
        python tools/eval/search/cardtrace.py [--sets injury-fresh] [--json out.json] [--show N]

For every query of the named gold sets (default: `injury-fresh`, the fresh "gash on arm"-family phrasings
written for task 24 -- none names its card by its own wording), live against the running Kiwix and embedding
server (no recording: these queries are not in any existing one): the card's nearest passage rank and cosine
in the box's own dense index (`vec_rank`, `cos`), whether it was even fetched inside `SEMANTIC_K`, whether it
cleared `SEMANTIC_MIN`, whether it qualified for card promotion (`CARD_COS`, `CARDS_KEPT` -- reproduced here
exactly as `search.py`'s own loop computes it, from the same near-list), whether the keyword-only search found
it at all and where, and where it actually lands on the page. `stage` is the first place it is lost, mirroring
`bookstrace.py`'s shape for books:

    not-embedded           the card has no measurably similar passage at all (a data problem)
    starved-of-budget       nearer than the full index rank suggests, but outside SEMANTIC_K -- never fetched
    below-semantic-min      inside SEMANTIC_K but below SEMANTIC_MIN -- dropped before any floor is checked
    below-ordinary-floor    above SEMANTIC_MIN, below CARD_COS, below the ordinary keyword-not-found floor too
                            (SEMANTIC_FLOOR[(False, False)]) -- never a row at all
    card-slots-full         above CARD_COS but two nearer cards already took the CARDS_KEPT promotion slots
    admitted-unprotected     a row (>= the ordinary floor), but not protected -- must out-score everything else
    medicine-override       protection earned, then discarded because _kept_medicines matched this query
    protected-but-absent     protection earned and not overridden, yet still not on the page (a real bug)
    ok                      in the first three results
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "api"))

from sos import search, searcheval as se, query as query_mod   # noqa: E402
from sos.config import get_settings                             # noqa: E402
from sos.embeddings import Semantic                              # noqa: E402
from sos.kiwix import KiwixClient                                 # noqa: E402

DEFAULT_SETS = ["injury-fresh"]


def _card_prefix(item: str) -> str | None:
    if not item.startswith("card:"):
        return None
    return f"/medical/card/{item.split(':', 1)[1]}"


async def trace(rows, limit: int = 100) -> list[dict]:
    settings = get_settings()
    conn = se.open_readonly(Path(settings.db_path))
    kiwix = KiwixClient(settings.kiwix_url)
    semantic = Semantic(settings)
    out = []
    try:
        for row in rows:
            prefixes = [p for e in row.expected for p in [_card_prefix(e.get("item", ""))] if p]
            if not prefixes:
                continue

            # The full ranked list of the box's own dense passages against this query -- exact (Index.search
            # is a dot product, not approximate), so asking for every key gives the card's true rank however
            # deep it sits, independent of SEMANTIC_K.
            full_near = await semantic.query(row.query, 10_000_000)
            best_rank, best_cos, best_url = None, None, None
            for i, (url, cos) in enumerate(full_near, 1):
                if any(url == p or url.startswith(p + "#") for p in prefixes):
                    best_rank, best_cos, best_url = i, cos, url
                    break

            # The keyword-only page: does the card lead it (kw_pos == 0, the words' own protection route)?
            kw_payload = await search.search(conn, settings, kiwix, row.query, None, limit, use_cache=False, semantic=None)
            kw_urls = [r["url"] for r in kw_payload["results"]]
            kw_pos = next((i for i, u in enumerate(kw_urls) if any(u == p or u.startswith(p + "#") for p in prefixes)), None)

            # Reproduce search.py's own card_pages loop (lines ~731-735) from the same SEMANTIC_K-deep,
            # SEMANTIC_MIN-filtered near-list it actually uses, so "did this card get one of the CARDS_KEPT
            # promotion slots" is exact, not guessed.
            near_k = [(u, c) for u, c in full_near[: search.SEMANTIC_K] if c >= search.SEMANTIC_MIN]
            kinds: dict[str, str] = {}
            if near_k:
                urls = [u for u, _ in near_k]
                for r in conn.execute(f"SELECT url, kind FROM fts_docs WHERE url IN ({','.join('?' * len(urls))})", urls):
                    kinds[r["url"]] = r["kind"]
            card_pages: list[str] = []
            for u, c in near_k:
                page = u.split("#", 1)[0]
                if c >= search.CARD_COS and kinds.get(u) == "card" and page not in card_pages and len(card_pages) < search.CARDS_KEPT:
                    card_pages.append(page)
            admitted_as_card = any(p in card_pages for p in prefixes)

            # _kept_medicines, reproduced on the keyword-only top few: an NHS row the words rank in the first
            # MEDICINE_TOP whose title carries MEDICINE_SHARE of the query's words silently empties card_pages
            # for this query (search.py line ~808, "[] if medicines else card_pages").
            terms = query_mod.reduce_query(row.query).terms
            medicine_hit = any(
                r["source"] == search.MEDICINE_SOURCE and search.term_share(terms, r["title"]) >= search.MEDICINE_SHARE
                for r in kw_payload["results"][: search.MEDICINE_TOP]
            )

            # The real page, meaning on: where does the card actually land?
            payload = await search.search(conn, settings, kiwix, row.query, None, limit, use_cache=False, semantic=semantic)
            urls = [r["url"] for r in payload["results"]]
            final_pos = next((i + 1 for i, u in enumerate(urls) if any(u == p or u.startswith(p + "#") for p in prefixes)), None)

            floor_unprotected = search.SEMANTIC_FLOOR[(False, False)]
            rec = {
                "id": row.id, "query": row.query, "expected_card": prefixes[0].rsplit("/", 1)[-1],
                "vec_rank": best_rank, "cos": best_cos, "in_semantic_k": best_rank is not None and best_rank <= search.SEMANTIC_K,
                "kw_pos": kw_pos, "kw_leads": kw_pos == 0, "admitted_as_card": admitted_as_card,
                "medicine_hit": medicine_hit, "final_pos": final_pos,
                "top3": [{"title": r["title"], "source": r["source"], "kind": r["kind"]} for r in payload["results"][:3]],
            }
            if final_pos is not None and final_pos <= 3:
                rec["stage"] = "ok"
            elif best_rank is None:
                rec["stage"] = "not-embedded"
            elif best_rank > search.SEMANTIC_K:
                rec["stage"] = "starved-of-budget"
            elif best_cos < search.SEMANTIC_MIN:
                rec["stage"] = "below-semantic-min"
            elif kw_pos == 0 or admitted_as_card:
                rec["stage"] = "medicine-override" if medicine_hit else "protected-but-absent"
            elif best_cos < search.CARD_COS:
                rec["stage"] = "admitted-unprotected" if best_cos >= floor_unprotected else "below-ordinary-floor"
            elif not admitted_as_card:
                rec["stage"] = "card-slots-full"
            else:
                rec["stage"] = "protected-but-absent"
            out.append(rec)
    finally:
        await kiwix.aclose()
        conn.close()
    return out


def summarise(records: list[dict]) -> str:
    stages = ("ok", "starved-of-budget", "below-semantic-min", "below-ordinary-floor", "card-slots-full",
              "admitted-unprotected", "medicine-override", "protected-but-absent", "not-embedded")
    lines = [f"{'n':>3}  " + "  ".join(f"{s:>21}" for s in stages)]
    lines.append(f"{len(records):>3}  " + "  ".join(f"{sum(r['stage'] == s for r in records):>21}" for s in stages))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="*", default=DEFAULT_SETS)
    ap.add_argument("--json")
    ap.add_argument("--show", type=int, default=999, help="print this many failing rows in full")
    args = ap.parse_args(argv)
    rows, problems = se.load_gold(se.DEFAULT_GOLD_DIR, args.sets)
    assert not problems, problems
    records = asyncio.run(trace(rows))
    print(summarise(records))
    print()
    failing = [r for r in records if r["stage"] != "ok"]
    for r in failing[: args.show]:
        print(json.dumps(r, ensure_ascii=False))
    if args.json:
        Path(args.json).write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
