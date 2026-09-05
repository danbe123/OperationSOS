import json
from pathlib import Path

import pytest

from sos.mapbuild import overlays
from sos.mapbuild.common import BuildError, FIXTURE_BBOX, validate_geojson
from tests.mapbuild_helpers import FakeRunner, make_ctx, REPO

DATA = REPO / "tools" / "map-styles" / "data"
SAMPLES = REPO / "api" / "tests" / "fixtures" / "maps" / "src"
POINT_FC = json.dumps({"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"name": "Sample", "amenity": "hospital"}, "geometry": {"type": "Point", "coordinates": [-1.5, 50.9]}}]}).encode()


def _inside(bbox, lon, lat):
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def test_nuclear_sites_file_is_valid_with_at_least_20_uk_points():
    obj = json.loads((DATA / "nuclear-sites.geojson").read_text())
    assert validate_geojson(obj) == []
    assert len(obj["features"]) >= 20
    names = [f["properties"]["name"] for f in obj["features"]]
    # Substring check (not exact-name membership): plan 03's nuclear-sites.geojson already shipped with
    # richer names than these bare place-names, e.g. "Barrow-in-Furness shipyard", "Rosyth dockyard".
    for required in ("Sellafield", "AWE Aldermaston", "AWE Burghfield", "HMNB Clyde (Faslane)", "RNAD Coulport", "HMNB Devonport",
                     "Barrow-in-Furness", "Rosyth", "Dounreay", "Harwell", "Winfrith", "Springfields", "Capenhurst"):
        assert any(required in n for n in names), required
    for f in obj["features"]:
        assert f["geometry"]["type"] == "Point"
        lon, lat = f["geometry"]["coordinates"]
        assert -11 <= lon <= 2.2 and 49.1 <= lat <= 61.2, f["properties"]["name"]


def test_chemical_sites_and_fixture_samples_are_valid_geojson():
    chem = json.loads((DATA / "chemical-sites.geojson").read_text())
    assert validate_geojson(chem) == [] and len(chem["features"]) >= 8
    for name in ("flood-england-sample.geojson", "access-england-sample.geojson"):
        obj = json.loads((SAMPLES / name).read_text())
        assert validate_geojson(obj) == []
        for f in obj["features"]:
            for lon, lat in f["geometry"]["coordinates"][0]:
                assert _inside(FIXTURE_BBOX, lon, lat), f"{name} vertex {lon},{lat} outside the fixture bbox"


def test_vector_source_forms(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    z = overlays.vector_source(ctx, "https://example.test/fz.zip|Flood_Zone_3", "flood_en_url")
    assert z.source == f"/vsizip/{ctx.src / 'flood_en_url.zip'}" and z.layer == "Flood_Zone_3" and z.open_options == ()
    fs = overlays.vector_source(ctx, "https://services.arcgis.com/x/arcgis/rest/services/CRoW/FeatureServer/0", "access_en_url")
    assert fs.source == "https://services.arcgis.com/x/arcgis/rest/services/CRoW/FeatureServer/0/query?where=1%3D1&outFields=*&f=json"
    assert fs.open_options == ("-oo", "FEATURE_SERVER_PAGING=YES") and fs.layer is None
    plain = overlays.vector_source(ctx, "https://example.test/zones.geojson", "x")
    assert plain.source == "https://example.test/zones.geojson"
    assert len(runner.find("aria2c")) == 1


def test_ogr_to_assembles_reprojection_with_optional_spat(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    src = overlays.VectorSource("/vsizip//tmp/a.zip", ("-oo", "X=Y"), "layer1")
    overlays.ogr_to(ctx, "FlatGeobuf", tmp_path / "out.fgb", src, spat=FIXTURE_BBOX)
    assert runner.calls[0] == ["ogr2ogr", "-f", "FlatGeobuf", "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI",
                               "-spat", "-1.56", "50.87", "-1.46", "50.97", "-oo", "X=Y", str(tmp_path / "out.fgb"), "/vsizip//tmp/a.zip", "layer1"]
    overlays.ogr_to(ctx, "GeoJSON", tmp_path / "out.geojson", overlays.VectorSource("in.geojson"))
    assert runner.calls[1] == ["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI", str(tmp_path / "out.geojson"), "in.geojson"]


def test_finalise_applies_the_5mb_rule(tmp_path):
    runner = FakeRunner(files={"water.pmtiles": b"tiles"})
    ctx = make_ctx(tmp_path, runner=runner)
    staged = tmp_path / "staged"
    staged.mkdir()
    small = tmp_path / "health.geojson"
    small.write_bytes(POINT_FC)
    assert overlays.finalise(ctx, "health", small, staged) == ("geojson", "health.geojson")
    assert (staged / "health.geojson").read_bytes() == POINT_FC
    big = tmp_path / "water.geojson"
    big.write_bytes(b"{" + b" " * overlays.SIZE_RULE_BYTES + b"}")
    assert overlays.finalise(ctx, "water", big, staged) == ("pmtiles", "water.pmtiles")
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:5] == ["-o", str(staged / "water.pmtiles"), "-l", "water"]
    assert "-zg" in tippe and "--coalesce-densest-as-needed" in tippe and "--detect-shared-borders" in tippe and tippe[-1] == str(big)


def test_build_footpaths_uses_designation_first_zoom_rule(tmp_path):
    runner = FakeRunner(files={"footpaths.pmtiles": b"fp"})
    ctx = make_ctx(tmp_path, runner=runner)
    work, staged = tmp_path / "work", tmp_path / "staged"
    work.mkdir(); staged.mkdir()
    out = overlays.build_footpaths(ctx, ctx.src / "fixture.osm.pbf", work, staged)
    assert out == staged / "footpaths.pmtiles" and out.exists()
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "w/highway=path,footway,bridleway,track,cycleway,steps" and tags[-2] == str(ctx.src / "fixture.osm.pbf")
    export = runner.find("osmium", "export")[0]
    assert "--geometry-types=linestring" in export and export[export.index("-c") + 1].endswith("export/paths.json") and "-f" in export and export[export.index("-f") + 1] == "geojsonseq"
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:8] == ["-o", str(staged / "footpaths.pmtiles"), "-l", "footpaths", "-Z10", "-z15", "-P"]
    assert "--drop-densest-as-needed" in tippe and "--extend-zooms-if-still-dropping" in tippe
    assert tippe[tippe.index("-j") + 1] == '{"footpaths":["any",[">=","$zoom",13],["has","designation"]]}'
    assert tippe[-1] == str(work / "paths.geojsonseq")


def test_build_osm_overlay_points_use_point_on_surface_and_polygons_do_not(tmp_path):
    runner = FakeRunner(files={"_raw.geojson": POINT_FC, "health.geojson": POINT_FC})
    ctx = make_ctx(tmp_path, runner=runner)
    work = tmp_path / "work"
    work.mkdir()
    health = next(o for o in overlays.OSM_OVERLAYS if o.id == "health")
    out = overlays.build_osm_overlay(ctx, health, ctx.src / "in.pbf", work)
    assert out == work / "health.geojson"
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "nwr/amenity=hospital,pharmacy,doctors"
    export = runner.find("osmium", "export")[0]
    assert "--add-unique-id=type_id" in export and export[export.index("-c") + 1].endswith("export/pois.json")
    ogr = runner.find("ogr2ogr")[0]
    assert ogr[-1] == 'SELECT ST_PointOnSurface(geometry) AS geometry, * FROM "health_raw"' and ogr[ogr.index("-dialect") + 1] == "sqlite"
    water = next(o for o in overlays.OSM_OVERLAYS if o.id == "water")
    out = overlays.build_osm_overlay(ctx, water, ctx.src / "in.pbf", work)
    assert out == work / "water_raw.geojson"
    tags = runner.find("osmium", "tags-filter")[1]
    assert tags[-3:] == ["nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works"]
    assert len(runner.find("ogr2ogr")) == 1


def test_osm_overlay_table_matches_the_spec():
    table = {o.id: (o.filters, o.points) for o in overlays.OSM_OVERLAYS}
    assert set(table) == {"health", "fuel", "water", "rail", "chemical-sites", "airports-military"}
    assert table["fuel"] == (("nwr/amenity=fuel",), True)
    assert table["rail"] == (("nwr/railway=station",), True)
    assert table["chemical-sites"] == (("nwr/industrial=chemical,refinery,oil",), True)
    assert table["airports-military"] == (("nwr/aeroway=aerodrome", "nwr/military=*"), False)


def test_flood_zones_fixture_uses_the_committed_sample_with_spat_and_named_layer(tmp_path):
    runner = FakeRunner(files={"flood-zones.pmtiles": b"fz"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    work, staged = tmp_path / "work", tmp_path / "staged"
    work.mkdir(); staged.mkdir()
    out, layers = overlays.build_flood_zones(ctx, work, staged)
    assert out == staged / "flood-zones.pmtiles" and layers == ["flood_england"]
    ogr = runner.find("ogr2ogr")[0]
    assert ogr[-1] == str(SAMPLES / "flood-england-sample.geojson") and "-spat" in ogr
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:9] == ["-o", str(staged / "flood-zones.pmtiles"), "-Z8", "-z14", "-P", "--detect-shared-borders", "--coalesce-densest-as-needed", "--simplification=6"]
    assert tippe[-2:] == ["-L", f"flood_england:{work / 'flood_england.fgb'}"]


def test_flood_zones_full_mode_skips_blank_regions_and_needs_at_least_one(tmp_path, caplog):
    runner = FakeRunner(files={"flood-zones.pmtiles": b"fz"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner,
                   versions={"FLOOD_EN_URL": "https://example.test/ea.zip|Flood_Zones_3", "FLOOD_SC_URL": "https://example.test/sepa/FeatureServer/2"})
    work, staged = tmp_path / "work", tmp_path / "staged"
    work.mkdir(); staged.mkdir()
    _, layers = overlays.build_flood_zones(ctx, work, staged)
    assert layers == ["flood_england", "flood_scotland"]
    assert "FLOOD_WA_URL is blank" in caplog.text and "FLOOD_NI_URL is blank" in caplog.text
    tippe = runner.find("tippecanoe")[0]
    assert [a for a in tippe if a.startswith("flood_")] == [f"flood_england:{work / 'flood_england.fgb'}", f"flood_scotland:{work / 'flood_scotland.fgb'}"]
    empty = make_ctx(tmp_path / "e", fixture=False, runner=FakeRunner())
    with pytest.raises(BuildError, match="FLOOD_"):
        overlays.build_flood_zones(empty, tmp_path / "e" / "w", tmp_path / "e" / "s")


def test_nuclear_sites_rejects_short_or_non_point_lists(tmp_path, monkeypatch):
    ctx = make_ctx(tmp_path)
    bad_repo = tmp_path / "repo"
    (bad_repo / "tools" / "map-styles" / "data").mkdir(parents=True)
    (bad_repo / "tools" / "map-styles" / "data" / "nuclear-sites.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"name": "x"}, "geometry": {"type": "Point", "coordinates": [-1, 51]}}]}))
    ctx.repo = bad_repo
    with pytest.raises(BuildError, match="20"):
        overlays.nuclear_sites(ctx)
    ctx.repo = REPO
    assert len(overlays.nuclear_sites(ctx)["features"]) >= 20


def test_verify_manifest_kinds_raises_on_drift(tmp_path):
    ctx = make_ctx(tmp_path, fixture=False)
    repo = tmp_path / "repo"
    (repo / "manifest").mkdir(parents=True)
    (repo / "manifest" / "overlays.json").write_text(json.dumps({"items": [
        {"id": "water", "kind": "geojson", "dest": "maps/overlays/water.geojson"},
        {"id": "health", "kind": "geojson", "dest": "maps/overlays/health.geojson"}]}))
    ctx.repo = repo
    # The build actually produced water as pmtiles (its real size class); the manifest still says geojson.
    index = {"water": {"kind": "pmtiles", "file": "overlays/water.pmtiles"},
             "health": {"kind": "geojson", "file": "overlays/health.geojson"}}
    with pytest.raises(BuildError, match="water"):
        overlays.verify_manifest_kinds(ctx, index)


def test_verify_manifest_kinds_passes_when_dest_and_kind_agree(tmp_path):
    ctx = make_ctx(tmp_path, fixture=False)
    repo = tmp_path / "repo"
    (repo / "manifest").mkdir(parents=True)
    (repo / "manifest" / "overlays.json").write_text(json.dumps({"items": [
        {"id": "water", "kind": "pmtiles", "dest": "maps/overlays/water.pmtiles"}]}))
    ctx.repo = repo
    # An overlay id absent from the manifest (e.g. newly added, not yet merged) must be ignored, not flagged.
    index = {"water": {"kind": "pmtiles", "file": "overlays/water.pmtiles"},
             "brand-new-overlay": {"kind": "geojson", "file": "overlays/brand-new-overlay.geojson"}}
    overlays.verify_manifest_kinds(ctx, index)  # must not raise


def test_verify_manifest_kinds_passes_against_the_real_merged_manifest(tmp_path):
    # ctx.repo defaults to REPO, so this checks the actual committed manifest/overlays.json (cross-plan,
    # already merged) still agrees with what this step really produces for its size-gated entries.
    ctx = make_ctx(tmp_path, fixture=False)
    index = {
        "water": {"kind": "pmtiles", "file": "overlays/water.pmtiles"},
        "airports-military": {"kind": "pmtiles", "file": "overlays/airports-military.pmtiles"},
        "health": {"kind": "pmtiles", "file": "overlays/health.pmtiles"},
        "access-land": {"kind": "pmtiles", "file": "overlays/access-land.pmtiles"},
    }
    overlays.verify_manifest_kinds(ctx, index)  # must not raise


def test_overlays_step_end_to_end_fixture(tmp_path):
    runner = FakeRunner(files={"fixture.osm.pbf": b"pbf", "_raw.geojson": POINT_FC, "health.geojson": POINT_FC, "fuel.geojson": POINT_FC,
                               "rail.geojson": POINT_FC, "chemical-sites.geojson": POINT_FC, "access_england.geojson": POINT_FC,
                               "footpaths.pmtiles": b"fp", "flood-zones.pmtiles": b"fz"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    overlays.OverlaysStep().run(ctx)
    out = ctx.out / "overlays"
    index = json.loads((out / "index.json").read_text())
    assert set(index) == {"footpaths", "health", "fuel", "water", "rail", "chemical-sites", "airports-military", "flood-zones", "access-land", "nuclear-sites"}
    assert index["footpaths"] == {"kind": "pmtiles", "file": "overlays/footpaths.pmtiles", "layers": ["footpaths"], "size_bytes": 2}
    assert index["flood-zones"]["layers"] == ["flood_england"] and index["flood-zones"]["coverage"] == ["england"]
    assert index["health"]["kind"] == "geojson" and index["health"]["features"] == 1
    assert index["chemical-sites"]["features"] == 1 + 10, "OSM points plus the hand-authored list"
    assert index["access-land"] == {"kind": "geojson", "file": "overlays/access-land.geojson", "coverage": ["england"], "size_bytes": (out / "access-land.geojson").stat().st_size}
    assert index["nuclear-sites"]["features"] >= 20
    for info in index.values():
        assert (ctx.out / info["file"]).exists(), info
    assert json.loads((out / "access-land.geojson").read_text())["features"][0]["properties"]["region"] == "england"
    assert not (ctx.incoming / "overlays").exists()
    assert json.loads((ctx.out / "overlays.json").read_text())["osm_input"] == "fixture.osm.pbf"
