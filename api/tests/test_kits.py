"""Kits: loading, scaling, relevance, validation, the endpoints and the readiness part (kits spec)."""
from pathlib import Path

import pytest

from sos import kits

FIXTURES = Path(__file__).parent / "fixtures" / "playbooks" / "kits"


def person(**kw) -> dict:
    return {"name": "?", "age": None, "needs": "", "medications": "", "contacts": "", **kw}


def test_load_kit_reads_tiers_and_items():
    kit = kits.load_kit(FIXTURES / "water.yaml")
    assert kit.id == "water" and kit.title == "Water" and kit.order == 1
    assert [t for t in kit.tiers] == ["basic", "serious", "full"]
    assert kit.tiers["serious"]["days"] == 14
    assert [i.id for i in kit.items] == ["stored-water", "containers", "tablets", "filter"]
    assert kit.items[0].qty == {"amount": 3, "unit": "L", "per": "person-day"}
    assert kit.items[0].stock == {"category": "water", "unit": "L"}
    assert kit.items[3].qty is None and kit.items[3].stock is None and kit.items[3].link is None
    assert kit.relevant_when is None
    assert kits.load_kit(FIXTURES / "baby-child.yaml").relevant_when == {"age_under": 2}


def test_load_kits_sorts_by_order():
    assert [k.id for k in kits.load_kits(FIXTURES)] == ["water", "baby-child"]
    assert kits.load_kits(FIXTURES / "missing") == []


@pytest.mark.parametrize("qty, days, people, expected", [
    ({"amount": 3, "unit": "L", "per": "person-day"}, 14, 4, {"amount": 3, "unit": "L", "scaled": 168, "text": "168 L for 4 people over 14 days"}),
    ({"amount": 3, "unit": "L", "per": "person-day"}, 3, 1, {"amount": 3, "unit": "L", "scaled": 9, "text": "9 L for 1 person over 3 days"}),
    ({"amount": 2, "unit": "", "per": "person"}, 3, 4, {"amount": 2, "unit": "", "scaled": 8, "text": "8 for 4 people"}),
    ({"amount": 1, "unit": "pack"}, 14, 4, {"amount": 1, "unit": "pack", "scaled": 1, "text": "1 pack"}),
    ({"amount": 1.5, "unit": "kg", "per": "household"}, 14, 4, {"amount": 1.5, "unit": "kg", "scaled": 1.5, "text": "1.5 kg"}),
])
def test_scaled_quantities(qty, days, people, expected):
    item = kits.KitItem(id="x", tier="basic", name="x", qty=qty)
    assert kits.scaled(item, days, people) == expected


def test_scaled_is_none_without_qty():
    assert kits.scaled(kits.KitItem(id="x", tier="basic", name="x"), 3, 1) is None


def test_relevance_age_and_needs():
    baby = kits.load_kit(FIXTURES / "baby-child.yaml")
    assert kits.relevant(baby, [person(age=40), person(age=1)]) is True
    assert kits.relevant(baby, [person(age=40), person(age=2)]) is False
    assert kits.relevant(baby, []) is False
    always = kits.load_kit(FIXTURES / "water.yaml")
    assert kits.relevant(always, []) is True
    pets = kits.Kit(id="p", title="Pets", icon="heart", order=1, summary="x" * 20, intro="", sources=[],
                    relevant_when={"needs_any": ["dog", "cat"]}, tiers=always.tiers, items=[], path=always.path, mtime=0.0)
    assert kits.relevant(pets, [person(needs="Walks the DOG daily")]) is True
    assert kits.relevant(pets, [person(medications="catapres")]) is True   # substring match, as the rules engine does
    assert kits.relevant(pets, [person(needs="asthma")]) is False


def test_basic_progress_counts_only_basic_items():
    kit = kits.load_kit(FIXTURES / "water.yaml")
    assert kits.basic_progress(kit, set()) == (0, 2)
    assert kits.basic_progress(kit, {"stored-water", "tablets", "filter"}) == (1, 2)
