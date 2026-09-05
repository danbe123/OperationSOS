# api/tests/test_ai_terms.py
import re

from sos.ai_terms import MEDICAL_TERMS, is_medical


def test_terms_are_normalised_and_plentiful():
    assert len(MEDICAL_TERMS) >= 200
    for term in MEDICAL_TERMS:
        assert term == term.strip().lower(), term
        assert re.fullmatch(r"[a-z0-9]+( [a-z0-9]+)*", term), term  # tokenised form only


def test_uk_drug_names_present_and_us_names_absent():
    for uk in ("paracetamol", "ibuprofen", "co codamol", "salbutamol", "chlorphenamine", "loperamide", "adrenaline"):
        assert uk in MEDICAL_TERMS, uk
    for us in ("acetaminophen", "tylenol", "epinephrine", "albuterol"):
        assert us not in MEDICAL_TERMS, us


def test_single_token_matches():
    assert is_medical(["paracetamol"])
    assert is_medical(["hypothermia"])
    assert is_medical(["burn"])


def test_plural_and_phrase_matches():
    assert is_medical(["burns"])                       # plural of a listed word
    assert is_medical(["heart", "attack"])             # bigram
    assert is_medical(["oral", "rehydration", "salts"])  # bigram inside a longer query
    assert is_medical(["carbon", "monoxide", "poisoning"])


def test_non_medical_queries_do_not_match():
    assert not is_medical(["car", "battery"])
    assert not is_medical(["fix", "phone", "screen"])
    assert not is_medical(["nuclear", "fallout", "shelter"])
    assert not is_medical(["pmr446", "channels"])
    assert not is_medical([])


def test_case_insensitive_input():
    assert is_medical(["Paracetamol"])
    assert is_medical(["HEART", "Attack"])
