import asyncio
import shutil
import time
from pathlib import Path

import httpx
import pytest
import respx

from sos import db, library, search
from sos.kiwix import KiwixClient
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
    assert articles[0]["url"] == f"/read/{WIKI}/Precipitation" and articles[0]["badge"] == "Wikipedia 100 (mini)"
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
    assert conn.execute("SELECT count(*) FROM search_cache WHERE q LIKE 'bleeding%'").fetchone()[0] == 0


@respx.mock(base_url=BASE)
def test_medical_intent_boosts_nhs_and_medical(respx_mock, conn, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search_multi.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "medicine dose"))
    nhs = [r for r in resp["results"] if r["source"] == "nhs"]
    assert nhs and nhs[0]["score"] == pytest.approx(search.score(1.4, 1) * 1.5)


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
