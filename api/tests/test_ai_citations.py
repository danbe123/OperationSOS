# api/tests/test_ai_citations.py
from sos.ai import CitationFilter


def run(valid, chunks):
    f = CitationFilter(valid)
    out = "".join(f.feed(c) for c in chunks) + f.flush()
    return out, f.citations


def test_valid_citations_pass_and_are_recorded_once_in_order():
    assert run({1, 2, 3}, ["Boil it [1]. Filter first [2]. Again [1]."]) == \
        ("Boil it [1]. Filter first [2]. Again [1].", [1, 2])


def test_unknown_citation_is_dropped():
    assert run({1, 2, 3}, ["Boil it [1]. Filter [4] first [2]."]) == ("Boil it [1]. Filter  first [2].", [1, 2])


def test_citation_split_across_chunks_is_held_back_until_closed():
    f = CitationFilter({1})
    assert f.feed("see [") == "see "
    assert f.feed("1") == ""
    assert f.feed("] and [9") == "[1] and "
    assert f.feed("]") == ""
    assert f.flush() == ""
    assert f.citations == [1]


def test_bracket_text_longer_than_six_chars_is_released_verbatim():
    assert run({1}, ["[abcdef ghi] done"]) == ("[abcdef ghi] done", [])
    assert run({1}, ["[12345", "] x"]) == ("[12345] x", [])       # released at six chars; the later ] is plain text


def test_multi_citation_forms_are_normalised():
    assert run({1, 2}, ["x [1, 2] y [1,3] z"]) == ("x [1][2] y [1] z", [1, 2])
    assert run({1, 2}, ["x [3,4] y"]) == ("x  y", [])


def test_trailing_incomplete_bracket_is_released_on_flush():
    assert run({1}, ["end [2"]) == ("end [2", [])
    assert run({1}, ["end ["]) == ("end [", [])


def test_no_valid_passages_drops_every_citation():
    assert run(set(), ["A [1] B [2]."]) == ("A  B .", [])


def test_streaming_by_single_characters_matches_the_whole_string():
    text = "Take one 500 mg tablet [1], at most eight a day [2]; see [7] too [1]."
    expected = ("Take one 500 mg tablet [1], at most eight a day [2]; see  too [1].", [1, 2])
    assert run({1, 2}, [text]) == expected
    assert run({1, 2}, list(text)) == expected
