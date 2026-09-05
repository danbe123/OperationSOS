# api/tests/test_ai_health.py
from pathlib import Path

import httpx
import pytest

from sos.ai import Verbatim, edit_distance, match_rank, query_variants, suggest_terms, title_key, verbatim_block
from sos.ai_terms import is_medical
from sos.kiwix import KiwixClient

FIXTURES = Path(__file__).parent / "fixtures" / "ai"
NHS = "nhs.uk_en_medicines_2025-12"
PARA_PATH = "www.nhs.uk/medicines/paracetamol-for-adults/"

# Real /kiwix/suggest entries from the sample NHS Medicines ZIM (labels shortened).
PARA_ENTRIES = [
    {"value": "About paracetamol for adults - NHS", "label": "About <b>paracetamol</b>...", "kind": "path",
     "path": "www.nhs.uk/medicines/paracetamol-for-adults/about-paracetamol-for-adults/"},
    {"value": "Co-codamol for adults: painkiller containing paracetamol and codeine - NHS", "label": "", "kind": "path",
     "path": "www.nhs.uk/medicines/co-codamol-for-adults/"},
    {"value": "Paracetamol for children: medicine for pain and high temperature - NHS", "label": "", "kind": "path",
     "path": "www.nhs.uk/medicines/paracetamol-for-children/"},
    {"value": "Paracetamol for adults: painkiller for pain and high temperature - NHS", "label": "", "kind": "path",
     "path": PARA_PATH},
    {"value": "para ", "label": "containing 'para'...", "kind": "pattern"},
]
HEART_ENTRIES = [{"value": "Heart attack - NHS", "label": "", "kind": "path", "path": "www.nhs.uk/conditions/heart-attack/"}]


@pytest.fixture
def health_routes(kiwix_mock):
    nhs_html = (FIXTURES / "nhs_paracetamol.html").read_text(encoding="utf-8")
    table = {"paracetamol": PARA_ENTRIES, "parac": PARA_ENTRIES, "heart attack": HEART_ENTRIES}

    def suggest(request):
        term = request.url.params.get("term", "")
        content = request.url.params.get("content", "")
        return httpx.Response(200, json=table.get(term, []) if content == NHS else [])

    def raw(request, book, path):
        if book == NHS and path == PARA_PATH:
            return httpx.Response(200, text=nhs_html)
        return httpx.Response(404, text="not found")

    kiwix_mock.get(url__regex=r"http://kiwix\.test/kiwix/suggest\?.*").mock(side_effect=suggest)
    kiwix_mock.get(url__regex=r"http://kiwix\.test/kiwix/raw/(?P<book>[^/]+)/content/(?P<path>.+)").mock(side_effect=raw)
    return kiwix_mock


@pytest.fixture
def kiwix(ai_settings):
    return KiwixClient(ai_settings.kiwix_url)


# --- pure helpers -----------------------------------------------------------

def test_edit_distance():
    assert edit_distance("paracetamol", "paracetemol") == 1
    assert edit_distance("", "ab") == 2 and edit_distance("abc", "abc") == 0
    assert edit_distance("kitten", "sitting") == 3


def test_title_key_strips_nhs_suffix_subtitle_and_punctuation():
    assert title_key("Paracetamol for adults: painkiller for pain and high temperature - NHS") == "paracetamol for adults"
    assert title_key("CPR (adult)") == "cpr adult"
    assert title_key("  Heart attack - NHS") == "heart attack"


def test_match_rank_exact_prefix_and_typos():
    assert match_rank("heart attack", "heart attack") == 0
    assert match_rank("paracetamol", "paracetamol for adults") == 1          # prefix at a word boundary
    assert match_rank("paracetemol", "paracetamol for adults") == 1          # one edit, query length 11
    assert match_rank("burn", "burns and scalds") == 1                       # one edit allowed at length 4
    assert match_rank("cpr", "cpr adult") == 1                               # exact prefix, any length
    assert match_rank("car", "cardiac arrest") is None                       # not at a word boundary
    assert match_rank("take", "taking paracetamol") is None                  # three edits
    assert match_rank("paracetamol", "about paracetamol for adults") is None
    assert match_rank("", "x") is None and match_rank("x", "") is None


def test_query_variants_and_suggest_terms():
    assert query_variants(["much", "paracetamol", "take"]) == [
        "much paracetamol take", "much paracetamol", "paracetamol take", "much", "paracetamol", "take"]
    assert query_variants(["cpr"]) == ["cpr"]
    assert suggest_terms(["paracetemol"]) == ["paracetemol", "parac"]
    assert suggest_terms(["how", "much", "paracetamol", "ibuprofen", "together", "safely"]) == [
        "how much paracetamol ibuprofen together safely", "parac", "ibupr", "toget"]


# --- verbatim_block ---------------------------------------------------------

@pytest.mark.anyio
async def test_card_exact_title_returns_card_paragraphs(ai_db, kiwix, health_routes):
    v = await verbatim_block("heart attack", ai_db, kiwix)
    assert v == Verbatim(
        title="Heart attack", url="/medical/card/heart-attack", as_at=None,
        paragraphs=["Call 999 now. Sit the person down with their knees bent and keep them calm and still.",
                    "Give one 300 mg aspirin to chew slowly if they are not allergic and can swallow."])


@pytest.mark.anyio
async def test_card_beats_nhs_page_on_equal_rank(ai_db, kiwix, health_routes):
    # the fake NHS suggest also returns "Heart attack - NHS" for this term; the quick card must win the tie
    v = await verbatim_block("heart attack", ai_db, kiwix)
    assert v is not None and v.url == "/medical/card/heart-attack"


@pytest.mark.anyio
async def test_nhs_prefix_title_returns_first_two_paragraphs_and_as_at(ai_db, kiwix, health_routes):
    v = await verbatim_block("paracetamol", ai_db, kiwix)
    assert v is not None
    assert v.title == "Paracetamol for adults: painkiller for pain and high temperature"
    assert v.url == f"/read/{NHS}/{PARA_PATH}"
    assert v.as_at == "2025-12-15"
    assert v.paragraphs == [
        "Find out how paracetamol for adults treats aches, pains and high temperature, and how to take it.",
        "Paracetamol is a common painkiller used to treat aches and pain. It can also be used to reduce a high temperature."]


@pytest.mark.anyio
async def test_typo_matches_via_five_letter_stem_suggest(ai_db, kiwix, health_routes):
    v = await verbatim_block("paracetemol", ai_db, kiwix)
    assert v is not None and v.url.endswith(PARA_PATH)


@pytest.mark.anyio
async def test_single_medical_token_inside_a_longer_query_matches(ai_db, kiwix, health_routes):
    v = await verbatim_block("much paracetamol take", ai_db, kiwix)
    assert v is not None and v.url.endswith(PARA_PATH)


@pytest.mark.anyio
async def test_no_title_match_returns_none_even_when_keywords_are_medical(ai_db, kiwix, health_routes):
    assert await verbatim_block("car battery", ai_db, kiwix) is None
    assert await verbatim_block("chest hurts", ai_db, kiwix) is None
    assert is_medical(["chest", "hurts"])            # keyword-only: boost and disclaimer, no verbatim
    assert await verbatim_block("", ai_db, kiwix) is None


@pytest.mark.anyio
async def test_only_available_nhs_books_are_queried(ai_db, kiwix, health_routes):
    await verbatim_block("paracetamol", ai_db, kiwix)
    suggest_calls = [str(c.request.url) for c in health_routes.calls if "/suggest" in str(c.request.url)]
    assert suggest_calls and all(f"content={NHS}" in u for u in suggest_calls)
    assert not any("content=nhs_uk" in u for u in suggest_calls)      # nhs_uk is available = 0 in the fixture


@pytest.mark.anyio
async def test_suggest_failure_is_tolerated(ai_db, kiwix, kiwix_mock):
    kiwix_mock.get(url__regex=r"http://kiwix\.test/kiwix/suggest\?.*").mock(side_effect=httpx.ConnectError("down"))
    v = await verbatim_block("heart attack", ai_db, kiwix)
    assert v is not None and v.url == "/medical/card/heart-attack"
