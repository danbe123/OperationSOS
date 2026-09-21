import asyncio
import json
import shutil
import time
from pathlib import Path

import httpx
import pytest
import respx

from sos import db, library, search
from sos.kiwix import KiwixClient, KiwixError, KiwixHit
from sos.manifest import load_manifests

FX = Path(__file__).parent / "fixtures"
BASE = "http://kiwix.test/kiwix"
WIKI = "wikipedia_en_100_mini_2026-01"


def test_fixed_ranking_comparisons():
    assert search.score(1.6, 4) > search.score(1.0, 1)      # playbook rank 4 beats Wikipedia rank 1
    assert search.score(1.6, 5) < search.score(1.0, 1)      # playbook rank 5 does not
    assert search.score(1.2, 2) > search.score(1.0, 1)      # medical rank 2 beats Wikipedia rank 1
    assert search.score(1.2, 3) < search.score(1.0, 1)      # medical rank 3 does not
    assert search.score(1.0, 1) == pytest.approx(1 / 6)


@pytest.mark.parametrize("row,cls", [
    ({"tier": "core", "category": "uk-official", "id": "nrr-2025"}, "uk-official"),
    ({"tier": "core", "category": "medical", "id": "nhs_uk"}, "nhs"),
    ({"tier": "core", "category": "medical", "id": "nhs_medicines"}, "nhs"),
    ({"tier": "core", "category": "medical", "id": "wikipedia_en_medicine_maxi"}, "medical"),
    ({"tier": "core", "category": "reference", "id": "wikipedia_en_all_maxi"}, "reference"),
    ({"tier": "core", "category": "practical", "id": "ifixit_en_all"}, "practical"),
    ({"tier": "core", "category": "survival", "id": "zimgit-water_en"}, "survival"),
    ({"tier": "extended", "category": "reference", "id": "gutenberg_en_all"}, "extended"),
    ({"tier": "core", "category": "education", "id": "khan"}, "reference"),
])
def test_classify(row, cls):
    assert search.classify(row) == cls


def test_medical_intent():
    assert search.is_medical_intent(["severe", "bleeding"]) is True
    assert search.is_medical_intent(["power", "cut"]) is False
    assert len(search.MEDICAL_TERMS) >= 40


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    library.upsert_items(c, load_manifests(env.manifests))
    for n in (WIKI, "sos-test-noindex"):
        shutil.copy(FX / "library" / f"{n}.zim", env.core / "zim" / f"{n}.zim")
    library.refresh_items(c, env)
    c.execute("UPDATE library_items SET fts=1 WHERE id=?", (WIKI,))
    c.execute("""INSERT INTO library_items(id, title, kind, tier, category, scenarios_json, dest, size_bytes, priority,
                 search_weight, suggest, available, fts) VALUES ('nhs.uk_en_medicines_2025-12','NHS Medicines A to Z','zim',
                 'core','medical','[]','zim/nhs.uk_en_medicines_2025-12.zim',1,5,1.4,1,1,1)""")
    db.set_setting(c, "zim_languages", '{"%s": "eng", "nhs.uk_en_medicines_2025-12": "eng", "sos-test-noindex": "eng"}' % WIKI)
    rows = [
        ("Water", "Finding, storing and making water safe.", "module:water", "module", "playbooks", "", None, "/m/water"),
        ("Grid collapse", "Weeks without power, water pumps down.", "scenario:grid-collapse", "playbook", "playbooks", "grid-collapse", None, "/s/grid-collapse"),
        ("Severe bleeding", "Press hard on the wound.", "card:bleeding", "card", "playbooks", "", None, "/medical/card/bleeding"),
        ("SOS test document", "Boil water for one minute", "sos-test-pdf#p1", "doc", "uk-official", "grid-collapse", 1, "/doc/sos-test-pdf#page=1"),
        ("Water Treatment Library", "", "item:zimgit-water", "item", "survival", "", None, "/library"),
    ]
    c.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", rows)
    c.execute("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES ('Oxford','city',51.752,-1.2577,'England',NULL)")
    c.commit()
    return c


def _run(coro):
    return asyncio.run(coro)


@respx.mock(base_url=BASE)
def test_search_merges_kiwix_and_fts_and_groups(respx_mock, conn, env):
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["q"] == "water" and resp["query"] == "water" and resp["partial"] is False
    assert route.call_count == 2  # one request for the reference class, one for the nhs class
    kinds = {r["kind"] for r in resp["results"]}
    assert {"article", "module", "playbook", "doc", "item"} <= kinds
    first = resp["results"][0]
    assert first["kind"] == "module" and first["title"] == "Water"        # exact title jump to the top of its group
    articles = [r for r in resp["results"] if r["kind"] == "article"]
    assert articles[0]["url"] == f"/read/{WIKI}/Precipitation" and articles[0]["badge"] == "Wikipedia 100"
    assert {g["source"] for g in resp["groups"]} >= {"reference", "playbooks", "docs", "library"}
    assert all(set(r) >= {"source", "badge", "title", "snippet", "url", "score", "kind"} for r in resp["results"])
    doc = next(r for r in resp["results"] if r["kind"] == "doc")
    assert doc["page"] == 1
    assert resp["took_ms"] >= 0


@respx.mock(base_url=BASE)
def test_playbook_rank_four_beats_article_rank_one(respx_mock, conn, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    playbooks = [r for r in resp["results"] if r["source"] == "playbooks"]
    articles = [r for r in resp["results"] if r["source"] == "reference"]
    assert playbooks[0]["score"] > articles[0]["score"]


# assert_all_called is off: the timed-out class is cancelled mid-flight, so respx never records that call.
@respx.mock(base_url=BASE, assert_all_called=False)
def test_slow_class_is_dropped_and_marked_partial(respx_mock, conn, env):
    async def slow(request):
        await asyncio.sleep(3)
        return httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text())

    respx_mock.get(url__regex=r".*books\.name=nhs.*").mock(side_effect=slow)
    respx_mock.get(url__regex=r".*books\.name=wikipedia.*").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    t0 = time.perf_counter()
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    elapsed = time.perf_counter() - t0
    assert resp["partial"] is True
    assert elapsed < 2.5
    assert any(r["kind"] == "article" for r in resp["results"])
    assert "nhs" not in {r["source"] for r in resp["results"]}


@respx.mock(base_url=BASE)
def test_cache_hit_on_repeat_and_miss_after_invalidate(respx_mock, conn, env):
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    _run(search.search(conn, env, KiwixClient(BASE), "water"))
    _run(search.search(conn, env, KiwixClient(BASE), "Water "))
    assert route.call_count == 2
    search.SearchCache.invalidate(conn)
    _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert route.call_count == 4


def _cache_rows(conn) -> int:
    return conn.execute("SELECT count(*) FROM search_cache").fetchone()[0]


@respx.mock(base_url=BASE)
def test_partial_responses_are_not_cached(respx_mock, conn, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(404, text="<error>Fulltext search unavailable</error>"))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["partial"] is False and all(r["kind"] != "article" for r in resp["results"])

    async def slow(request):
        await asyncio.sleep(3)
        return httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text())

    respx_mock.get("/search").mock(side_effect=slow)
    resp2 = _run(search.search(conn, env, KiwixClient(BASE), "bleeding"))
    assert resp2["partial"] is True
    assert conn.execute("SELECT count(*) FROM search_cache WHERE q LIKE '%bleeding%'").fetchone()[0] == 0


class RefusingKiwix:
    def __init__(self, exc):
        self.exc = exc

    async def search(self, *args):
        raise self.exc


@pytest.mark.parametrize("exc", [asyncio.TimeoutError(), httpx.ConnectError("refused"), OSError("unreachable"),
                                 KiwixError("search: HTTP 500: broken", status=500)],
                         ids=["timeout", "connection", "os", "500"])
def test_a_kiwix_that_cannot_answer_is_partial_and_not_cached(conn, env, exc):
    resp = _run(search.search(conn, env, RefusingKiwix(exc), "water"))
    assert resp["partial"] is True and resp["results"][0]["title"] == "Water"   # the box's own rows still come back
    assert _cache_rows(conn) == 0


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503])
@respx.mock(base_url=BASE)
def test_a_transient_http_refusal_is_partial_and_not_cached(respx_mock, conn, env, status):
    respx_mock.get("/search").mock(return_value=httpx.Response(status, text="<error>try later</error>"))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["partial"] is True
    assert _cache_rows(conn) == 0


@pytest.mark.parametrize("body", ["not xml", "<rss/>",
                                  '<rss xmlns:op="http://a9.com/-/spec/opensearch/1.1/"><channel>'
                                  "<op:totalResults>many</op:totalResults></channel></rss>"],
                         ids=["not-xml", "no-channel", "bad-total"])
@respx.mock(base_url=BASE)
def test_a_malformed_kiwix_reply_is_partial_and_not_cached(respx_mock, conn, env, body):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=body))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["partial"] is True
    assert _cache_rows(conn) == 0


@pytest.mark.parametrize("status", [400, 403, 404])
@respx.mock(base_url=BASE)
def test_a_permanent_refusal_is_no_results_for_that_group_and_still_cached(respx_mock, conn, env, status):
    respx_mock.get("/search").mock(return_value=httpx.Response(status, text="<error>Fulltext search unavailable</error>"))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["partial"] is False and resp["results"][0]["title"] == "Water"
    assert all(r["kind"] != "article" for r in resp["results"])
    assert _cache_rows(conn) == 1


@respx.mock(base_url=BASE)
def test_one_group_refused_for_good_leaves_the_others_and_the_cache(respx_mock, conn, env):
    respx_mock.get(url__regex=r".*books\.name=nhs.*").mock(
        return_value=httpx.Response(404, text="<error>Fulltext search unavailable</error>"))
    wiki = respx_mock.get(url__regex=r".*books\.name=wikipedia.*").mock(
        return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["partial"] is False
    assert {r["source"] for r in resp["results"] if r["kind"] == "article"} == {"reference"}
    assert _cache_rows(conn) == 1
    again = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert wiki.call_count == 1 and again["results"] == resp["results"]


@respx.mock(base_url=BASE)
def test_medical_intent_boosts_nhs_and_medical(respx_mock, conn, env, monkeypatch):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search_multi.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "medicine dose", use_cache=False))
    nhs = {r["url"]: r["score"] for r in resp["results"] if r["source"] == "nhs"}
    assert nhs
    # the same question with no medical word in it: every NHS row scores exactly a boost lower
    monkeypatch.setattr(search, "MEDICAL_TERMS", frozenset())
    plain = _run(search.search(conn, env, KiwixClient(BASE), "medicine dose", use_cache=False))
    unboosted = {r["url"]: r["score"] for r in plain["results"] if r["source"] == "nhs"}
    assert unboosted
    for url, s in unboosted.items():
        if url in nhs:
            assert nhs[url] == pytest.approx(s * search.MEDICAL_BOOST)


def test_place_hit_only_on_exact_match(conn, env):
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "near Oxford"))
        place = [r for r in resp["results"] if r["kind"] == "place"]
        assert len(place) == 1 and place[0]["lat"] == 51.752 and place[0]["url"].startswith("/map?lat=51.752&lon=-1.2577")
        assert place[0]["score"] == pytest.approx(search.score(2.0, 1))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "Oxford hospitals"))
        assert not [r for r in resp["results"] if r["kind"] == "place"]


def test_empty_query_and_source_filter_and_limit(conn, env):
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
        assert _run(search.search(conn, env, KiwixClient(BASE), "   "))["results"] == []
        resp = _run(search.search(conn, env, KiwixClient(BASE), "water", sources=["playbooks"], limit=2))
        assert len(resp["results"]) == 2 and {r["source"] for r in resp["results"]} == {"playbooks"}
        assert any(g["source"] == "reference" for g in resp["groups"])


@respx.mock(base_url=BASE)
def test_suggest_caps_at_ten_and_mixes_sources(respx_mock, conn, env):
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "suggest.json").read_text()))
    for i in range(12):
        conn.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                     (f"Water tip {i}", "", f"page:water-{i}", "page", "playbooks", "", None, f"/p/water-{i}"))
    conn.commit()
    out = _run(search.suggest(conn, env, KiwixClient(BASE), "wat"))
    assert len(out) == 10
    assert all(set(s) == {"value", "label", "url", "source"} for s in out)
    assert all(s["value"].lower().startswith("wat") for s in out)
    short = _run(search.suggest(conn, env, KiwixClient(BASE), "w"))
    assert short == []


def test_medical_intent_boosts_quick_cards_as_well_as_medical_sources(conn, env):
    conn.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                 ("Severe bleeding", "Press hard on the wound and do not let go.", "severe-bleeding", "card", "playbooks", "", None,
                  "/medical/card/severe-bleeding"))
    conn.commit()
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search_multi.xml").read_text()))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "bleeding", use_cache=False))
    card = next(r for r in resp["results"] if r["kind"] == "card")
    # the box's own card carries the playbook weight and, for a medical question, the medical boost, and its
    # title carries the query (so the whole passage carries it, in_body 1.0): it outranks any rank-1 medical
    # or NHS article (1.4 x 1.5 at rank 1)
    assert card["score"] == pytest.approx(search.score(1.6, 1) * 1.5 * search.relevance(["bleeding"], card["title"], card["snippet"], "bleeding", 1.0))
    assert card["score"] > search.score(1.4, 1) * 1.5
    assert resp["results"][0]["kind"] == "card"


def test_badge_title_drops_the_catalogue_tail_and_results_are_deduplicated():
    assert search.badge_title("NHS Medicines A to Z (Kiwix build, December 2025)") == "NHS Medicines A to Z"
    assert search.badge_title("Wikipedia (English, with images)") == "Wikipedia"
    assert search.badge_title("iFixit repair guides") == "iFixit repair guides"
    rows = [{"source": "playbooks", "url": "/p/solar#a", "score": 0.2}, {"source": "playbooks", "url": "/p/solar#b", "score": 0.3},
            {"source": "playbooks", "url": "/p/water#a", "score": 0.1}, {"source": "docs", "url": "/doc/x#page=1", "score": 0.2},
            {"source": "docs", "url": "/doc/x#page=2", "score": 0.2}]
    out = search.dedupe(rows)
    assert [(r["url"], r["score"]) for r in out] == [("/p/solar#b", 0.3), ("/p/water#a", 0.1), ("/doc/x#page=1", 0.2), ("/doc/x#page=2", 0.2)]


def _seed_books(conn):
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
                 "('gutenberg_en_all', 'Project Gutenberg', 'zim', 'core', 'books', 'zim/gutenberg_en_all.zim', 100, 1, 1)")
    conn.executemany("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) VALUES "
                     "('gutenberg_en_all', ?, ?, ?, ?, ?, ?, ?, NULL)", [
        (1232, "The Prince", "Niccolo Machiavelli", "J", 4, "The Prince.1232.epub", "The Prince.1232.html"),
        (2701, "Water Babies", "Charles Kingsley", "PR", 3, "Water Babies.2701.epub", "Water Babies.2701.html"),
    ])
    conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
    conn.commit()


@respx.mock(base_url=BASE)
def test_books_group_sits_in_the_results_with_its_own_badge_and_url(respx_mock, conn, env):
    _seed_books(conn)
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    hits = [r for r in resp["results"] if r["source"] == "books"]
    assert hits and hits[0]["title"] == "Water Babies" and hits[0]["url"] == "/book/gutenberg/2701"
    assert hits[0]["badge"] == "Books" and hits[0]["kind"] == "book" and hits[0]["snippet"] == "Charles Kingsley · English literature"
    assert hits[0]["score"] == pytest.approx(search.score(search.BOOK_WEIGHT, 1))
    assert {"source": "books", "badge": "Books", "count": 1} in resp["groups"]
    # the Gutenberg ZIM is flagged fts=1 above, but the box never fans a Kiwix search out to it
    assert route.call_count == 2
    assert all("gutenberg_en_all" not in str(call.request.url) for call in route.calls)


@respx.mock(base_url=BASE, assert_all_called=False)
def test_books_vanish_from_search_and_suggest_when_the_zim_is_gone(respx_mock, conn, env):
    _seed_books(conn)
    conn.execute("UPDATE library_items SET available=0 WHERE id='gutenberg_en_all'")
    conn.commit()
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text="[]"))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert not [r for r in resp["results"] if r["source"] == "books"]
    assert not [s for s in _run(search.suggest(conn, env, KiwixClient(BASE), "prin")) if s["source"] == "Book"]


@respx.mock(base_url=BASE, assert_all_called=False)
def test_suggest_finds_a_book_by_its_author(respx_mock, conn, env):
    _seed_books(conn)
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text="[]"))
    out = _run(search.suggest(conn, env, KiwixClient(BASE), "kings"))
    assert any(s["url"] == "/book/gutenberg/2701" for s in out)


@respx.mock(base_url=BASE)
def test_books_survive_the_result_cap(respx_mock, conn, env):
    _seed_books(conn)
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water", limit=2, use_cache=False))
    sources = [r["source"] for r in resp["results"]]
    assert sources.count("books") == 1 and len(sources) == 3      # the cap plus the one book hit
    assert resp["results"][-1]["title"] == "Water Babies"


def test_classify_puts_core_book_zims_in_their_own_class():
    assert search.classify({"tier": "core", "category": "books", "id": "survivorlibrary.com_en_all"}) == "books"


@respx.mock(base_url=BASE, assert_all_called=False)
def test_suggest_offers_catalogue_titles(respx_mock, conn, env):
    _seed_books(conn)
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text="[]"))
    out = _run(search.suggest(conn, env, KiwixClient(BASE), "prin"))
    assert {"value": "The Prince", "label": "The Prince — Niccolo Machiavelli", "url": "/book/gutenberg/1232", "source": "Book"} in out


def test_term_share_counts_a_phrase_in_full_and_a_synonym_for_half():
    terms = ["food", "freezer", "power", "cut"]                         # three ideas: food, freezer, power cut
    assert search.term_share(terms, "In a power cut keep the freezer shut and the food inside") == pytest.approx(1.0)
    assert search.term_share(terms, "In a blackout keep the fridge shut and the meals inside") == pytest.approx(0.5)
    assert search.term_share(terms, "Never cut a live power line; a wound bleeds") == pytest.approx(0.0)
    assert search.term_share(terms, "Power cuts: what to do") == pytest.approx(1 / 3)
    assert search.term_share([], "anything") == 0.0


def test_section_of_and_strip_heading_take_the_anchor_as_the_passage_s_heading():
    assert search.section_of("/m/water#what-to-do") == "What to do"
    assert search.section_of("/m/power#uk-specifics") == "UK specifics"
    assert search.section_of("/doc/nrr#page=3") == "" and search.section_of("/p/plan") == ""
    assert search.strip_heading("What to do 1. Fill every container.", "/m/water#what-to-do") == "1. Fill every container."
    assert search.strip_heading("Key facts - Heat one room.", "/m/shelter-heat#key-facts") == "Heat one room."
    assert search.strip_heading("Fill every container.", "/m/water#what-to-do") == "Fill every container."   # not opened with it: untouched
    assert search.snippet_from_body("Warnings Warning: shock can develop slowly.", url="/medical/card/shock#warnings") == "Warning: shock can develop slowly."


def test_a_page_s_go_deeper_links_give_way_to_the_section_that_says_something(conn, env):
    conn.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", [
        ("Solar panels in a power cut", "Go deeper - Power module - Mains electricity", "page:solar", "page", "playbooks", "", None, "/p/solar#go-deeper"),
        ("Solar panels in a power cut", "In a power cut a grid-tied inverter shuts down.", "page:solar", "page", "playbooks", "", None, "/p/solar#keeping-some-power"),
    ])
    conn.commit()
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text="<rss><channel></channel></rss>"))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "power cut", use_cache=False))
    solar = next(r for r in resp["results"] if r["title"].startswith("Solar"))
    assert solar["url"] == "/p/solar#keeping-some-power"


def test_the_page_about_the_query_ranks_above_one_that_mentions_it(conn, env):
    conn.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", [
        ("Food storage", "Pasta must be boiled in water. Boil water. Boil water.", "page:food-storage", "page", "playbooks", "", None, "/p/food-storage#cooking"),
        ("Water disinfection", "Boil: a rolling boil for one minute kills what is in the water, whatever the altitude.", "page:water-disinfection", "page", "playbooks", "", None, "/p/water-disinfection#boil"),
    ])
    conn.commit()
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text="<rss><channel></channel></rss>"))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "boil water", use_cache=False))
    pages = [r["url"] for r in resp["results"] if r["kind"] == "page"]
    assert pages[0] == "/p/water-disinfection#boil"     # both carry both words; the title of one is about it


def test_the_household_s_word_for_a_failure_finds_the_module_and_its_title_puts_it_first(conn, env):
    conn.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", [
        ("National grid collapse", "Water: when booster pumps stop the taps run dry; when it fails, sewage backs up.", "scenario:grid", "playbook", "playbooks", "", None, "/s/grid-collapse#first-72-hours"),
        ("Water", "1. Fill every clean container while the mains still runs. With the mains off it is too late to fill.", "module:water", "module", "playbooks", "", None, "/m/water#what-to-do"),
    ])
    conn.commit()
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text="<rss><channel></channel></rss>"))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "what to do if the water stops", use_cache=False))
    own = [r["url"] for r in resp["results"] if r["source"] == "playbooks"]
    # "stops" finds "off" (a synonym, half a word) and the module's title is the subject: it leads the
    # playbook that carries the word itself
    assert own[:2] == ["/m/water#what-to-do", "/s/grid-collapse#first-72-hours"]


# --- one archive Kiwix refuses must not hide the rest of its class ------------------------------------------

class PickyKiwix:
    """A Kiwix that refuses (HTTP 400) any request naming an archive in `bad`, and answers one hit per
    archive otherwise; `calls` is every request it was sent."""

    def __init__(self, bad=(), status=400):
        self.bad, self.status, self.calls = set(bad), status, []

    async def search(self, names, pattern, n, timeout):
        self.calls.append(list(names))
        if self.bad & set(names):
            raise KiwixError("search: HTTP 400: Two or more books in different languages", status=self.status)
        return [KiwixHit(f"Water in {name}", f"A/{name}", "Water supply", name) for name in names]


@pytest.fixture
def survival(conn):
    """Four archives of one class, each with a full-text index, in the one language group."""
    names = ["surv-a", "surv-b", "surv-c", "surv-d"]
    for i, name in enumerate(names):
        conn.execute("INSERT INTO library_items(id,title,kind,tier,category,dest,available,fts,priority) "
                     "VALUES (?,?,'zim','core','survival',?,1,1,?)", (name, name, f"zim/{name}.zim", 50 + i))
    languages = json.loads(db.get_setting(conn, "zim_languages", "{}"))
    db.set_setting(conn, "zim_languages", json.dumps({**languages, **{n: "eng" for n in names}}))
    conn.commit()
    search._refused_seen.clear()
    return names


def _survival_urls(resp):
    return {r["url"] for r in resp["results"] if r["source"] == "survival"}


def test_a_healthy_class_costs_one_request_per_group(conn, env, survival):
    kiwix = PickyKiwix()
    resp = _run(search.search(conn, env, kiwix, "water"))
    assert resp["partial"] is False
    assert sorted(c for c in kiwix.calls if c[0].startswith("surv")) == [survival]   # the four archives, once
    assert _survival_urls(resp) == {f"/read/{n}/A/{n}" for n in survival}


@pytest.mark.parametrize("bad", ["surv-a", "surv-b", "surv-d"])
def test_one_refused_archive_leaves_the_rest_of_its_class(conn, env, survival, bad):
    kiwix = PickyKiwix(bad=[bad])
    resp = _run(search.search(conn, env, kiwix, "water"))
    assert resp["partial"] is False
    assert _survival_urls(resp) == {f"/read/{n}/A/{n}" for n in survival if n != bad}
    assert _cache_rows(conn) == 1          # the refusal is permanent: the answer is complete and is kept
    # every archive that was asked for singly or in a half was asked for at most once per level
    assert max(len(c) for c in kiwix.calls) == 4 and [bad] in kiwix.calls


def test_several_refused_archives_are_all_left_out(conn, env, survival):
    kiwix = PickyKiwix(bad=["surv-a", "surv-c"])
    resp = _run(search.search(conn, env, kiwix, "water"))
    assert resp["partial"] is False
    assert _survival_urls(resp) == {"/read/surv-b/A/surv-b", "/read/surv-d/A/surv-d"}


def test_every_archive_refused_is_a_class_with_nothing_to_say(conn, env, survival):
    resp = _run(search.search(conn, env, PickyKiwix(bad=survival), "water"))
    assert resp["partial"] is False and not _survival_urls(resp)


@pytest.mark.parametrize("status", [429, 500, 503])
def test_a_transient_refusal_is_not_split(conn, env, survival, status):
    kiwix = PickyKiwix(bad=["surv-a"], status=status)
    resp = _run(search.search(conn, env, kiwix, "water"))
    assert resp["partial"] is True and not _survival_urls(resp)
    assert sorted(c for c in kiwix.calls if c[0].startswith("surv")) == [survival]   # asked once, not halved


def test_a_half_that_times_out_is_partial_but_the_other_half_answers(conn, env, survival):
    class Mixed(PickyKiwix):
        async def search(self, names, pattern, n, timeout):
            if names == ["surv-c", "surv-d"]:
                raise asyncio.TimeoutError()
            return await super().search(names, pattern, n, timeout)

    resp = _run(search.search(conn, env, Mixed(bad=["surv-b"]), "water"))
    assert resp["partial"] is True
    assert _survival_urls(resp) == {"/read/surv-a/A/surv-a"}


def test_a_refusal_is_logged_once_however_many_searches_meet_it(conn, env, survival, caplog):
    kiwix = PickyKiwix(bad=["surv-b"])
    with caplog.at_level("WARNING", logger="sos.search"):
        for q in ("water", "fire", "boil water"):
            _run(search.search(conn, env, kiwix, q, use_cache=False))
    refusals = [r for r in caplog.records if "Kiwix refused" in r.getMessage()]
    assert 1 <= len(refusals) <= 3          # the whole group, one half, and the archive itself: once each
    assert len({r.getMessage() for r in refusals}) == len(refusals)


def test_interleave_keeps_each_lists_ranks():
    assert search._interleave([["a1", "a2", "a3"], ["b1"], []]) == ["a1", "b1", "a2", "a3"]
    assert search._interleave([]) == []
