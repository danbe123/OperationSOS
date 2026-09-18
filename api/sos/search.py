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
import functools
import re
import sqlite3
import time
from urllib.parse import quote

import httpx

from sos import places as places_mod
from sos.books import BOOK_ZIMS, SHELF_NAMES, available_zim, content_url
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
# Semantic: how many nearest passages are asked for, how near counts, and what one is worth beside a keyword
# hit. bge-small's cosines run close together — a passage that answers sits at 0.68 to 0.82, the nearest
# stranger at 0.62 to 0.72 — so a hit is worth its distance above the floor, up to the ceiling, times the
# source's weight. Meaning as a lift to a row the words found is cheap evidence and takes a low floor;
# meaning as the only evidence takes a higher one, and higher still for a page of one of 21,000 converted
# document pages, whose neighbourhood is dense with strangers (a building regulation for "generator
# indoors" at 0.71; the box's own "Mains electricity" answers at 0.68).
SEMANTIC_K = 20
SEMANTIC_FLOOR = {          # (found by the words too, a converted document's page) -> the cosine asked for
    (True, False): 0.60, (True, True): 0.66, (False, False): 0.66, (False, True): 0.74,
}
SEMANTIC_MIN = min(SEMANTIC_FLOOR.values())
SEMANTIC_CEIL = 0.82
SEMANTIC_WEIGHT = 0.5
# The household collection's own ZIM id for Survivor Library (Gutenberg reuses BOOK_ZIMS's own id): its
# real books are plain PDF entries at this one path shape (Task 5's confirmed finding), read straight
# through the generic Kiwix content route rather than a bespoke reader.
SURVIVOR_ZIM = "survivorlibrary.com_en_all"
# Wikipedia's own ZIM id (also sos.embeddings.WIKIPEDIA_ZIM): named again here, not imported, so search.py
# gains no new module-level coupling to sos.embeddings (Task 9, Ruling 9) -- the rerank pass below needs
# only this id string to find Wikipedia's own keyword hits by their url; everything else it needs (the
# store, the query embedding) arrives through the `semantic` parameter search() already receives.
WIKIPEDIA_ZIM = "wikipedia_en_all_maxi"
# Wikipedia's own keyword hits are rescored, never zeroed and never doubled: a real semantic match (cosine
# near 1.0) lifts a hit to 1.3x, a weak or negative one settles it to 0.7x -- tune against real queries in
# Task 10's acceptance step, not by theory.
WIKIPEDIA_RERANK_BASE = 0.7
WIKIPEDIA_RERANK_SPAN = 0.6


def semantic_bonus(cos: float, w: float) -> float:
    """What one meaning hit is worth: its distance above the floor, capped at the ceiling, times the
    source's own weight -- the one place this formula is written, shared by the box's own library and
    the household collection alike."""
    return SEMANTIC_WEIGHT * w * min(1.0, (cos - SEMANTIC_MIN) / (SEMANTIC_CEIL - SEMANTIC_MIN))


# A question rarely has every one of its words in the passage that answers it ("generator indoors": the
# Mains electricity page says "never indoors" of a generator two sentences apart): when the AND finds fewer
# than this, the OR is asked too, its rows after the AND's and ranked by how many of the words they carry.
FTS_OR_BELOW = 5
# How many rows the keyword index hands over to be re-ranked, for the box's own 750 passages and for the
# 21,000 converted document pages separately: one bm25 limit of twenty across both let "water" AND ("stops"
# OR "off" OR "fails") fill up before the Water module's long "What to do" was reached — 173 of the box's
# own passages carry those words, and bm25 put the module's sections at 47, 92 and 96. The box's own
# library is small enough to re-rank nearly whole (150 rows: 10 ms to fetch, 20 ms to score on the PC).
FTS_ROWS_OWN = 150
FTS_ROWS_DOC = 30
# A page's "Go deeper" (its links) and a card's "Source" are lists of other titles: a row from one is worth
# less, so a page found there is represented by the section that says something (see dedupe).
FURNITURE_SECTIONS = {"go-deeper", "source"}
FURNITURE_FACTOR = 0.5
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


@functools.lru_cache(maxsize=65536)
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


SYNONYM_CREDIT = 0.5   # a synonym found ("fridge" for "freezer") is worth half the word itself


def _has(tokens: list[str], have: set[str], term: str) -> bool:
    """Stems matched; a term of four letters or more also counts when it begins a word there ("radio" in
    "radios", "flood" in "floodwater"); a phrase counts where its words stand together, in order."""
    if " " in term:
        want = [stem(w) for w in term.split()]
        return any(tokens[i:i + len(want)] == want for i in range(len(tokens) - len(want) + 1))
    st = stem(term)
    return st in have or (len(st) >= 4 and any(w.startswith(st) for w in have))


def term_share(terms: list[str], text: str) -> float:
    """The share of the query's ideas found in a text: a term (or a phrase, "power cut") counts in full, a
    synonym of it for half."""
    groups = query_mod.expand_terms(terms)
    if not groups:
        return 0.0
    tokens = [stem(w) for w in _WORD.findall(_TAGS.sub(" ", text or ""))]
    have = set(tokens)
    hit = 0.0
    for alts in groups:
        if _has(tokens, have, alts[0]):
            hit += 1
        elif any(_has(tokens, have, a) for a in alts[1:]):
            hit += SYNONYM_CREDIT
    return hit / len(groups)


def norm_title(title: str) -> str:
    return " ".join(_NHS_TAIL.sub("", title or "").lower().split())


def relevance(terms: list[str], title: str, snippet: str, q: str, in_body: float = 0.0) -> float:
    """What a result's own words say about the query, as a multiplier on its class score: the whole query in
    the title counts most, in the snippet less; the title being the query leads its source; a hit with the
    query in neither the title nor the snippet is a boilerplate match (a crawled site's footer, a page that
    mentions the word once in a list) and is put down rather than out. For the box's own passages the share
    of the words carried by the whole passage is known and stands in for the engine's fourteen-word snippet."""
    in_title = term_share(terms, title)
    in_snippet = max(term_share(terms, snippet), in_body)
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


def section_of(url: str) -> str:
    """The section a passage is, from its anchor: '/m/water#what-to-do' is 'What to do'."""
    frag = url.split("#", 1)[1] if "#" in (url or "") else ""
    if not frag or frag.startswith("page="):
        return ""
    words = frag.replace("-", " ").strip()
    words = " ".join("UK" if w == "uk" else w for w in words.split())
    return words[:1].upper() + words[1:]


def strip_heading(body: str, url: str) -> str:
    """The passage's words without the section heading they open with: the heading is the anchor's."""
    heading = section_of(url)
    text = (body or "").lstrip()
    if heading and text[:len(heading)].lower() == heading.lower():
        text = text[len(heading):].lstrip(" -–:.\n")
    return text


def snippet_from_body(body: str, limit: int = 220, url: str = "") -> str:
    """A passage found by its meaning has no keyword to mark: its opening words are its snippet."""
    text = " ".join(re.sub(r"\[\[[^\]]*\]\]|\{\{[^}]*\}\}", " ", strip_heading(body, url)).split())
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


_cache_generation: dict[str, object] = {}


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
    # A new semantic index changes every answer: the cache of the old ones goes with it.
    generation = getattr(semantic, "generation", None) if semantic is not None else None
    if generation is not None and _cache_generation.get("seen") != generation:
        SearchCache.invalidate(conn)
        _cache_generation["seen"] = generation
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

    # Wikipedia's own keyword hits, rescored by meaning -- never a new row, only a nudge to a row the words
    # already found (Task 9). Wikipedia's `source`/`_cat` are both the literal string "reference" (classify()
    # never returns the ZIM id for it: wikipedia_en_all_maxi's manifest category is "reference", and
    # classify()'s "reference"/"practical"/"survival"/"books" branch returns the category unchanged), so the
    # only place the ZIM id survives is the url itself -- the filter below matches on that, not on source/_cat.
    if semantic is not None:
        wiki_prefix = f"/read/{WIKIPEDIA_ZIM}/"
        wiki_hits = [r for r in results if r["url"].startswith(wiki_prefix)]
        if wiki_hits:
            # everything after the fixed "/read/<zim id>/" prefix, keeping any internal slashes intact: a
            # real Wikipedia article path is namespaced (e.g. "A/Some_Article"), and WikipediaStore's own
            # keys (_wikipedia_article_keys, sos/embeddings.py) are reader.paths() values verbatim, slashes
            # and all -- an rsplit("/", 1) here would throw away everything before the last slash instead.
            keys = [r["url"].split("/", 3)[3] for r in wiki_hits]
            try:
                wiki_scores = await semantic.rerank_wikipedia(q, keys)
            except Exception:  # the semantic layer is a convenience: its failures never fail the search
                wiki_scores = {}
            for r, key in zip(wiki_hits, keys):
                cos = wiki_scores.get(key)
                if cos is not None:
                    r["score"] *= WIKIPEDIA_RERANK_BASE + WIKIPEDIA_RERANK_SPAN * max(0.0, cos)

    item_weights = {r["id"]: float(r["search_weight"] or 1.0) for r in conn.execute("SELECT id, search_weight FROM library_items")}
    fts_sql = ("SELECT title, doc_id, kind, category, page, url, body, snippet(fts_docs, 1, '<b>', '</b>', '…', 14) AS snip "
               "FROM fts_docs WHERE fts_docs MATCH ? AND kind {op} 'doc' ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT {n}")

    def fts_rows(docs: bool) -> tuple[list, dict]:
        """The keyword rows of one half of the index — the box's own passages, or the document pages — with
        the share of the query each carries. bm25 favours a short passage that repeats one word over a long
        one that carries them all: the rows rank by the share of the query's ideas the passage carries plus
        the share its title carries (the page that is about the query — "Water" for "the water stops",
        "Water disinfection" for "boil water" — above one that mentions it), bm25 deciding among equals."""
        n = FTS_ROWS_DOC if docs else FTS_ROWS_OWN
        sql = fts_sql.format(op="=" if docs else "!=", n=n)
        rows = conn.execute(sql, (query_mod.fts_match_expanded(reduced.terms, fts_mode),)).fetchall()
        if fts_mode == "and" and len(reduced.terms) >= 2 and len(rows) < FTS_OR_BELOW:
            have = {r["url"] for r in rows}
            rows = list(rows) + [r for r in conn.execute(sql, (query_mod.fts_match_expanded(reduced.terms, "or"),)).fetchall()
                                 if r["url"] not in have][: n - len(rows)]
        carried = {row["url"]: term_share(reduced.terms, f"{row['title']} {row['body']}") for row in rows}
        titled = {row["url"]: term_share(reduced.terms, row["title"]) for row in rows}
        return sorted(rows, key=lambda row: -(carried[row["url"]] + titled[row["url"]])), carried

    ranked: list[tuple[int, sqlite3.Row, float]] = []
    for docs in (False, True):
        rows, carried = fts_rows(docs)
        ranked.extend((rank, row, carried[row["url"]]) for rank, row in enumerate(rows, 1))
    for rank, row, carry in ranked:
        kind = row["kind"]
        src = SOURCE_BY_KIND.get(kind, "docs")
        if src == "playbooks":
            w = PLAYBOOK_WEIGHT
        elif kind == "doc":
            w = item_weights.get(str(row["doc_id"]).split("#")[0], 1.0)
        else:
            w = 1.0
        entry = {"source": src, "badge": KIND_BADGES.get(kind, "Document"), "title": row["title"], "snippet": row["snip"] or "",
                 "url": row["url"], "score": score(w, rank), "kind": kind, "_cat": row["category"], "_carried": carry}
        if src == "playbooks" and row["url"].split("#", 1)[-1] in FURNITURE_SECTIONS:
            entry["score"] *= FURNITURE_FACTOR
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
    # words is lifted, one the words missed is added with its opening as its snippet. The household
    # collection (Gutenberg, Survivor Library -- one vector per book) is asked the same way immediately
    # after, under this same guard: a household hit joins the "books" group, the same source the
    # catalogue's own keyword hits use, so a book found by both words and meaning is lifted once rather
    # than shown twice under two badges, and every household hit is eligible for the BOOKS_KEPT rescue.
    if semantic is not None:
        by_url = {r["url"]: r for r in results}

        try:
            near = await semantic.query(q, SEMANTIC_K)
        except Exception:  # the semantic layer is a convenience: its failures never fail the search
            near = []
        near = [(url, cos) for url, cos in near if cos >= SEMANTIC_MIN]
        if near:
            found = {}
            for row in conn.execute(
                    f"SELECT title, doc_id, kind, category, page, url, substr(body, 1, 400) AS body FROM fts_docs "
                    f"WHERE url IN ({','.join('?' * len(near))})", [u for u, _ in near]).fetchall():
                found[row["url"]] = row
            for url, cos in near:
                row = found.get(url)
                if row is None:
                    continue
                kind = row["kind"]
                if cos < SEMANTIC_FLOOR[(url in by_url, kind == "doc")]:
                    continue
                src = SOURCE_BY_KIND.get(kind, "docs")
                w = PLAYBOOK_WEIGHT if src == "playbooks" else item_weights.get(str(row["doc_id"]).split("#")[0], 1.0) if kind == "doc" else 1.0
                bonus = semantic_bonus(cos, w)
                if url in by_url:
                    by_url[url]["score"] += bonus
                    continue
                entry = {"source": src, "badge": KIND_BADGES.get(kind, "Document"), "title": row["title"],
                         "snippet": snippet_from_body(row["body"], url=url), "url": url, "score": bonus, "kind": kind,
                         "_cat": row["category"], "via": "meaning"}
                if row["page"]:
                    entry["page"] = int(row["page"])
                results.append(entry)
                by_url[url] = entry

        try:
            household_near = await semantic.query_household(q, SEMANTIC_K)
        except Exception:  # the semantic layer is a convenience: its failures never fail the search
            household_near = []
        household_near = [(key, cos) for key, cos in household_near if cos >= SEMANTIC_MIN]
        for key, cos in household_near:
            zim, _, book_id = key.partition(":")
            if zim == "gutenberg_en_all":
                url = f"/book/gutenberg/{book_id}"
            else:
                url = content_url(SURVIVOR_ZIM, f"www.survivorlibrary.com/library/{book_id}.pdf")
            # a household book is never a "doc page" in the existing sense: its neighbourhood is not the
            # dense, noisy one a converted document's page has, so False is right for that flag here too.
            if cos < SEMANTIC_FLOOR[(url in by_url, False)]:
                continue
            bonus = semantic_bonus(cos, BOOK_WEIGHT)
            if url in by_url:
                by_url[url]["score"] += bonus
                continue
            book_row = conn.execute("SELECT title, author FROM books WHERE zim=? AND id=?", (zim, book_id)).fetchone()
            if book_row is not None:
                title, author = book_row["title"], book_row["author"] or ""
            else:
                # Survivor Library has no catalogue row at all (Task 6's known gap); a Gutenberg id whose
                # own row went missing is covered the same way: the slug is all there is to show.
                title, author = re.sub(r"[-_]+", " ", book_id).strip().title(), ""
            entry = {"source": "books", "badge": "Books", "title": title, "snippet": author, "url": url,
                     "score": bonus, "kind": "book", "_cat": "books", "via": "meaning"}
            results.append(entry)
            by_url[url] = entry

    # A place is an exact match by construction and a catalogue hit is ranked on its title and author
    # already: the rescoring is for articles and the box's own passages.
    for r in results:
        if r.get("via") != "meaning" and r["kind"] not in ("place", "book"):
            r["score"] *= relevance(reduced.terms, r["title"], r["snippet"], q, r.get("_carried", 0.0))
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
        r.pop("_carried", None)
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
