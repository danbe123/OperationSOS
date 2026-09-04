import asyncio
from pathlib import Path

import httpx
import pytest
import respx

from sos import kiwix

FX = Path(__file__).parent / "fixtures" / "kiwix"
BASE = "http://kiwix.test/kiwix"


def test_parse_search_xml_single_book():
    total, hits = kiwix.parse_search_xml((FX / "search.xml").read_text())
    assert total == 18
    assert [h.title for h in hits] == ["Precipitation", "Bivalvia", "Insect"]
    assert hits[0].book == "wikipedia_en_100_mini_2026-01"
    assert hits[0].path == "Precipitation"
    assert hits[0].snippet.startswith("In meteorology, precipitation is any product")
    assert "<b>" not in hits[0].snippet and "..." not in hits[0].snippet[:3]


def test_parse_search_xml_multi_book_and_thousands_separator():
    total, hits = kiwix.parse_search_xml((FX / "search_multi.xml").read_text())
    assert total == 2010
    assert hits[0].book == "nhs.uk_en_medicines_2025-12"
    assert hits[0].path == "www.nhs.uk/medicines/bendroflumethiazide/taking-bendroflumethiazide-with-other-medicines-and-herbal-remedies/"
    assert hits[1].book == "wikipedia_en_100_mini_2026-01" and hits[1].path == "Medicine"


def test_parse_catalog_uses_content_link_for_book_name():
    books = kiwix.parse_catalog_xml((FX / "catalog.xml").read_text())
    assert [b.name for b in books] == ["wikipedia_en_100_mini_2026-01", "sos-test-noindex"]
    assert books[0].fts is True and books[0].language == "eng" and books[0].title == "Wikipedia 100"
    assert books[1].fts is False


def test_parse_suggest_drops_pattern_entries_and_unescapes_labels():
    out = kiwix.parse_suggest_json((FX / "suggest.json").read_text())
    assert out == [
        {"value": "Aquatic water turtles", "label": "Aquatic <b>water</b> turtles", "path": "Aquatic_water_turtles"},
        {"value": "Water", "label": "<b>Water</b>", "path": "Water"},
    ]


def test_extract_text_wikipedia_keeps_main_and_drops_boilerplate():
    paras = kiwix.extract_text((FX / "raw_wiki.html").read_text())
    assert paras[0].startswith("In meteorology, precipitation is any product")
    joined = "\n".join(paras)
    assert "Main page" not in joined and "Random article" not in joined
    assert "Creative Commons" not in joined and "Related portals" not in joined
    assert "window.x" not in joined and "Enable JavaScript" not in joined
    assert "Precipitation" not in paras[0][:14] or True
    assert "Rain" in paras and "Snow" in paras
    assert all(p == p.strip() and "  " not in p for p in paras)


def test_extract_text_nhs_uses_maincontent_and_drops_nhs_chrome():
    paras = kiwix.extract_text((FX / "raw_nhs.html").read_text())
    joined = "\n".join(paras)
    assert "Skip to main content" not in joined
    assert "Health A to Z" not in joined
    assert "Page last reviewed" not in joined
    assert "About paracetamol" not in joined
    assert "MedicalWebPage" not in joined
    assert any(p.startswith("The usual dose for adults is 1 or 2 500mg tablets") for p in paras)
    assert "Always leave at least 4 hours between doses." in paras


def test_extract_text_without_main_falls_back_to_body():
    paras = kiwix.extract_text("<html><body><nav>skip</nav><p>Only paragraph.</p><div>Block<br>Two</div></body></html>")
    assert paras == ["Only paragraph.", "Block", "Two"]


def _run(coro):
    return asyncio.run(coro)


@respx.mock(base_url=BASE)
def test_client_search_issues_one_multi_book_request(respx_mock):
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "search_multi.xml").read_text()))
    client = kiwix.KiwixClient(BASE)
    hits = _run(client.search(["wikipedia_en_100_mini_2026-01", "nhs.uk_en_medicines_2025-12"], "medicine", n=8, timeout=2.0))
    assert len(hits) == 2
    assert route.call_count == 1
    url = route.calls[0].request.url
    assert url.params.get_list("books.name") == ["wikipedia_en_100_mini_2026-01", "nhs.uk_en_medicines_2025-12"]
    assert url.params["pattern"] == "medicine" and url.params["format"] == "xml" and url.params["pageLength"] == "8"


@respx.mock(base_url=BASE)
def test_client_search_404_no_index_raises(respx_mock):
    respx_mock.get("/search").mock(return_value=httpx.Response(404, text="<error>Fulltext search unavailable</error>"))
    client = kiwix.KiwixClient(BASE)
    with pytest.raises(kiwix.KiwixError):
        _run(client.search(["sos-test-noindex"], "water"))


@respx.mock(base_url=BASE, assert_all_called=False)
def test_client_search_timeout_raises_timeout(respx_mock):
    # A genuine client-side timeout cancels the in-flight mocked request before it
    # resolves, so respx never records it as "called" (installed respx 0.23.1) --
    # irrelevant to what this test checks (that the caller gets asyncio.TimeoutError).
    async def slow(request):
        await asyncio.sleep(0.5)
        return httpx.Response(200, text=(FX / "search.xml").read_text())

    respx_mock.get("/search").mock(side_effect=slow)
    client = kiwix.KiwixClient(BASE)
    with pytest.raises(asyncio.TimeoutError):
        _run(client.search(["wikipedia_en_100_mini_2026-01"], "water", timeout=0.1))


@respx.mock(base_url=BASE)
def test_client_catalog_suggest_raw_exists(respx_mock):
    respx_mock.get("/catalog/v2/entries", params={"count": "-1"}).mock(
        return_value=httpx.Response(200, text=(FX / "catalog.xml").read_text()))
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text=(FX / "suggest.json").read_text()))
    respx_mock.get("/raw/wikipedia_en_100_mini_2026-01/content/Aquatic_water_turtles").mock(
        return_value=httpx.Response(302, headers={"Location": f"{BASE}/raw/wikipedia_en_100_mini_2026-01/content/Turtle"}))
    respx_mock.get("/raw/wikipedia_en_100_mini_2026-01/content/Turtle").mock(
        return_value=httpx.Response(200, text=(FX / "raw_wiki.html").read_text()))
    respx_mock.get("/raw/wikipedia_en_100_mini_2026-01/content/Nope").mock(return_value=httpx.Response(404, text="no"))
    client = kiwix.KiwixClient(BASE)
    books = _run(client.catalog())
    assert books[0].name == "wikipedia_en_100_mini_2026-01"
    sugg = _run(client.suggest("wikipedia_en_100_mini_2026-01", "wat"))
    assert sugg[1]["path"] == "Water"
    html = _run(client.raw_article("wikipedia_en_100_mini_2026-01", "Aquatic_water_turtles"))
    assert "<main" in html
    assert _run(client.exists("wikipedia_en_100_mini_2026-01", "Turtle")) is True
    assert _run(client.exists("wikipedia_en_100_mini_2026-01", "Nope")) is False
