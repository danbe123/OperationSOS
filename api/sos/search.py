"""Unified search (spec section 8): Kiwix classes in parallel with timeouts, FTS5 docs, exact place hits,
`score = w / (5 + rank)`, medical intent boost, exact-title jump, a bounded results cache and suggest.

Precision (2026-09-18, the owner's review: "these need to display much more elegantly and be much more
precise"): a class's rank was the only relevance the score knew, so the first hit from every class tied
whatever it was — "Side effects of warfarin" beside the Severe bleeding card for "bleeding", "Dental drill"
fourth for "power cut", the Wikipedia article titled exactly "Power cut" eighth. Every result is now
rescored by how much of the query is in its title and its snippet (an exact title leads its source; a hit
with the words in neither is a boilerplate match and is put down), the same article from two
encyclopaedias is one row, no source floods the page, the box's own library is asked with the household's
synonyms beside its words, and — when the box carries the vectors — the passages nearest the query in
meaning are fused in (`sos/embeddings.py`)."""
from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import time
from urllib.parse import quote

import httpx

from sos import places as places_mod
from sos.books import BOOK_ZIMS, SHELF_NAMES, available_zim
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
BOOK_WEIGHT = 0.6   # a novel matching "fire" must never read like the survival guide; see results.ts ORDER too
BOOKS_KEPT = 5      # catalogue hits the result cap may not squeeze out: their group is meant to be seen, low as it scores
SUGGEST_MAX = 10
# Precision: what a title and a snippet are worth, and what a hit with the words in neither is worth.
TITLE_WEIGHT = 1.2
SNIPPET_WEIGHT = 0.5
EXACT_TITLE = 2.2
BOILERPLATE = 0.45
PER_SOURCE = 3      # a source's fourth result and beyond give way a little to the rest
SOURCE_DECAY = 0.85
# Semantic: how many nearest passages are asked for, how near counts, and what one is worth beside a keyword hit.
SEMANTIC_K = 20
SEMANTIC_MIN = 0.5
SEMANTIC_WEIGHT = 1.0
WARM_QUERIES = ("water", "bleeding", "power cut")

CLASS_TITLES = {
    "uk-official": "UK official", "nhs": "NHS", "medical": "Medical", "reference": "Reference", "practical": "Practical",
    "survival": "Survival", "extended": "Extended library", "playbooks": "Playbooks", "docs": "Documents",
    "library": "Library", "places": "Places", "books": "Books",
}
KIND_BADGES = {"playbook": "Playbook", "module": "Module", "card": "Quick card", "page": "Page", "doc": "Document",
               "item": "Library", "place": "Place", "book": "Book"}
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


_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_TAGS = re.compile(r"<[^>]+>")
_NHS_TAIL = re.compile(r"\s*[-–—]\s*NHS\s*$", re.IGNORECASE)


def stem(word: str) -> str:
    """Enough of a stem to match "bleeding" to "bleed", "tins" to "tin", "purification" to "purify"-ish: the
    suffixes English hangs on a word, taken off the end. Not Porter; the index has Porter, this is for
    the titles and snippets the index does not see."""
    w = word.lower()
    for suffix in ("ation", "ations", "ings", "ing", "edly", "ies", "ied", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[: -len(suffix)]
            if suffix == "ies" or suffix == "ied":
                w += "y"
            break
    return w


def words_of(text: str) -> set[str]:
    return {stem(w) for w in _WORD.findall(_TAGS.sub(" ", text or ""))}


def term_share(terms: list[str], text: str) -> float:
    """The share of the query's terms found in a text, stems matched; a term of four letters or more also
    counts when it begins a word there ("radio" in "radios", "flood" in "floodwater")."""
    if not terms:
        return 0.0
    have = words_of(text)
    hit = 0
    for t in terms:
        st = stem(t)
        if st in have or (len(st) >= 4 and any(w.startswith(st) for w in have)):
            hit += 1
    return hit / len(terms)


def norm_title(title: str) -> str:
    return " ".join(_NHS_TAIL.sub("", title or "").lower().split())


def relevance(terms: list[str], title: str, snippet: str, q: str) -> float:
    """What a result's own words say about the query, as a multiplier on its class score: the whole query in
    the title counts most, in the snippet less; the title being the query leads its source; a hit with the
    query in neither the title nor the snippet is a boilerplate match (a crawled site's footer, a page that
    mentions the word once in a list) and is put down rather than out."""
    in_title = term_share(terms, title)
    in_snippet = term_share(terms, snippet)
    factor = 1.0 + TITLE_WEIGHT * in_title + SNIPPET_WEIGHT * in_snippet
    if norm_title(title) == " ".join((q or "").lower().split()) or (terms and norm_title(title) == " ".join(terms)):
        factor *= EXACT_TITLE
    elif in_title == 0 and in_snippet == 0 and "<b>" not in (snippet or ""):
        factor *= BOILERPLATE
    return factor


def dedupe_titles(results: list[dict]) -> list[dict]:
    """One row per article title within a source: "Bleeding" from WikEM and "Bleeding" from MDWiki, both
    medical, are the same answer twice on the screen, and "Potassium iodide" likewise. The best-scoring
    stays. Two sources with an article of the same name (Wikipedia's and WikEM's "Water purification")
    are two answers; the box's own rows, documents, books and places keep theirs: a document's pages
    share one title."""
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for r in sorted(results, key=lambda r: -r["score"]):
        if r.get("kind") == "article":
            key = (r["source"], norm_title(r["title"]))
            if key in seen:
                continue
            seen.add(key)
        out.append(r)
    return out


def diversify(results: list[dict]) -> list[dict]:
    """No source floods the page: a source's fourth result and each after it is worth a little less than it
    scored, so five NHS medicines' side-effect pages do not fill the first screen for "bleeding"."""
    counts: dict[str, int] = {}
    out = []
    for r in sorted(results, key=lambda r: -r["score"]):
        n = counts.get(r["source"], 0)
        counts[r["source"]] = n + 1
        if n >= PER_SOURCE:
            r = {**r, "score": r["score"] * (SOURCE_DECAY ** (n - PER_SOURCE + 1))}
        out.append(r)
    out.sort(key=lambda r: -r["score"])
    return out


def snippet_from_body(body: str, limit: int = 220) -> str:
    """A passage found by its meaning has no keyword to mark: its opening words are its snippet."""
    text = " ".join(re.sub(r"\[\[[^\]]*\]\]|\{\{[^}]*\}\}", " ", body or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "…"


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
    if cat in ("reference", "practical", "survival", "books"):
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
                 sources: list[str] | None = None, limit: int = 40, *, fts_mode: str = "and", use_cache: bool = True,
                 semantic=None) -> dict:
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
        if row["id"] in BOOK_ZIMS:
            continue  # the catalogue query below is the Gutenberg search; its ZIM has no article text worth a round trip
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
        (query_mod.fts_match_expanded(reduced.terms, fts_mode),),
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

    # The catalogue rows outlive the ZIM (index_books leaves them when the file is gone), so the gate is the item.
    book_rows = conn.execute(
        "SELECT b.id, b.title, b.author, b.shelf FROM fts_books f CROSS JOIN books b ON b.rowid = f.rowid "
        "WHERE fts_books MATCH ? ORDER BY bm25(fts_books, 5.0, 3.0), b.popularity DESC LIMIT 10",
        (query_mod.fts_match(reduced.terms, fts_mode),)).fetchall() if available_zim(conn) else []
    for rank, row in enumerate(book_rows, 1):
        shelf = SHELF_NAMES.get(row["shelf"] or "")
        results.append({
            "source": "books", "badge": "Books", "title": row["title"],
            "snippet": " · ".join(filter(None, [row["author"], shelf])),
            "url": f"/book/gutenberg/{row['id']}", "score": score(BOOK_WEIGHT, rank), "kind": "book", "_cat": "books",
        })

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

    # The passages nearest the query in meaning, from the box's own library: a row already found by its
    # words is lifted, one the words missed is added with its opening as its snippet.
    if semantic is not None:
        try:
            near = await semantic.query(q, SEMANTIC_K)
        except Exception:  # the semantic layer is a convenience: its failures never fail the search
            near = []
        near = [(url, cos) for url, cos in near if cos >= SEMANTIC_MIN]
        if near:
            by_url = {r["url"]: r for r in results}
            found = {}
            for row in conn.execute(
                    f"SELECT title, doc_id, kind, category, page, url, substr(body, 1, 400) AS body FROM fts_docs "
                    f"WHERE url IN ({','.join('?' * len(near))})", [u for u, _ in near]).fetchall():
                found[row["url"]] = row
            for rank, (url, cos) in enumerate(near, 1):
                row = found.get(url)
                if row is None:
                    continue
                kind = row["kind"]
                src = SOURCE_BY_KIND.get(kind, "docs")
                w = PLAYBOOK_WEIGHT if src == "playbooks" else item_weights.get(str(row["doc_id"]).split("#")[0], 1.0) if kind == "doc" else 1.0
                bonus = SEMANTIC_WEIGHT * score(w, rank)
                if url in by_url:
                    by_url[url]["score"] += bonus
                    continue
                entry = {"source": src, "badge": KIND_BADGES.get(kind, "Document"), "title": row["title"],
                         "snippet": snippet_from_body(row["body"]), "url": url, "score": bonus, "kind": kind,
                         "_cat": row["category"], "via": "meaning"}
                if row["page"]:
                    entry["page"] = int(row["page"])
                results.append(entry)
                by_url[url] = entry

    # A place is an exact match by construction and a catalogue hit is ranked on its title and author
    # already: the rescoring is for articles and the box's own passages.
    for r in results:
        if r.get("via") != "meaning" and r["kind"] not in ("place", "book"):
            r["score"] *= relevance(reduced.terms, r["title"], r["snippet"], q)
    results = dedupe(results)
    results = dedupe_titles(results)
    results = diversify(results)

    counts: dict[str, int] = {}
    for r in results:
        counts[r["source"]] = counts.get(r["source"], 0) + 1
    groups = [{"source": s, "badge": CLASS_TITLES.get(s, s), "count": n} for s, n in counts.items()]
    if sources:
        wanted = set(sources)
        results = [r for r in results if r["source"] in wanted]
    kept = results[:limit]
    # Books score below everything else by design, so a busy query would cut them all; keep a few past the cap.
    book_hits = sum(1 for r in kept if r["source"] == "books")
    if book_hits < BOOKS_KEPT:
        kept += [r for r in results[limit:] if r["source"] == "books"][:BOOKS_KEPT - book_hits]
    results = kept
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
        # No `title :` column filter here: an author's name is as good a way in as a title.
        book_match = " ".join(f'"{t}"*' for t in tokens)
        book_rows = conn.execute(
            "SELECT b.id, b.title, b.author FROM fts_books f CROSS JOIN books b ON b.rowid = f.rowid "
            "WHERE fts_books MATCH ? ORDER BY bm25(fts_books, 5.0, 3.0), b.popularity DESC LIMIT 3",
            (book_match,)).fetchall() if available_zim(conn) else []
        for r in book_rows:
            label = f"{r['title']} — {r['author']}" if r["author"] else r["title"]
            out.append({"value": r["title"], "label": label, "url": f"/book/gutenberg/{r['id']}", "source": "Book"})
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
