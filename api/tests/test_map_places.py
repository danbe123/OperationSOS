"""Map places: the guidance behind a tapped place on the map (map places spec, 2026-09-07)."""
from pathlib import Path

import yaml

from sos import map_places
from sos.content import validate_tree
from sos.manifest import load_manifests

REPO = Path(__file__).resolve().parents[2]
PB = REPO / "playbooks"
KINDS = ["hospital", "pharmacy", "gp", "clinic", "fuel", "water-works", "reservoir", "spring", "rail-station",
         "airport", "military", "nuclear", "chemical", "flood-zone", "footpath", "access-land"]


def test_places_yaml_has_every_kind_with_guidance_and_a_link():
    places = map_places.load_places(PB / "map" / "places.yaml")
    assert sorted(places) == sorted(KINDS)
    for kind, place in places.items():
        words = len(place.expect.split())
        assert 40 <= words <= 120, (kind, words)
        assert "](page:" in place.expect or "](module:" in place.expect or "](card:" in place.expect, kind
        assert place.link.split(":")[0] in {"page", "module", "card"}, kind
        assert place.title


def test_places_validate_clean_against_the_real_tree():
    items = load_manifests(REPO / "manifest")
    overlay_ids = {i.overlay.id for i in items if i.overlay}
    assert validate_tree(PB, items, overlay_ids) == []


SLUGS = {"page": {"fuel-and-power"}, "module": set(), "card": set(), "scenario": set()}


def _tree(tmp_path, src: dict):
    """A playbooks directory holding just `map/`, so validate_places can be run on a doctored copy."""
    folder = tmp_path / "map"
    folder.mkdir()
    (folder / "places.yaml").write_text(yaml.safe_dump(src))
    (folder / "schema.json").write_text((PB / "map" / "schema.json").read_text())
    return tmp_path


def test_places_validation_reports_a_bad_link_and_a_missing_kind(tmp_path):
    src = yaml.safe_load((PB / "map" / "places.yaml").read_text())
    src["places"]["fuel"]["link"] = "page:no-such-page"
    del src["places"]["spring"]
    errors = map_places.validate_places(_tree(tmp_path, src), set(), set(), SLUGS, set())
    assert any("no-such-page" in e for e in errors)
    assert any("spring" in e and "missing" in e for e in errors)


def test_a_broken_link_the_paragraph_also_cites_is_reported_once(tmp_path):
    src = yaml.safe_load((PB / "map" / "places.yaml").read_text())
    fuel = src["places"]["fuel"]
    fuel["expect"] = fuel["expect"].replace(f"]({fuel['link']})", "](page:no-such-page)")
    fuel["link"] = "page:no-such-page"
    errors = map_places.validate_places(_tree(tmp_path, src), set(), set(), SLUGS, set())
    assert [e for e in errors if "no-such-page" in e] == [
        "map/places.yaml: fuel: link page:no-such-page: page 'no-such-page' does not exist"]


def test_places_endpoint_renders_html(client):
    body = client.get("/api/map/places").json()
    assert sorted(body) == sorted(KINDS)
    fuel = body["fuel"]
    assert fuel["title"] and fuel["html"].startswith("<p>") and 'href="/' in fuel["html"]
    assert fuel["link"]["href"].startswith("/") and fuel["link"]["title"]
