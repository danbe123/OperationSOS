import json
import shutil
from pathlib import Path

import pytest

from sos.mapbuild import verify
from sos.mapbuild.common import BuildError, FIXTURE_MAX_BYTES
from tests.mapbuild_helpers import FakeRunner, make_ctx, REPO

FIXTURE_HEADER = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 15, "bounds": [-1.56, 50.87, -1.46, 50.97]}
# manifest/maps.json ids (footpaths and flood-zones live only in manifest/overlays.json -- Ruling R6).
MANIFEST_IDS = ["uk-ie", "os-zoomstack", "contours", "hillshade", "styles", "sprites", "glyphs", "places", "packs", "apk"]
ALLOWED_KINDS = {"zim", "pmtiles", "geojson", "pdf", "epub", "dir", "model", "mwm", "apk", "style", "glyphs", "sprites", "places"}


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data))


def _synthetic_out(out: Path, base="test.pmtiles") -> None:
    """A minimal but complete output tree matching the real StylesStep/OverlaysStep/PacksStep naming
    conventions, that check_style_sources, check_overlays and output_sizes all accept."""
    for name in (base, "os-zoomstack.pmtiles", "contours.pmtiles", "hillshade.pmtiles",
                 "overlays/footpaths.pmtiles", "overlays/flood-zones.pmtiles", "overlays/water.pmtiles"):
        _write(out / name, b"pm")
    _write(out / "overlays" / "index.json", {
        "footpaths": {"kind": "pmtiles", "file": "overlays/footpaths.pmtiles", "layers": ["footpaths"]},
        "flood-zones": {"kind": "pmtiles", "file": "overlays/flood-zones.pmtiles", "layers": ["flood_england"]},
        "water": {"kind": "pmtiles", "file": "overlays/water.pmtiles", "layers": ["water"]},
        "nuclear-sites": {"kind": "geojson", "file": "overlays/nuclear-sites.geojson", "features": 20},
    })
    _write(out / "overlays" / "nuclear-sites.geojson", {"type": "FeatureCollection", "features": []})
    for face in ("Noto Sans Regular", "Source Sans Pro Regular"):
        _write(out / "fonts" / face / "0-255.pbf", b"g")
    for name in ("v4/light.json", "v4/light.png", "v4/dark.json", "v4/dark.png", "os/sprites.json", "os/sprites.png"):
        _write(out / "sprites" / name, b"s")
    style = lambda src, sprite, face: {"version": 8, "sources": {"s": {"type": "vector", "url": f"pmtiles:///maps/{src}"}}, "sprite": sprite,
                                      "glyphs": "/maps/fonts/{fontstack}/{range}.pbf",
                                      "layers": [{"id": "l", "type": "symbol", "source": "s", "source-layer": "x", "layout": {"text-font": [face]}}]}
    # Real style filenames (StylesStep Ruling R1): osm-<theme>.json and os-<theme>.json, not osm-light.json etc.
    _write(out / "styles" / "osm-field.json", style(base, "/maps/sprites/v4/light", "Noto Sans Regular"))
    _write(out / "styles" / "osm-blackout.json", style(base, "/maps/sprites/v4/dark", "Noto Sans Regular"))
    _write(out / "styles" / "osm-vault.json", style(base, "/maps/sprites/v4/dark", "Noto Sans Regular"))
    _write(out / "styles" / "os-field.json", style("os-zoomstack.pmtiles", "/maps/sprites/os/sprites", "Source Sans Pro Regular"))
    _write(out / "styles" / "os-blackout.json", style("os-zoomstack.pmtiles", "/maps/sprites/os/sprites", "Source Sans Pro Regular"))
    _write(out / "styles" / "os-vault.json", style("os-zoomstack.pmtiles", "/maps/sprites/os/sprites", "Source Sans Pro Regular"))
    _write(out / "styles" / "layers" / "contours.json", {"sources": {"contours": {"type": "vector", "url": "pmtiles:///maps/contours.pmtiles"}}, "layers": []})
    _write(out / "styles" / "layers" / "hillshade.json", {"sources": {"hillshade": {"type": "raster", "url": "pmtiles:///maps/hillshade.pmtiles"}}, "layers": []})
    _write(out / "styles" / "layers" / "footpaths.json", {"sources": {"footpaths": {"type": "vector", "url": "pmtiles:///maps/overlays/footpaths.pmtiles"}}, "layers": []})
    _write(out / "styles" / "layers" / "flood-zones.json", {"sources": {"flood-zones": {"type": "vector", "url": "pmtiles:///maps/overlays/flood-zones.pmtiles"}}, "layers": []})
    _write(out / "styles" / "layers" / "overlays.json", {"sources": {"water": {"type": "vector", "url": "pmtiles:///maps/overlays/water.pmtiles"}}, "layers": []})
    _write(out / "styles" / "index.json", {
        "osm": {"vault": "/maps/styles/osm-vault.json", "field": "/maps/styles/osm-field.json", "blackout": "/maps/styles/osm-blackout.json", "tiles": f"/maps/{base}"},
        "os": {"vault": "/maps/styles/os-vault.json", "field": "/maps/styles/os-field.json", "blackout": "/maps/styles/os-blackout.json", "tiles": "/maps/os-zoomstack.pmtiles"},
        "layers": {"contours": "/maps/styles/layers/contours.json", "hillshade": "/maps/styles/layers/hillshade.json",
                   "footpaths": "/maps/styles/layers/footpaths.json", "flood-zones": "/maps/styles/layers/flood-zones.json",
                   "overlays": "/maps/styles/layers/overlays.json"}})
    _write(out / "places.csv.gz", b"\x1f\x8b")
    _write(out / "packs" / "index.html", b"<html></html>")
    _write(out / "packs" / "index.json", {"version": "260826", "apk": None, "packs": [], "index_url": "/maps/packs/index.html"})


def test_manifest_maps_json_has_the_ten_items_with_valid_shapes():
    doc = json.loads((REPO / "manifest" / "maps.json").read_text())
    items = doc["items"]
    assert [i["id"] for i in items] == MANIFEST_IDS
    for item in items:
        assert item["kind"] in ALLOWED_KINDS and item["tier"] == "core" and item["category"] == "maps"
        assert item["source"]["type"] == "build" and item["source"]["tool"] == "sos build-maps" and item["source"]["artifact"]
        assert item["dest"].startswith("maps/") and item["size_bytes"] > 0 and item["as_at"] and item["licence"]
        assert isinstance(item["priority"], int) and item["description"]
        assert not item.get("overlay"), "footpaths and flood-zones carry the overlay object; both live only in overlays.json"
    # Ruling R2: the packs aggregate is a directory item, not an mwm file; apk is untouched.
    by_id = {i["id"]: i for i in items}
    assert by_id["packs"]["kind"] == "dir"
    assert by_id["apk"]["kind"] == "apk"
    # Ruling R6: footpaths/flood-zones must not be duplicated here -- they live in manifest/overlays.json.
    assert "footpaths" not in by_id and "flood-zones" not in by_id
    assert "NOMAD" not in json.dumps(doc)


def test_manifest_maps_json_does_not_duplicate_overlays_json_ids_or_dests():
    maps_doc = json.loads((REPO / "manifest" / "maps.json").read_text())
    overlays_doc = json.loads((REPO / "manifest" / "overlays.json").read_text())
    maps_ids = {i["id"] for i in maps_doc["items"]}
    overlays_ids = {i["id"] for i in overlays_doc["items"]}
    maps_dests = {i["dest"] for i in maps_doc["items"]}
    overlays_dests = {i["dest"] for i in overlays_doc["items"]}
    assert not (maps_ids & overlays_ids)
    assert not (maps_dests & overlays_dests)


def test_check_style_sources_accepts_a_complete_tree_and_reports_gaps(tmp_path):
    out = tmp_path / "out"
    _synthetic_out(out)
    assert verify.check_style_sources(out) == []
    (out / "contours.pmtiles").unlink()
    (out / "sprites" / "v4" / "dark.png").unlink()
    shutil.rmtree(out / "fonts" / "Source Sans Pro Regular")
    problems = verify.check_style_sources(out)
    assert any("contours.pmtiles" in p for p in problems)
    assert any("dark.png" in p or "sprites/v4/dark" in p for p in problems)
    assert any("Source Sans Pro Regular" in p for p in problems)
    (out / "styles" / "osm-field.json").write_text(json.dumps({"version": 8, "sources": {"s": {"type": "vector", "url": "https://example.test/tiles.json"}}, "layers": []}))
    assert any("not pmtiles:///maps/" in p for p in verify.check_style_sources(out))
    shutil.rmtree(out / "styles")
    assert verify.check_style_sources(out) == ["no styles under styles/"]


def test_check_style_sources_walks_nested_case_literal_text_font_expressions(tmp_path):
    """Ruling R14: `@protomaps/basemaps@5.7.2` emits `text-font` as a nested case/literal expression
    for internationalised labels (e.g. layer `places_locality`), not a flat list of face names. The
    naive "is it a list" check used to wrongly treat the condition token `"case"` as a face name and
    report a bogus missing-glyphs problem for it, while never checking the real face names nested
    inside the `["literal", [...]]` branches."""
    out = tmp_path / "out"
    _synthetic_out(out)
    nested_font = ["case", ["==", ["get", "script"], "Devanagari"],
                   ["literal", ["Noto Sans Devanagari Regular v1"]],
                   ["literal", ["Noto Sans Regular"]]]
    style = {"version": 8, "sources": {"s": {"type": "vector", "url": "pmtiles:///maps/test.pmtiles"}},
              "sprite": "/maps/sprites/v4/light", "glyphs": "/maps/fonts/{fontstack}/{range}.pbf",
              "layers": [{"id": "places_locality", "type": "symbol", "source": "s", "source-layer": "x",
                          "layout": {"text-font": nested_font}}]}
    _write(out / "styles" / "osm-field.json", style)
    problems = verify.check_style_sources(out)
    assert not any("case" in p for p in problems), problems
    assert any("Noto Sans Devanagari Regular v1" in p for p in problems), problems
    assert not any("Noto Sans Regular" in p for p in problems), problems
    _write(out / "fonts" / "Noto Sans Devanagari Regular v1" / "0-255.pbf", b"g")
    assert verify.check_style_sources(out) == []


def test_check_overlays_requires_the_index_checks_its_files_and_skips_unbuilt_ids(tmp_path):
    out = tmp_path / "out"
    overlays_manifest = tmp_path / "overlays.json"
    overlays_manifest.write_text(json.dumps({"items": [
        {"id": "footpaths", "source": {"artifact": "overlays/footpaths.pmtiles"}},
        {"id": "water", "source": {"artifact": "overlays/water.pmtiles"}},
        {"id": "access-land", "source": {"artifact": "overlays/access-land.pmtiles"}},
    ]}))
    # No overlays/index.json at all: hard failure (part a).
    assert verify.check_overlays(out, overlays_manifest) == ["overlays/index.json is missing"]

    _write(out / "overlays" / "footpaths.pmtiles", b"pm")
    _write(out / "overlays" / "index.json", {
        "footpaths": {"kind": "pmtiles", "file": "overlays/footpaths.pmtiles"},
        "water": {"kind": "pmtiles", "file": "overlays/water.pmtiles"},  # named but not actually written (part b)
    })
    problems = verify.check_overlays(out, overlays_manifest)
    assert any("water" in p and "overlays/water.pmtiles" in p for p in problems)
    # access-land is in the manifest but was never built (absent from the index): skipped, no problem raised for it.
    assert not any("access-land" in p for p in problems)

    _write(out / "overlays" / "water.pmtiles", b"pm")
    assert verify.check_overlays(out, overlays_manifest) == []


def test_check_overlays_skips_the_artifact_kind_cross_check_in_fixture_mode(tmp_path):
    """Ruling R15: access-land/airports-military/water are declared in manifest/overlays.json at their
    real production-scale kind (pmtiles), but at fixture scale every overlay's tiny sample input
    legitimately finalises as geojson under the uniform 5MB rule (Task 7's `finalise()`) -- this is
    correct fixture behaviour, not a drifted manifest, so the artifact-path cross-check must not fire
    for it when fixture=True. Full-mode (or the default) must still catch the mismatch."""
    out = tmp_path / "out"
    overlays_manifest = tmp_path / "overlays.json"
    overlays_manifest.write_text(json.dumps({"items": [
        {"id": "access-land", "kind": "pmtiles", "source": {"artifact": "overlays/access-land.pmtiles"}},
    ]}))
    _write(out / "overlays" / "access-land.geojson", b"{}")
    _write(out / "overlays" / "index.json", {
        "access-land": {"kind": "geojson", "file": "overlays/access-land.geojson"},
    })
    assert verify.check_overlays(out, overlays_manifest, fixture=True) == []
    problems = verify.check_overlays(out, overlays_manifest)
    assert any("access-land" in p and "overlays/access-land.pmtiles" in p for p in problems)
    assert verify.check_overlays(out, overlays_manifest, fixture=False) == problems


def test_output_sizes_and_manifest_update(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    _synthetic_out(ctx.out)
    (ctx.out / "packs" / "index.json").write_text(json.dumps({"version": "260826", "apk": {"file": "a.apk", "url": "/maps/packs/a.apk", "size_bytes": 64193127, "sha256": "x", "tag": "t"}, "packs": [], "index_url": "/maps/packs/index.html"}))
    sizes = verify.output_sizes(ctx)
    assert set(sizes) == set(MANIFEST_IDS)
    assert sizes["uk-ie"] == 2 and sizes["apk"] == 64193127 and sizes["glyphs"] == 2 and sizes["sprites"] == 6
    manifest = tmp_path / "maps.json"
    shutil.copyfile(REPO / "manifest" / "maps.json", manifest)
    updated = verify.update_manifest_sizes(manifest, {"uk-ie": 3200000000, "unknown": 1})
    assert updated == ["uk-ie"]
    doc = json.loads(manifest.read_text())
    assert next(i for i in doc["items"] if i["id"] == "uk-ie")["size_bytes"] == 3200000000
    assert next(i for i in doc["items"] if i["id"] == "apk")["size_bytes"] == 64193127, "untouched items keep their values"


def test_overlay_sizes_covers_every_id_the_index_names(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    _synthetic_out(ctx.out)
    sizes = verify.overlay_sizes(ctx)
    assert sizes == {"footpaths": 2, "flood-zones": 2, "water": 2, "nuclear-sites": len(json.dumps({"type": "FeatureCollection", "features": []}))}
    overlays_manifest = tmp_path / "overlays.json"
    shutil.copyfile(REPO / "manifest" / "overlays.json", overlays_manifest)
    updated = verify.update_manifest_sizes(overlays_manifest, sizes)
    assert set(updated) == {"footpaths", "flood-zones", "water", "nuclear-sites"}
    doc = json.loads(overlays_manifest.read_text())
    assert next(i for i in doc["items"] if i["id"] == "footpaths")["size_bytes"] == 2


def test_write_fixture_manifest_rewrites_base_and_drops_apk(tmp_path):
    dest = tmp_path / "fixtures" / "manifest" / "maps.json"
    verify.write_fixture_manifest(REPO / "manifest" / "maps.json", dest, "test.pmtiles")
    doc = json.loads(dest.read_text())
    ids = [i["id"] for i in doc["items"]]
    assert ids == [i for i in MANIFEST_IDS if i != "apk"]
    base = doc["items"][0]
    assert base["dest"] == "maps/test.pmtiles" and base["source"]["artifact"] == "test.pmtiles"
    assert next(i for i in doc["items"] if i["id"] == "places")["dest"] == "maps/places.csv.gz"


def _repo_copy(tmp_path):
    repo = tmp_path / "repo"
    (repo / "manifest").mkdir(parents=True)
    shutil.copyfile(REPO / "manifest" / "maps.json", repo / "manifest" / "maps.json")
    shutil.copyfile(REPO / "manifest" / "overlays.json", repo / "manifest" / "overlays.json")
    (repo / "install").mkdir()
    (repo / "install" / "versions.env").write_text("PROTOMAPS_BUILD=20260902\n")
    return repo


def test_verify_step_fixture_verifies_every_archive_and_writes_sizes(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out)
    verify.VerifyStep().run(ctx)
    verified = sorted(c[2] for c in runner.find("pmtiles", "verify"))
    assert verified == sorted(str(p) for p in [ctx.out / "test.pmtiles", ctx.out / "os-zoomstack.pmtiles", ctx.out / "contours.pmtiles", ctx.out / "hillshade.pmtiles",
                                                ctx.out / "overlays" / "footpaths.pmtiles", ctx.out / "overlays" / "flood-zones.pmtiles", ctx.out / "overlays" / "water.pmtiles"])
    assert runner.find("pmtiles", "tile")[0][-3:] == ["12", "2031", "1372"]
    fixture_manifest = ctx.repo / "api" / "tests" / "fixtures" / "manifest" / "maps.json"
    doc = json.loads(fixture_manifest.read_text())
    assert next(i for i in doc["items"] if i["id"] == "uk-ie")["size_bytes"] == 2
    assert "apk" not in [i["id"] for i in doc["items"]]
    original = json.loads((ctx.repo / "manifest" / "maps.json").read_text())
    assert next(i for i in original["items"] if i["id"] == "uk-ie")["size_bytes"] == 3400000000, "fixture runs never touch manifest/maps.json"
    original_overlays = json.loads((ctx.repo / "manifest" / "overlays.json").read_text())
    assert next(i for i in original_overlays["items"] if i["id"] == "footpaths")["size_bytes"] == 900000000, "fixture runs never touch manifest/overlays.json either"
    report = json.loads((ctx.out / "build.json").read_text())
    assert report["fixture"] is True and report["sizes"]["contours"] == 2 and len(report["verified_archives"]) == 7
    assert report["overlay_sizes"]["footpaths"] == 2 and report["updated_overlays"] == []


def test_verify_step_full_mode_updates_the_real_manifest_copy(tmp_path):
    header = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 15, "bounds": [-11, 49.1, 2.2, 61.2]}
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(header), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out, base="uk-ie.pmtiles")
    verify.VerifyStep().run(ctx)
    probed = {tuple(c[-3:]) for c in runner.find("pmtiles", "tile")}
    assert probed == {("12", "2023", "1403"), ("12", "2034", "1186")}
    doc = json.loads((ctx.repo / "manifest" / "maps.json").read_text())
    assert next(i for i in doc["items"] if i["id"] == "uk-ie")["size_bytes"] == 2
    overlays_doc = json.loads((ctx.repo / "manifest" / "overlays.json").read_text())
    assert next(i for i in overlays_doc["items"] if i["id"] == "footpaths")["size_bytes"] == 2
    assert next(i for i in overlays_doc["items"] if i["id"] == "flood-zones")["size_bytes"] == 2


def test_verify_step_fails_on_oversized_fixture_missing_output_or_bad_style(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out)
    (ctx.out / "test.pmtiles").write_bytes(b"x" * FIXTURE_MAX_BYTES)
    with pytest.raises(BuildError, match="under"):
        verify.VerifyStep().run(ctx)
    (ctx.out / "test.pmtiles").write_bytes(b"pm")
    (ctx.out / "places.csv.gz").unlink()
    with pytest.raises(BuildError, match="places.csv.gz"):
        verify.VerifyStep().run(ctx)
    assert not (ctx.out / "build.json").exists()


def test_verify_step_fails_when_an_overlay_the_manifest_lists_is_missing_from_the_output(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out)
    (ctx.out / "overlays" / "water.pmtiles").unlink()
    with pytest.raises(BuildError, match="water"):
        verify.VerifyStep().run(ctx)
