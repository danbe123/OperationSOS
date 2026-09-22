"""Injury intent (task 25, 2026-09-22): `query.analyse_injury` reads a plain-English description of an injury
("gash on arm", "spilled boiling water on my leg") as a condition, a place on the body and qualifiers, from the
raw words in order -- and does not read a name, a household phrase or a book request as one ("Sam Gash",
"power cut", "bike brake bleeding", "a book about treating gunshot wounds")."""
import pytest

from sos import query


@pytest.mark.parametrize("q,conditions,locations", [
    ("gash on arm", ("open_wound",), ("arm",)),
    ("deep cut leg", ("open_wound",), ("leg",)),
    ("spilled boiling water on my leg", ("burn",), ("leg",)),
    ("burned my hand on the stove", ("burn",), ("hand",)),
    ("kettle of boiling water went over my kids hand and the skin is blistering", ("burn",), ("hand", "skin")),
    ("blood won't stop", ("bleeding",), ()),
    ("can't stop the bleeding", ("bleeding",), ()),
    ("blood wont stop pouring from his arm he cut it on broken glass", ("bleeding", "open_wound"), ("arm",)),
    ("twisted my ankle badly", ("sprain",), ("ankle",)),
    ("arm bent the wrong way after the fall", ("fracture",), ("arm",)),
    ("broke my wrist", ("fracture",), ("wrist",)),
    ("nose won't stop bleeding", ("nosebleed",), ("nose",)),
    ("hit his head and he's confused", ("head_injury",), ("head",)),
    ("something stuck in my eye", ("eye_injury",), ("eye",)),
    ("bitten by a dog", ("bite_sting",), ()),
    ("stung by a wasp on my arm", ("bite_sting",), ("arm",)),
    ("broken neck", ("spinal_injury",), ("neck",)),
    ("scald", ("burn",), ()),
    ("gash", ("open_wound",), ()),
    ("bleeding", ("bleeding",), ()),
    ("burns", ("burn",), ()),
    ("severe bleeding", ("bleeding",), ()),
    ("cut myself shaving", ("open_wound",), ()),
    ("how do I treat a burn", ("burn",), ()),
    ("stabbed in the thigh losing lots of blood", ("bleeding", "open_wound"), ("thigh",)),
])
def test_an_injury_described_is_read_as_its_condition_and_place(q, conditions, locations):
    intent = query.analyse_injury(q)
    assert intent.confirmed, q
    assert intent.conditions == conditions, (q, intent)
    assert set(locations) <= set(intent.locations), (q, intent)
    assert intent.purpose == "care"


def test_the_modifiers_are_kept():
    assert "deep" in query.analyse_injury("deep cut leg").modifiers


@pytest.mark.parametrize("q", [
    "Sam Gash", "sam gash", "Olympic Arms", "power cut", "power cut what to do", "bike brake bleeding",
    "how to bleed the brakes", "bleeding the radiators", "broken link", "burn a CD", "arm wrestling rules",
    "Burn Notice", "Broken Arrow film", "Robert Burns poems", "Achilles heel meaning", "how to cut a mango",
    "chest feels crushed with pain going into my jaw and left arm and im sweating cold", "low blood sugar",
    "blood pressure", "heartburn after eating", "boil water to make it safe", "break a leg", "gash in the car door",
    "a haircut", "cut the grass", "",
])
def test_a_name_a_household_phrase_or_an_anatomy_word_is_not_an_injury(q):
    assert not query.analyse_injury(q).confirmed, (q, query.analyse_injury(q))


@pytest.mark.parametrize("q", ["a book about treating gunshot wounds", "old book on first aid for snake bites",
                               "books on burns treatment"])
def test_a_book_asked_for_is_a_book_not_an_emergency(q):
    intent = query.analyse_injury(q)
    assert intent.purpose == "book"
    assert not intent.confirmed        # `confirmed` is care intent: a book request never leads with a card


def test_a_nosebleed_is_not_severe_bleeding_and_keeps_its_anatomy():
    intent = query.analyse_injury("blood pouring from my nose")
    assert intent.conditions == ("nosebleed",)


def test_a_bleed_in_pregnancy_is_left_to_the_existing_search():
    assert "bleeding" not in query.analyse_injury("bleeding in pregnancy").conditions


def test_the_condition_retrieval_query_needs_the_condition_not_the_place():
    intent = query.analyse_injury("gash on arm")
    match = query.fts_match_conditions(intent)
    assert '"wound"' in match and '"gash"' in match and '"arm"' not in match
    assert " AND " not in match
    assert query.fts_match_conditions(query.analyse_injury("Sam Gash")) == ""


def test_a_location_specific_condition_keeps_its_anatomy_in_retrieval():
    assert '"nosebleed"' in query.fts_match_conditions(query.analyse_injury("nose won't stop bleeding"))
    assert '"eye"' in query.fts_match_conditions(query.analyse_injury("something stuck in my eye"))


def test_reduce_query_carries_the_analysis():
    assert query.reduce_query("gash on arm").injury.conditions == ("open_wound",)
    assert not query.reduce_query("water").injury.confirmed


def test_every_condition_has_retrieval_words():
    assert set(query.CONDITION_TERMS) == set(query.CONDITION_IDS)


@pytest.mark.parametrize("q", ["throat swelling up after a wasp sting and hives everywhere, do I use the epipen",
                               "stung by a bee and now she is not breathing", "cut his head and now he is unconscious"])
def test_a_graver_emergency_beside_the_injury_stands_the_injury_policy_aside(q):
    intent = query.analyse_injury(q)
    assert intent.conditions and not intent.confirmed and "other-emergency" in intent.matched_rules


@pytest.mark.parametrize("q", ["what should I do after an adder bite", "snake bit my ankle", "tick bite on my leg"])
def test_an_adder_or_tick_bite_is_the_pages_not_the_bite_cards(q):
    """The Bites and stings card sends adders and ticks to the "Ticks and adders" page: no card is led with."""
    assert not query.analyse_injury(q).confirmed
