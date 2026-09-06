"""Unified search (spec section 8): Kiwix classes in parallel with timeouts, FTS5 docs, exact place hits,
`score = w / (5 + rank)`, medical intent boost, exact-title jump, a bounded results cache and suggest."""
from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import time
from urllib.parse import quote

import httpx

from sos import places as places_mod
from sos import query as query_mod
from sos.config import Settings
from sos.db import connect, get_setting, now_iso
from sos.kiwix import KiwixClient, KiwixError

K = 5
CLASS_TIMEOUTS = {"reference": 4.0}
DEFAULT_TIMEOUT = 2.0
PAGE_LENGTH = 8
CACHE_MAX = 500
PLAYBOOK_WEIGHT = 1.6
MEDICAL_BOOST = 1.5
PLACE_WEIGHT = 2.0
SUGGEST_MAX = 10
WARM_QUERIES = ("water", "bleeding", "power cut")

CLASS_TITLES = {
    "uk-official": "UK official", "nhs": "NHS", "medical": "Medical", "reference": "Reference", "practical": "Practical",
    "survival": "Survival", "extended": "Extended library", "playbooks": "Playbooks", "docs": "Documents",
    "library": "Library", "places": "Places",
}
KIND_BADGES = {"playbook": "Playbook", "module": "Module", "card": "Quick card", "page": "Page", "doc": "Document",
               "item": "Library", "place": "Place"}
SOURCE_BY_KIND = {"playbook": "playbooks", "module": "playbooks", "card": "playbooks", "page": "playbooks",
                  "doc": "docs", "item": "library"}

_LOCAL_MEDICAL_TERMS = frozenset("""
bleeding bleed wound laceration burn burns scald fracture broken bone sprain choking choke cpr resuscitation unconscious
breathing pulse shock stroke heart attack chest seizure fit fever temperature infection sepsis antibiotic antibiotics
paracetamol ibuprofen aspirin dose dosage medicine medicines tablet tablets pill pills vomiting diarrhoea dehydration
rehydration hypothermia frostbite heatstroke poison poisoning overdose allergy anaphylaxis asthma inhaler diabetes
insulin pregnancy labour birth rash tick bite sting drowning concussion
""".split())
try:  # plan 05 ships the full 200-term list
    from sos.ai_terms import MEDICAL_TERMS  # type: ignore
except ImportError:
    MEDICAL_TERMS = _LOCAL_MEDICAL_TERMS


def score(weight: float, rank: int) -> float:
    return weight / (K + rank)


_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")


def badge_title(title: str) -> str:
    """The short name a result wears: the library title without its catalogue tail, e.g. '(Kiwix build, December 2025)'."""
    return _PARENTHETICAL.sub("", title or "").strip() or title


def dedupe(results: list[dict]) -> list[dict]:
    """One row per authored page: its sections are indexed separately, so "Solar panels in a power cut" could
    appear three times under different anchors. The best-scoring section wins. Library articles and PDF pages
    keep their own rows (a PDF page is a distinct answer)."""
    best: dict[str, dict] = {}
    out: list[dict] = []
    for r in results:
        if r.get("source") != "playbooks":
            out.append(r)
            continue
        key = r["url"].split("#", 1)[0]
        if key not in best:
            best[key] = r
            out.append(r)
        elif r["score"] > best[key]["score"]:
            out[out.index(best[key])] = r
            best[key] = r
    return out


def classify(row) -> str:
    if row["tier"] == "extended":
        return "extended"
    cat = row["category"]
    if cat == "uk-official":
        return "uk-official"
    if cat == "medical":
        return "nhs" if str(row["id"]).startswith("nhs") else "medical"
    if cat in ("reference", "practical", "survival"):
        return cat
    return "reference"


def is_medical_intent(tokens: list[str]) -> bool:
    return any(t in MEDICAL_TERMS for t in tokens)


class SearchCache:
    @staticmethod
    def key(q: str, sources: list[str] | None, limit: int) -> str:
        return f"{' '.join(q.lower().split())}|{','.join(sorted(sources or []))}|{limit}"

    @staticmethod
    def get(conn: sqlite3.Connection, key: str) -> dict | None:
        row = conn.execute("SELECT results_json FROM search_cache WHERE q=?", (key,)).fetchone()
        return json.loads(row["results_json"]) if row else None

    @staticmethod
    def put(conn: sqlite3.Connection, key: str, payload: dict) -> None:
        conn.execute("INSERT OR REPLACE INTO search_cache(q, results_json, created_at) VALUES (?,?,?)",
                     (key, json.dumps(payload), now_iso()))
        conn.execute(
            "DELETE FROM search_cache WHERE q IN (SELECT q FROM search_cache ORDER BY created_at DESC LIMIT -1 OFFSET ?)",
            (CACHE_MAX,),
        )
        conn.commit()

    @staticmethod
    def invalidate(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM search_cache")
        conn.commit()


async def _search_class(kiwix: KiwixClient, cls: str, names: list[str], pattern: str, timeout: float):
    try:
        return cls, await kiwix.search(names, pattern, PAGE_LENGTH, timeout), False
    except asyncio.TimeoutError:
        return cls, None, True
    except (KiwixError, httpx.HTTPError, OSError):
        return cls, None, False


def _empty(q: str) -> dict:
    return {"q": q, "query": "", "results": [], "groups": [], "took_ms": 0, "partial": False}


async def search(conn: sqlite3.Connection, settings: Settings, kiwix: KiwixClient, q: str,
                 sources: list[str] | None = None, limit: int = 40, *, fts_mode: str = "and", use_cache: bool = True) -> dict:
    t0 = time.perf_counter()
    reduced = query_mod.reduce_query(q or "")
    if not reduced.terms:
        return _empty(q or "")
    limit = max(1, min(int(limit or 40), 100))
    key = SearchCache.key(q, sources, limit)
    use_cache = use_cache and fts_mode == "and"
    cached = SearchCache.get(conn, key) if use_cache else None
    if cached is not None:
        cached["q"] = q  # the cache key is normalised; echo back what the caller actually asked for
        cached["took_ms"] = int((time.perf_counter() - t0) * 1000)
        return cached

    results: list[dict] = []
    partial = False

    languages = json.loads(get_setting(conn, "zim_languages", "{}") or "{}")
    books: dict[tuple[str, str], list[str]] = {}
    weights: dict[str, float] = {}
    titles: dict[str, str] = {}
    for row in conn.execute("SELECT * FROM library_items WHERE kind='zim' AND available=1 AND fts=1 ORDER BY priority, id"):
        cls = classify(row)
        books.setdefault((cls, languages.get(row["id"], "eng")), []).append(row["id"])
        weights[row["id"]] = float(row["search_weight"] or 1.0)
        titles[row["id"]] = row["title"]
    pattern = query_mod.fts_match(reduced.terms, "or") if fts_mode == "or" else reduced.kiwix
    tasks = [_search_class(kiwix, cls, names, pattern, CLASS_TIMEOUTS.get(cls, DEFAULT_TIMEOUT))
             for (cls, _lang), names in books.items()]
    for cls, hits, timed_out in await asyncio.gather(*tasks):
        if hits is None:
            partial = partial or timed_out
            continue
        for rank, hit in enumerate(hits, 1):
            results.append({
                "source": cls, "badge": badge_title(titles.get(hit.book, CLASS_TITLES[cls])), "title": hit.title, "snippet": hit.snippet,
                "url": f"/read/{hit.book}/{hit.path}", "score": score(weights.get(hit.book, 1.0), rank), "kind": "article",
                "_cat": "medical" if cls in ("nhs", "medical") else cls,
            })

    item_weights = {r["id"]: float(r["search_weight"] or 1.0) for r in conn.execute("SELECT id, search_weight FROM library_items")}
    rows = conn.execute(
        "SELECT title, doc_id, kind, category, page, url, snippet(fts_docs, 1, '<b>', '</b>', '…', 14) AS snip "
        "FROM fts_docs WHERE fts_docs MATCH ? ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT 20",
        (query_mod.fts_match(reduced.terms, fts_mode),),
    ).fetchall()
    for rank, row in enumerate(rows, 1):
        kind = row["kind"]
        src = SOURCE_BY_KIND.get(kind, "docs")
        if src == "playbooks":
            w = PLAYBOOK_WEIGHT
        elif kind == "doc":
            w = item_weights.get(str(row["doc_id"]).split("#")[0], 1.0)
        else:
            w = 1.0
        entry = {"source": src, "badge": KIND_BADGES.get(kind, "Document"), "title": row["title"], "snippet": row["snip"] or "",
                 "url": row["url"], "score": score(w, rank), "kind": kind, "_cat": row["category"]}
        if row["page"]:
            entry["page"] = int(row["page"])
        results.append(entry)

    for cand in query_mod.place_candidates(q):
        hit = places_mod.exact_place(conn, cand) if len(cand) >= 2 else None
        if hit:
            results.append({
                "source": "places", "badge": "Place", "title": hit["name"],
                "snippet": f"{hit['kind'].title()}, {hit['region']}",
                "url": f"/map?lat={hit['lat']}&lon={hit['lon']}&z=13&label={quote(hit['name'])}",
                "score": score(PLACE_WEIGHT, 1), "kind": "place", "lat": hit["lat"], "lon": hit["lon"], "_cat": "places",
            })
            break

    if is_medical_intent(reduced.terms):
        for r in results:
            # the box's own quick cards are medical guidance too: without the boost an NHS medicine page
            # about warfarin outranked the Severe bleeding card for "bleeding"
            if r["_cat"] == "medical" or r["kind"] == "card":
                r["score"] *= MEDICAL_BOOST

    qnorm = " ".join((q or "").lower().split())
    by_source: dict[str, list[dict]] = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)
    for rs in by_source.values():
        top = max(x["score"] for x in rs)
        for r in rs:
            if r["title"].strip().lower() == qnorm:
                r["score"] = top + 0.001
    results = dedupe(results)
    results.sort(key=lambda r: -r["score"])

    counts: dict[str, int] = {}
    for r in results:
        counts[r["source"]] = counts.get(r["source"], 0) + 1
    groups = [{"source": s, "badge": CLASS_TITLES.get(s, s), "count": n} for s, n in counts.items()]
    if sources:
        wanted = set(sources)
        results = [r for r in results if r["source"] in wanted]
    results = results[:limit]
    for r in results:
        r.pop("_cat", None)
    payload = {"q": q, "query": reduced.kiwix, "results": results, "groups": groups,
               "took_ms": int((time.perf_counter() - t0) * 1000), "partial": partial}
    if not partial and use_cache:
        SearchCache.put(conn, key, payload)
    return payload


async def suggest(conn: sqlite3.Connection, settings: Settings, kiwix: KiwixClient, q: str) -> list[dict]:
    term = " ".join((q or "").split())
    if len(term) < 2:
        return []
    out: list[dict] = []
    tokens = query_mod.tokenise(term)
    if tokens:
        match = "title : (" + " ".join(f'"{t}"*' for t in tokens) + ")"
        rows = conn.execute(
            "SELECT title, url, kind FROM fts_docs WHERE fts_docs MATCH ? ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT ?",
            (match, SUGGEST_MAX),
        ).fetchall()
        for r in rows:
            out.append({"value": r["title"], "label": r["title"], "url": r["url"], "source": KIND_BADGES.get(r["kind"], "Document")})
    books = conn.execute("SELECT id, title FROM library_items WHERE kind='zim' AND available=1 AND suggest=1 ORDER BY priority, id").fetchall()

    async def one(book):
        try:
            return book, await asyncio.wait_for(kiwix.suggest(book["id"], term), 1.5)
        except (asyncio.TimeoutError, KiwixError, httpx.HTTPError, OSError):
            return book, []

    for book, entries in await asyncio.gather(*(one(b) for b in books)):
        for e in entries[:5]:
            out.append({"value": e["value"], "label": e["label"], "url": f"/read/{book['id']}/{e['path']}", "source": book["title"]})
    seen: set[tuple[str, str | None]] = set()
    unique: list[dict] = []
    for s in out:
        k = (s["value"], s["url"])
        if k not in seen:
            seen.add(k)
            unique.append(s)
    return unique[:SUGGEST_MAX]


async def warm(settings: Settings, kiwix: KiwixClient, db_path) -> None:
    """Three canned queries after boot and rescan so the Wikipedia and NHS indexes are hot."""
    conn = connect(db_path)
    try:
        for q in WARM_QUERIES:
            try:
                await search(conn, settings, kiwix, q)
            except Exception:  # warming is best-effort: a cold or missing index must not block boot
                pass
    finally:
        conn.close()
