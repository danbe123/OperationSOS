"""Kits: loading, scaling, validation and the endpoints (kits spec, cut back by the no-setup spec)."""
from pathlib import Path

import pytest

from sos import kits

FIXTURES = Path(__file__).parent / "fixtures" / "playbooks" / "kits"


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


def test_every_kit_is_relevant():
    """No register to test a gate against, so a kit is never hidden: `relevant_when` stays as content."""
    assert kits.relevant(kits.load_kit(FIXTURES / "water.yaml")) is True
    assert kits.relevant(kits.load_kit(FIXTURES / "baby-child.yaml")) is True


@pytest.mark.parametrize("people, expected", [(1, 1), (2, 2), (7, 7), (0, 1), (-4, 1)])
def test_matching_people_is_the_setting_never_below_one(people, expected):
    """A gated kit scales by the household count like any other: the box cannot count the babies."""
    for name in ("water.yaml", "baby-child.yaml"):
        assert kits.matching_people(kits.load_kit(FIXTURES / name), people) == expected


import shutil

from sos import content
from sos import content as content_mod
from sos.manifest import load_manifests

REPO = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).parent / "fixtures"
OVERLAYS = {"health", "water", "fuel", "flood", "nuclear-sites"}


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "playbooks"
    shutil.copytree(FIXTURE_ROOT / "playbooks", root)
    shutil.copy(REPO / "playbooks" / "schema.json", root / "schema.json")
    shutil.copy(REPO / "playbooks" / "kits" / "schema.json", root / "kits" / "schema.json")
    return root


@pytest.fixture
def items():
    return load_manifests(FIXTURE_ROOT / "manifest")


def test_validate_tree_accepts_fixture_kits(tree, items):
    assert [e for e in content.validate_tree(tree, items, OVERLAYS) if not e.startswith("warning:")] == []


def test_validate_tree_reports_kit_problems(tree, items):
    (tree / "kits" / "water.yaml").write_text((tree / "kits" / "water.yaml").read_text(encoding="utf-8")
        .replace("link: module:water\n  - id: containers", "link: module:nowhere\n  - id: containers")
        .replace("id: filter\n", "id: tablets\n"), encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("kits/water.yaml: link module:nowhere: module 'nowhere' does not exist" in line for line in out), out
    assert any("kits/water.yaml: item 'tablets': duplicate id" in line for line in out), out


def test_validate_tree_reports_kit_schema_and_tier_order(tree, items):
    text = (tree / "kits" / "water.yaml").read_text(encoding="utf-8").replace("days: 90", "days: 2").replace("icon: water\n", "")
    (tree / "kits" / "water.yaml").write_text(text, encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("kits/water.yaml: tiers: days must increase" in line for line in out), out
    assert any("kits/water.yaml: file: 'icon' is a required property" in line for line in out), out


def test_validate_deep_checks_kit_links_and_sources(tree, items):
    seen = []

    def kiwix_check(book, path):
        seen.append((book, path))
        return path != "A/Water"

    def doc_check(item):
        return item.id != "sos-test-pdf"

    # A doc: link in a kit's why, and a doc: source, so both halves of the deep check have something
    # to bite on: the fixture kit cites only kiwix.
    path = tree / "kits" / "water.yaml"
    path.write_text(path.read_text(encoding="utf-8")
                    .replace("why: Turns any water into drinking water once tablets run out.",
                             "why: Turns any water into drinking water ([the guide](doc:sos-test-pdf))."),
                    encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS, kiwix_check=kiwix_check, doc_check=doc_check)
    # Both fixture kits cite the article, and the water kit cites it twice -- in a why and in its own
    # sources -- so it is asked for once per kit, not once per mention.
    assert seen.count(("wikipedia_en_100_mini_2026-01", "A/Water")) == 2
    assert "kits/water.yaml: kiwix:wikipedia_en_100_mini_2026-01/A/Water returned non-200" in out
    assert "kits/baby-child.yaml: kiwix:wikipedia_en_100_mini_2026-01/A/Water returned non-200" in out
    assert any("kits/water.yaml: doc 'sos-test-pdf' file missing" in e for e in out), out


def test_validate_without_deep_checkers_asks_nothing_of_the_kits(tree, items):
    asked = []
    out = content.validate_tree(tree, items, OVERLAYS, kiwix_check=None,
                                doc_check=lambda item: asked.append(item) or True)
    # No kiwix checker, so no kiwix line -- and the doc checker is the only one that ran.
    assert not [e for e in out if "returned non-200" in e]
    assert asked


def test_content_cache_serves_kits(tree):
    cache = content.ContentCache(tree)
    assert [k.id for k in cache.kits()] == ["water", "baby-child"]
    assert cache.kit("water").title == "Water"
    assert cache.kit("nope") is None and cache.kit("../water") is None
    first = cache.kit("water")
    assert cache.kit("water") is first                      # cached while the file is unchanged
    path = tree / "kits" / "water.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("title: Water", "title: Water (edited)"), encoding="utf-8")
    import os
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
    assert cache.kit("water").title == "Water (edited)"


def test_kits_list_reports_relevance_and_progress(client):
    r = client.get("/api/kits")
    assert r.status_code == 200
    body = r.json()
    assert body["people"] == 2
    water, baby = body["kits"]
    assert water["slug"] == "water" and water["relevant"] is True
    assert water["tiers"] == {"basic": {"done": 0, "total": 2}, "serious": {"done": 0, "total": 1}, "full": {"done": 0, "total": 1}}
    assert baby["slug"] == "baby-child" and baby["relevant"] is True


def test_kit_detail_scales_to_the_people_setting(client):
    kit = client.get("/api/kits/water").json()
    assert kit["slug"] == "water" and kit["people"] == 2 and kit["relevant"] is True
    assert "module" in kit["intro_html"] and "/m/water" in kit["intro_html"]
    basic, serious, full = kit["tiers"]
    assert (basic["id"], basic["days"], basic["total"], basic["done"]) == ("basic", 3, 2, 0)
    stored = basic["items"][0]
    assert stored["id"] == "stored-water" and stored["qty"]["text"] == "18 L for 2 people over 3 days"
    assert stored["checked"] is False and stored["href"] == "/m/water"
    assert basic["items"][1]["qty"]["text"] == "4 for 2 people"
    assert serious["items"][0]["qty"]["text"] == "1 pack" and serious["days"] == 14
    assert full["items"][0]["qty"] is None and full["items"][0]["href"] is None
    assert client.get("/api/kits/nope").status_code == 404


def test_a_gated_kit_scales_by_the_same_count_as_any_other(client):
    client.put("/api/settings/people", json={"people": 4})
    kit = client.get("/api/kits/baby-child").json()
    assert kit["relevant"] is True and kit["people"] == 4
    nappies = kit["tiers"][0]["items"][0]
    assert nappies["id"] == "nappies"
    assert nappies["qty"]["scaled"] == 72 and nappies["qty"]["text"] == "72 for 4 people over 3 days"
    assert client.get("/api/kits/water").json()["people"] == 4
    assert client.get("/api/kits").json()["people"] == 4


def test_a_tick_is_kept_and_can_be_taken_back(client):
    r = client.put("/api/kits/water/items/stored-water", json={"checked": True})
    assert r.status_code == 200
    item = r.json()["tiers"][0]["items"][0]
    assert item["checked"] is True and item["updated_at"]
    assert client.put("/api/kits/water/items/stored-water", json={"checked": False}).json()["tiers"][0]["items"][0]["checked"] is False
    assert client.put("/api/kits/water/items/nothing", json={"checked": True}).status_code == 404


def test_reset_clears_ticks_only_for_that_kit(client):
    client.put("/api/kits/water/items/stored-water", json={"checked": True})
    client.put("/api/kits/water/items/tablets", json={"checked": True})
    client.put("/api/kits/baby-child/items/nappies", json={"checked": True})
    kit = client.delete("/api/kits/water/ticks").json()
    assert all(not i["checked"] for t in kit["tiers"] for i in t["items"])
    assert client.get("/api/kits/baby-child").json()["tiers"][0]["items"][0]["checked"] is True
    assert client.get("/api/playbooks/grid-collapse").json()["checklist"]     # scenario ticks untouched by kit keys


def test_have_lists_every_ticked_item_in_kit_and_tier_order(client):
    """`GET /kits/have`: the one list of what this household has, kits in their order and items in the
    kit's own -- basic, then serious, then full -- whatever order the ticks were made in."""
    client.put("/api/kits/water/items/tablets", json={"checked": True})       # serious, ticked first
    client.put("/api/kits/water/items/stored-water", json={"checked": True})  # basic, ticked second
    body = client.get("/api/kits/have").json()
    assert body["people"] == 2
    # A kit with nothing ticked is left out rather than shown as an empty heading.
    assert [k["slug"] for k in body["kits"]] == ["water"]
    water = body["kits"][0]
    assert water["title"] == "Water" and water["icon"] == "water"
    assert [(i["id"], i["tier"]) for i in water["items"]] == [("stored-water", "basic"), ("tablets", "serious")]
    assert water["items"][0]["name"] == "Drinking water in sealed containers"
    assert all(i["updated_at"] for i in water["items"])
    # The same scaled sentence the kit's own page gives, so the two screens never disagree.
    detail = client.get("/api/kits/water").json()
    assert water["items"][0]["qty"] == detail["tiers"][0]["items"][0]["qty"] == {
        "amount": 3, "unit": "L", "scaled": 18, "text": "18 L for 2 people over 3 days"}
    assert water["items"][1]["qty"]["text"] == "1 pack"

    client.put("/api/kits/baby-child/items/nappies", json={"checked": True})
    body = client.get("/api/kits/have").json()
    assert [k["slug"] for k in body["kits"]] == ["water", "baby-child"]       # kits in their own order
    assert [i["qty"]["text"] for i in body["kits"][1]["items"]] == ["36 for 2 people over 3 days"]


def test_have_drops_a_row_the_moment_it_is_unticked(client):
    client.put("/api/kits/water/items/stored-water", json={"checked": True})
    client.put("/api/kits/water/items/tablets", json={"checked": True})
    client.put("/api/kits/water/items/tablets", json={"checked": False})
    body = client.get("/api/kits/have").json()
    assert [i["id"] for i in body["kits"][0]["items"]] == ["stored-water"]
    client.delete("/api/kits/water/ticks")
    assert client.get("/api/kits/have").json()["kits"] == []


def test_why_and_note_come_back_as_inline_html(client):
    tablets = client.get("/api/kits/water").json()["tiers"][1]["items"][0]
    assert tablets["id"] == "tablets"
    assert tablets["why"].endswith("([Prepare](kiwix:wikipedia_en_100_mini_2026-01/A/Water)).")     # the raw text stays
    assert tablets["why_html"] == ('One pack treats a fortnight of water '
                                   '(<a href="/read/wikipedia_en_100_mini_2026-01/A/Water">Prepare</a>).')
    assert tablets["note_html"] == "Check the use-by date."                 # no paragraph wrapper around a row
    assert client.get("/api/kits/water").json()["tiers"][0]["items"][1]["why_html"] == ""


def test_a_two_paragraph_why_comes_back_whole(client, tmp_path, monkeypatch):
    """A row's why is unwrapped only when there is one paragraph to unwrap: stripping the outer tags
    off two of them by position leaves `first</p><p>second` on the screen."""
    from sos.routers import kits as kits_router

    class FakeRequest:
        class app:
            class state:
                class content:
                    resolver = staticmethod(content_mod.resolve_link)

    one = kits_router._inline("One line ([Prepare](kiwix:wikipedia_en_100_mini_2026-01/A/Water)).", FakeRequest)
    assert one == 'One line (<a href="/read/wikipedia_en_100_mini_2026-01/A/Water">Prepare</a>).'
    two = kits_router._inline("First paragraph.\n\nSecond paragraph.", FakeRequest)
    assert two == "<p>First paragraph.</p>\n<p>Second paragraph.</p>"
    assert kits_router._inline("", FakeRequest) == ""


# --- the people setting (no-setup spec section 3) --------------------------------------------------------------

def test_the_kit_list_reports_the_people_setting(client):
    assert client.get("/api/kits").json()["people"] == 2
    client.put("/api/settings/people", json={"people": 4})
    assert client.get("/api/kits").json()["people"] == 4


def test_a_kit_rescales_when_the_count_changes(client):
    kit = client.get("/api/kits/water").json()
    assert kit["people"] == 2
    assert kit["tiers"][0]["items"][0]["qty"]["text"] == "18 L for 2 people over 3 days"
    client.put("/api/settings/people", json={"people": 4})
    kit = client.get("/api/kits/water").json()
    assert kit["people"] == 4
    assert kit["tiers"][0]["items"][0]["qty"]["text"] == "36 L for 4 people over 3 days"


def test_every_kit_is_relevant_with_nothing_typed_in(client):
    body = client.get("/api/kits").json()
    assert all(k["relevant"] is True for k in body["kits"])
    assert client.get("/api/kits/baby-child").json()["relevant"] is True


def test_a_kit_item_takes_a_tick_and_nothing_else(client):
    r = client.put("/api/kits/water/items/stored-water", json={"checked": True, "stock": {"quantity": 9}})
    assert r.status_code == 422
    r = client.put("/api/kits/water/items/stored-water", json={"checked": True})
    assert r.status_code == 200
    item = r.json()["tiers"][0]["items"][0]
    assert item["checked"] is True and "stock_item" not in item and "stock" not in item
