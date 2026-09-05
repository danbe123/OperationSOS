# api/tests/test_ai_retrieval.py
import re
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import sos.ai as ai
from sos.ai import (Hit, article_paragraphs, best_window, estimate_tokens, longest_terms, reduce_query,
                    retrieve, run_search, trim_around_first_term)

FIXTURES = Path(__file__).parent / "fixtures" / "ai"
WIKI = "wikipedia_en_100_mini_2026-01"
STOP = {"how", "do", "i", "the", "a", "to", "what", "is", "my", "can", "of", "for", "in", "and", "should", "if"}


def simple_terms(question: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", question.lower()) if t not in STOP]


@pytest.fixture
def fixed_tokenizer(monkeypatch):
    monkeypatch.setattr(ai, "content_terms", simple_terms)


def hits_for(*specs):
    return [Hit(title=t, url=u, source=s, kind=k) for (t, u, s, k) in specs]


@pytest.fixture
def raw_routes(kiwix_mock):
    nhs = (FIXTURES / "nhs_paracetamol.html").read_text(encoding="utf-8")
    wiki = (FIXTURES / "wiki_mi.html").read_text(encoding="utf-8")
    pages = {(WIKI, "Myocardial_infarction"): wiki,
             ("nhs.uk_en_medicines_2025-12", "www.nhs.uk/medicines/paracetamol-for-adults/"): nhs}

    def serve(request, book, path):
        html = pages.get((book, path))
        return httpx.Response(200, text=html) if html else httpx.Response(404, text="not found")

    kiwix_mock.get(url__regex=r"http://kiwix\.test/kiwix/raw/(?P<book>[^/]+)/content/(?P<path>.+)").mock(side_effect=serve)
    return kiwix_mock


# --- query reduction -------------------------------------------------------

def test_reduce_query_uses_plan01_tokeniser_and_drops_question_words():
    terms = reduce_query("How do I make the water safe to drink?")
    assert "water" in terms and "safe" in terms and "drink" in terms
    for stop in ("how", "do", "i", "the", "to"):
        assert stop not in terms
    assert len(terms) <= 6


def test_reduce_query_keeps_six_terms_in_order_without_duplicates(fixed_tokenizer):
    q = "water water filter boil chlorine tablets iodine bleach storage"
    assert reduce_query(q) == ["water", "filter", "boil", "chlorine", "tablets", "iodine"]


def test_longest_terms_keeps_original_order():
    assert longest_terms(["boil", "water", "chlorine", "tablets", "iodine", "safe"]) == ["chlorine", "tablets", "iodine"]
    assert longest_terms(["make", "water", "safe", "drink", "chlorine", "bleach"]) == ["water", "chlorine", "bleach"]
    assert longest_terms(["ab", "cd"]) == ["ab", "cd"]


# --- html to paragraphs ----------------------------------------------------

def test_article_paragraphs_nhs_keeps_main_and_drops_chrome():
    blocks = article_paragraphs((FIXTURES / "nhs_paracetamol.html").read_text(encoding="utf-8"))
    assert blocks[0].startswith("Paracetamol for adults")
    assert any(b.startswith("Find out how paracetamol for adults treats") for b in blocks)
    assert any(b.startswith("The usual dose of paracetamol for adults is 1 or 2 500mg tablets") for b in blocks)
    joined = "\n".join(blocks)
    for chrome in ("Skip to main content", "NHS homepage", "Health A to Z", "About us", "Cookies",
                   "Ibuprofen for adults", "dataLayer", "nhsuk-header"):
        assert chrome not in joined, chrome


def test_article_paragraphs_wikipedia_uses_main_and_skips_empty_paragraphs():
    blocks = article_paragraphs((FIXTURES / "wiki_mi.html").read_text(encoding="utf-8"))
    assert blocks[0] == "Myocardial infarction"
    assert any(b.startswith("A myocardial infarction (MI), commonly known as a heart attack") for b in blocks)
    assert "Acute myocardial infarction (AMI), heart attack" in blocks
    joined = "\n".join(blocks)
    assert "Main page" not in joined and "last edited" not in joined and "" not in blocks


def test_article_paragraphs_falls_back_to_body_without_main():
    html = ("<html><head><title>T</title></head><body><nav>menu</nav>"
            "<div><p>First para.</p><p>Second para.</p></div></body></html>")
    assert article_paragraphs(html) == ["First para.", "Second para."]


# --- windows ---------------------------------------------------------------

def test_estimate_tokens_is_words_times_1_3():
    assert estimate_tokens("one two three four") == int(4 * 1.3) + 1
    assert estimate_tokens("") == 1


def test_best_window_prefers_the_term_dense_region():
    blocks = ["Intro about nothing much."] + [f"Filler paragraph number {i} with many words " * 20 for i in range(6)]
    blocks += ["Boil water for one minute to make it safe to drink.", "Chlorine tablets also work."]
    out = best_window(blocks, ["water", "boil", "safe"], max_tokens=60)
    assert out.startswith("Boil water") and "Chlorine" in out


def test_best_window_trims_an_oversized_block_around_the_first_term():
    big = "word " * 900 + "water is key here " + "tail " * 100
    out = best_window([big], ["water"], max_tokens=130)
    assert "water" in out and len(out.split()) <= 100


def test_best_window_with_no_term_hits_takes_the_start():
    blocks = ["Alpha paragraph.", "Beta paragraph.", "Gamma paragraph."]
    assert best_window(blocks, ["zzz"], max_tokens=400) == "Alpha paragraph.\nBeta paragraph.\nGamma paragraph."
    assert best_window([], ["x"]) == ""


def test_trim_around_first_term():
    text = " ".join(f"w{i}" for i in range(50)) + " fallout " + " ".join(f"z{i}" for i in range(50))
    out = trim_around_first_term(text, ["fallout"], max_words=12)
    assert "fallout" in out and len(out.split()) == 12
    assert trim_around_first_term("short text", ["x"], 12) == "short text"


# --- search adapter --------------------------------------------------------

@pytest.mark.anyio
async def test_run_search_uses_or_mode_and_bypasses_cache(monkeypatch, ai_db, ai_settings):
    captured = {}

    async def fake_search(conn, settings, kiwix, q, **kw):
        captured.update(q=q, **kw)
        return SimpleNamespace(results=[SimpleNamespace(title="Water", url=f"/read/{WIKI}/Water", source=WIKI,
                                                        kind="article", snippet="", score=0.2)])

    monkeypatch.setattr(ai.sos_search, "search", fake_search)
    hits = await run_search("water boil", ai_db, None, ai_settings)
    assert captured["q"] == "water boil" and captured["fts_mode"] == "or" and captured["use_cache"] is False
    assert Hit(title="Water", url=f"/read/{WIKI}/Water", source=WIKI, kind="article") in hits


@pytest.mark.anyio
async def test_large_title_index_does_not_displace_fulltext_guidance(monkeypatch, ai_db, ai_settings):
    from unittest.mock import AsyncMock
    ai_db.execute("UPDATE fts_docs SET body=? WHERE url='/p/water-disinfection'",
                  ("Boil water for one minute to make it safe to drink.",))
    monkeypatch.setattr(ai.sos_search, "search", AsyncMock(return_value={"results": []}))
    kiwix = SimpleNamespace(
        suggest=AsyncMock(return_value=[{"value": f"Safe drinking water society {i}", "path": f"society-{i}"}
                                        for i in range(60)]),
        raw_article=AsyncMock(return_value="<main><p>The water society was founded in 1900.</p></main>"),
    )
    hits = await run_search("water safe drink", ai_db, kiwix, ai_settings)
    assert any(h.url == "/p/water-disinfection" for h in hits[:3])


def test_fts_match_or_mode():
    from sos.query import fts_match
    assert fts_match(["water", "boil"], "or") == '"water" OR "boil"'
    assert fts_match(["st", "john", "s"]) == '"st" "john" "s"'
    assert fts_match(["1:1", "ratio"], "or") == '"1:1" OR "ratio"'


# --- retrieve --------------------------------------------------------------

@pytest.mark.anyio
async def test_matched_health_source_is_grounding_without_copying_ui_excerpt(ai_db):
    original = [ai.Passage(n, f"Other {n}", f"/p/other-{n}", "playbooks", "Other text") for n in (1, 2, 3)]
    verbatim = ai.Verbatim("Heart attack", "/medical/card/heart-attack", ["UI-only excerpt"], None)
    selected = await ai.prefer_health_source(original, verbatim, ["heart", "attack"], ai_db, None)
    assert selected[0].url == verbatim.url and "Call 999" in selected[0].text
    assert "UI-only excerpt" not in selected[0].text
    assert [p.n for p in selected] == [1, 2, 3]
    assert await ai.prefer_health_source(selected, verbatim, ["heart"], ai_db, None) == selected

@pytest.mark.anyio
async def test_retrieve_builds_three_numbered_passages_from_article_doc_and_card(monkeypatch, ai_db, ai_settings, raw_routes):
    from sos.kiwix import KiwixClient
    calls = []

    async def fake_run_search(q, conn, kiwix, settings, fts_mode="or"):
        calls.append(q)
        return hits_for(
            ("Myocardial infarction", f"/read/{WIKI}/Myocardial_infarction", WIKI, "article"),
            ("Nuclear War Survival Skills p. 12", "/doc/nwss#page=12", "nwss", "doc"),
            ("Heart attack", "/medical/card/heart-attack", "playbooks", "card"),
            ("Oxford", "/map?lat=51.75&lon=-1.26&z=12&label=Oxford", "places", "place"),
        )

    monkeypatch.setattr(ai, "run_search", fake_run_search)
    passages = await retrieve(["heart", "attack", "symptoms"], ai_db, KiwixClient(ai_settings.kiwix_url), ai_settings)
    assert [p.n for p in passages] == [1, 2, 3]
    assert passages[0].title == "Myocardial infarction" and passages[0].source == WIKI
    assert "commonly known as a heart attack" in passages[0].text
    assert passages[1].url == "/doc/nwss#page=12" and "fallout" in passages[1].text.lower()
    assert passages[2].url == "/medical/card/heart-attack" and "Call 999" in passages[2].text
    assert all(estimate_tokens(p.text) <= 400 for p in passages)
    assert calls == ["heart attack symptoms"]


@pytest.mark.anyio
async def test_retrieve_retries_with_three_longest_terms_when_fewer_than_three_hits(monkeypatch, ai_db, ai_settings, raw_routes):
    from sos.kiwix import KiwixClient
    calls = []

    async def fake_run_search(q, conn, kiwix, settings, fts_mode="or"):
        calls.append(q)
        if len(calls) == 1:
            return hits_for(("Heart attack", "/medical/card/heart-attack", "playbooks", "card"))
        return hits_for(
            ("Heart attack", "/medical/card/heart-attack", "playbooks", "card"),
            ("Water disinfection", "/p/water-disinfection", "playbooks", "page"),
            ("Water", "/m/water", "playbooks", "module"),
        )

    monkeypatch.setattr(ai, "run_search", fake_run_search)
    passages = await retrieve(["make", "water", "safe", "drink", "chlorine", "bleach"], ai_db,
                              KiwixClient(ai_settings.kiwix_url), ai_settings)
    assert calls == ["make water safe drink chlorine bleach", "water chlorine bleach"]
    assert [p.url for p in passages] == ["/medical/card/heart-attack", "/p/water-disinfection", "/m/water"]


@pytest.mark.anyio
async def test_retrieve_does_not_retry_with_three_or_fewer_terms(monkeypatch, ai_db, ai_settings):
    calls = []

    async def fake_run_search(q, conn, kiwix, settings, fts_mode="or"):
        calls.append(q)
        return hits_for(("Water", "/m/water", "playbooks", "module"))

    monkeypatch.setattr(ai, "run_search", fake_run_search)
    passages = await retrieve(["water", "safe"], ai_db, None, ai_settings)
    assert calls == ["water safe"] and len(passages) == 1


@pytest.mark.anyio
async def test_retrieve_skips_failed_fetches_and_fills_from_later_hits(monkeypatch, ai_db, ai_settings, raw_routes):
    from sos.kiwix import KiwixClient

    async def fake_run_search(q, conn, kiwix, settings, fts_mode="or"):
        return hits_for(
            ("Missing", f"/read/{WIKI}/Does_not_exist", WIKI, "article"),
            ("Myocardial infarction", f"/read/{WIKI}/Myocardial_infarction", WIKI, "article"),
            ("Unknown doc", "/doc/nope#page=3", "nope", "doc"),
            ("Heart attack", "/medical/card/heart-attack", "playbooks", "card"),
        )

    monkeypatch.setattr(ai, "run_search", fake_run_search)
    passages = await retrieve(["heart", "attack"], ai_db, KiwixClient(ai_settings.kiwix_url), ai_settings)
    assert [p.title for p in passages] == ["Myocardial infarction", "Heart attack"]
    assert [p.n for p in passages] == [1, 2]


@pytest.mark.anyio
async def test_retrieve_returns_empty_for_no_terms_or_only_places_and_items(monkeypatch, ai_db, ai_settings):
    async def only_places(q, conn, kiwix, settings, fts_mode="or"):
        return hits_for(("Oxford", "/map?lat=1&lon=2&z=12&label=Oxford", "places", "place"),
                        ("Wikipedia", "/library", "library", "item"))

    monkeypatch.setattr(ai, "run_search", only_places)
    assert await retrieve([], ai_db, None, ai_settings) == []
    assert await retrieve(["oxford"], ai_db, None, ai_settings) == []

@pytest.mark.anyio
async def test_title_only_archive_is_searched_and_relevant_text_wins(monkeypatch, ai_db, ai_settings):
    from unittest.mock import AsyncMock
    ai_db.execute("UPDATE library_items SET fts=0 WHERE id=?", (WIKI,))
    ai_db.commit()
    async def search(*args, **kwargs):
        return {"results": [{"title": "Battery market", "url": f"/read/{WIKI}/Market", "source": "reference", "kind": "article", "score": .3}]}
    monkeypatch.setattr(ai.sos_search, "search", search)
    k = SimpleNamespace(suggest=AsyncMock(return_value=[{"value": "Replace a battery", "path": "Guide"}]),
                        raw_article=AsyncMock(side_effect=lambda book, path: '<p>Replace the battery by opening the case.</p>' if path == 'Guide' else '<p>A stock market report.</p>'))
    hits = await run_search('replace battery', ai_db, k, ai_settings)
    assert k.suggest.await_count > 0
    assert hits[0].url.endswith('/Guide')
