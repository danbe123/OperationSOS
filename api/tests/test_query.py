import sqlite3

import pytest

from sos import query


@pytest.mark.parametrize("q,tokens,fts,kiwix", [
    ("wi-fi", ["wi", "fi"], '"wi" "fi"', "wi fi"),
    ("St John's", ["st", "john", "s"], '"st" "john"', "st john"),
    ("999 vs 111", ["999", "vs", "111"], '"999" "111"', "999 111"),
    ("1:1 ratio", ["1", "ratio"], '"1" "ratio"', "1 ratio"),
    ("AND", ["and"], '"and"', "and"),
    ("What should I do if my power is cut?", ["what", "should", "i", "do", "if", "my", "power", "is", "cut"], '"power" "cut"', "power cut"),
    ("  Éowyn   STORM ", ["éowyn", "storm"], '"éowyn" "storm"', "éowyn storm"),
])
def test_reduce_query(q, tokens, fts, kiwix):
    r = query.reduce_query(q)
    assert r.tokens == tokens
    assert r.fts == fts
    assert r.kiwix == kiwix
    assert r.raw == q


def test_empty_query():
    r = query.reduce_query("   ")
    assert r.tokens == [] and r.terms == [] and r.fts == "" and r.kiwix == ""


@pytest.mark.parametrize("q", ["wi-fi", "St John's", "999 vs 111", "1:1 ratio", "AND", "NOT", "OR x", '"quoted"', "a*b", "(x)"])
def test_fts5_match_never_raises(q):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE t USING fts5(title, body, tokenize='porter unicode61 remove_diacritics 2')")
    conn.execute("INSERT INTO t VALUES ('x', 'wi fi st john 999 111 1 ratio and not or quoted a b x')")
    match = query.reduce_query(q).fts
    conn.execute("SELECT * FROM t WHERE t MATCH ?", (match,)).fetchall()


def test_stopword_list_size_and_contents():
    assert len(query.STOPWORDS) >= 200
    for w in ("what", "how", "should", "do", "if", "my", "can", "is", "the", "and", "vs", "s", "t"):
        assert w in query.STOPWORDS
    for w in ("water", "power", "bleeding", "999", "flood", "radiation"):
        assert w not in query.STOPWORDS


@pytest.mark.parametrize("s,expected", [
    ("SW1A 1AA", True), ("sw1a1aa", True), ("M1 1AE", True), ("EC1A 1BB", True), ("B33 8TH", True),
    ("SW1A", False), ("Oxford", False), ("SW1A 1A", False),
])
def test_is_postcode(s, expected):
    assert query.is_postcode(s) is expected


@pytest.mark.parametrize("s,expected", [("SW1A", True), ("m1", True), ("B33", True), ("SW1A 1AA", False), ("Oxford", False), ("S", False)])
def test_is_district(s, expected):
    assert query.is_district(s) is expected


@pytest.mark.parametrize("q,expected", [
    ("near Oxford", ["near Oxford", "Oxford"]),
    ("Oxford", ["Oxford"]),
    ("hospitals in Burnley", ["hospitals in Burnley"]),
    ("Burnley near", ["Burnley near", "Burnley"]),
    ("in", ["in"]),
    ("  near   Oxted ", ["near Oxted", "Oxted"]),
])
def test_place_candidates(q, expected):
    assert query.place_candidates(q) == expected


def test_expand_terms_takes_two_words_that_are_one_idea_as_a_phrase_group():
    from sos.query import expand_terms, fts_match_expanded
    groups = expand_terms(["safe", "power", "cut"])
    assert groups[0] == ["safe"] and groups[1][0] == "power cut" and "blackout" in groups[1] and len(groups) == 2
    assert "wound" not in groups[1]                                     # "cut" on its own would have been one
    assert fts_match_expanded(["power", "cut"]) == '("power cut" OR "power cuts" OR "blackout" OR "outage" OR "power failure")'
    assert expand_terms(["cut", "finger"])[0][:2] == ["cut", "wound"]   # not adjacent to power: a wound
