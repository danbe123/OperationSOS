"""Validates the COMMITTED --fixture build outputs under api/tests/fixtures/maps and the fixture
manifest at api/tests/fixtures/manifest/maps.json. Skipped entirely until `sos build-maps --fixture`
has been run once to produce those committed artefacts (Step 5 of the Task 10 brief)."""
import csv
import gzip
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sos.mapbuild.common import FIXTURE_BBOX, FIXTURE_MAX_BYTES, validate_geojson
from sos.mapbuild.verify import archives, check_style_sources
from tests.mapbuild_helpers import REPO

FIXTURE = REPO / "api" / "tests" / "fixtures" / "maps"
pytestmark = pytest.mark.skipif(not (FIXTURE / "test.pmtiles").exists(), reason="run `sos build-maps --fixture` first")


def test_fixture_base_is_under_5_mib():
    assert (FIXTURE / "test.pmtiles").stat().st_size < FIXTURE_MAX_BYTES


def test_fixture_styles_resolve_to_fixture_files():
    assert check_style_sources(FIXTURE) == []
    index = json.loads((FIXTURE / "styles" / "index.json").read_text())
    assert index["osm"]["tiles"] == "/maps/test.pmtiles"


def test_fixture_overlays_index_matches_files():
    index = json.loads((FIXTURE / "overlays" / "index.json").read_text())
    for overlay_id in ("footpaths", "flood-zones", "nuclear-sites", "health", "fuel", "water", "rail", "chemical-sites", "airports", "military", "access-land"):
        assert overlay_id in index
        assert (FIXTURE / index[overlay_id]["file"]).exists(), overlay_id
    nuclear = json.loads((FIXTURE / "overlays" / "nuclear-sites.geojson").read_text())
    assert validate_geojson(nuclear) == [] and len(nuclear["features"]) >= 20
    assert index["flood-zones"]["layers"] == ["flood_england"]


def test_fixture_places_are_inside_the_bbox():
    with gzip.open(FIXTURE / "places.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and list(rows[0]) == ["name", "kind", "lat", "lon", "region", "postcode"]
    assert len(rows) >= 100
    for row in rows:
        assert FIXTURE_BBOX[0] <= float(row["lon"]) <= FIXTURE_BBOX[2] and FIXTURE_BBOX[1] <= float(row["lat"]) <= FIXTURE_BBOX[3], row
    assert any(row["name"] == "Totton" and row["kind"] == "town" for row in rows)


def test_fixture_packs_index_and_manifest():
    packs = json.loads((FIXTURE / "packs" / "index.json").read_text())
    assert packs["apk"] is None and [p["id"] for p in packs["packs"]] == ["Jersey"] and packs["index_url"] == "/maps/packs/index.html"
    manifest = json.loads((REPO / "api" / "tests" / "fixtures" / "manifest" / "maps.json").read_text())
    base = next(i for i in manifest["items"] if i["id"] == "uk-ie")
    assert base["dest"] == "maps/test.pmtiles" and base["size_bytes"] == (FIXTURE / "test.pmtiles").stat().st_size
    assert "apk" not in [i["id"] for i in manifest["items"]]
    assert {"footpaths", "flood-zones"}.isdisjoint(i["id"] for i in manifest["items"]), "those two live only in manifest/overlays.json"


@pytest.mark.skipif(shutil.which("pmtiles") is None, reason="pmtiles binary not on PATH")
def test_fixture_archives_pass_pmtiles_verify_and_cover_the_bbox():
    # Sanctioned exception to the "every external tool call goes through ctx.run" rule (Ruling R10b):
    # this test exists specifically to exercise the real, committed pmtiles binary against the real,
    # committed fixture archives, so a raw subprocess.run here is the point, not a shortcut around a
    # fake runner -- there is no Context/ctx.run available in this test at all.
    found = archives(FIXTURE)
    assert len(found) >= 6
    for archive in found:
        subprocess.run(["pmtiles", "verify", str(archive)], check=True, capture_output=True)
    header = json.loads(subprocess.run(["pmtiles", "show", "--header-json", str(FIXTURE / "test.pmtiles")], check=True, capture_output=True, text=True).stdout)
    assert header["maxzoom"] == 15 and header["bounds"] == list(FIXTURE_BBOX)
