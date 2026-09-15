import json
import subprocess
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


def test_vector_source_keeps_a_ready_made_feature_server_query(tmp_path):
    ctx = make_ctx(tmp_path)
    url = "https://s/FeatureServer/7/query?where=1%3D1&outFields=*&f=json&maxAllowableOffset=5"
    src = overlays.vector_source(ctx, url, "flood_sc_url_1")
    assert src.source == url and src.open_options == ("-oo", "FEATURE_SERVER_PAGING=YES")


def test_ogr_to_assembles_reprojection_with_optional_spat(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    src = overlays.VectorSource("/vsizip//tmp/a.zip", ("-oo", "X=Y"), "layer1")
    overlays.ogr_to(ctx, "FlatGeobuf", tmp_path / "out.fgb", src, spat=FIXTURE_BBOX)
    assert runner.calls[0] == ["ogr2ogr", "-f", "FlatGeobuf", "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI",
                               "-spat", "-1.56", "50.87", "-1.46", "50.97", "-oo", "X=Y", str(tmp_path / "out.fgb"), "/vsizip//tmp/a.zip", "layer1"]
    overlays.ogr_to(ctx, "GeoJSON", tmp_path / "out.geojson", overlays.VectorSource("in.geojson"))
    assert runner.calls[1] == ["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI", str(tmp_path / "out.geojson"), "in.geojson"]


def test_ogr_to_retries_a_remote_source_and_passes_gdal_retry_options(tmp_path):
    attempts = {"n": 0}

    def flaky(cmd, *, cwd=None, capture=False, binary=False):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise overlays.BuildError("command failed (exit 1): ogr2ogr\nERROR 1: Recv failure: Connection reset by peer")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    ctx = make_ctx(tmp_path, runner=flaky)
    src = overlays.VectorSource("https://x/FeatureServer/2/query?where=1%3D1&outFields=*&f=json", ("-oo", "FEATURE_SERVER_PAGING=YES"))
    overlays.ogr_to(ctx, "FlatGeobuf", tmp_path / "out.fgb", src)
    assert attempts["n"] == 3

    always = FakeRunner()
    ctx = make_ctx(tmp_path, runner=always)
    overlays.ogr_to(ctx, "FlatGeobuf", tmp_path / "out.fgb", src)
    assert always.calls[0][7:13] == ["--config", "GDAL_HTTP_MAX_RETRY", "5", "--config", "GDAL_HTTP_RETRY_DELAY", "10"]

    def broken(cmd, *, cwd=None, capture=False, binary=False):
        raise overlays.BuildError("command failed (exit 1): ogr2ogr")

    ctx = make_ctx(tmp_path, runner=broken)
    with pytest.raises(overlays.BuildError):
        overlays.ogr_to(ctx, "GeoJSON", tmp_path / "out.geojson", overlays.VectorSource("/vsizip//tmp/a.zip"))


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
    assert tags[-1] == "nwr/amenity=hospital,pharmacy,doctors,clinic"
    export = runner.find("osmium", "export")[0]
    assert "--add-unique-id=type_id" in export and export[export.index("-c") + 1].endswith("health-export.json")
    ogr = runner.find("ogr2ogr")[0]
    assert ogr[-1] == 'SELECT ST_PointOnSurface(geometry) AS geometry, * FROM "health_raw"' and ogr[ogr.index("-dialect") + 1] == "sqlite"
    water = next(o for o in overlays.OSM_OVERLAYS if o.id == "water")
    out = overlays.build_osm_overlay(ctx, water, ctx.src / "in.pbf", work)
    assert out == work / "water_raw.geojson"
    tags = runner.find("osmium", "tags-filter")[1]
    assert tags[-4:] == ["nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works", "nwr/natural=spring"]
    assert len(runner.find("ogr2ogr")) == 1


def test_osm_overlay_table_matches_the_spec():
    table = {o.id: (o.filters, o.points) for o in overlays.OSM_OVERLAYS}
    assert set(table) == {"health", "fuel", "water", "rail", "chemical-sites", "airports", "military"}
    assert table["health"] == (("nwr/amenity=hospital,pharmacy,doctors,clinic",), True)
    assert table["fuel"] == (("nwr/amenity=fuel",), True)
    assert table["water"] == (("nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works", "nwr/natural=spring"), False)
    assert table["rail"] == (("nwr/railway=station",), True)
    assert table["chemical-sites"] == (("nwr/industrial=chemical,refinery,oil",), True)
    assert table["airports"] == (("nwr/aeroway=aerodrome",), False)
    assert table["military"] == (("nwr/military=*", "nwr/landuse=military"), False)


def _point(name, amenity, lon, lat, **extra):
    props = {"name": name, "amenity": amenity, **extra}
    return {"type": "Feature", "properties": props, "geometry": {"type": "Point", "coordinates": [lon, lat]}}


# 0.0002 degrees of longitude/latitude in southern England is a little over 15m: close enough to be the
# same site tagged twice (a POI node and the building around it), never close enough to be two branches
# of the same chain on opposite sides of a street.
NEAR = 0.0002
FAR = 0.01  # ~1.1km: a different branch of the same chain, never the same site.


def test_merge_duplicate_points_collapses_a_node_and_its_building_tagged_the_same():
    # osmium's `nwr` filter keeps both a hospital's entrance node and its building outline; ST_PointOnSurface
    # turns the second into a point too, a few metres from the first.
    a = _point("Haywood Hospital", "hospital", -2.15, 53.05, phone=None)
    b = _point("Haywood Hospital", "hospital", -2.15 + NEAR, 53.05, phone="+44 1782 000000")
    merged = overlays.merge_duplicate_points([a, b])
    assert len(merged) == 1
    # The richer record survives: the one with a phone number, not whichever came first.
    assert merged[0]["properties"]["phone"] == "+44 1782 000000"


def test_merge_duplicate_points_keeps_different_branches_of_the_same_chain():
    a = _point("Well Pharmacy", "pharmacy", -1.5, 52.0)
    b = _point("Well Pharmacy", "pharmacy", -1.5 + FAR, 52.0)
    assert overlays.merge_duplicate_points([a, b]) == [a, b]


def test_merge_duplicate_points_never_merges_across_different_amenities():
    # A hospital and an on-site pharmacy can share a name; they are not the same facility.
    a = _point("City General", "hospital", 0.0, 51.5)
    b = _point("City General", "pharmacy", 0.0 + NEAR, 51.5)
    assert overlays.merge_duplicate_points([a, b]) == [a, b]


def test_merge_duplicate_points_never_merges_unnamed_points():
    # No name means no safe signal the two points are the same site rather than two different ones.
    a = _point(None, "doctors", 0.0, 51.5)
    b = _point(None, "doctors", 0.0 + NEAR, 51.5)
    assert overlays.merge_duplicate_points([a, b]) == [a, b]


def test_merge_duplicate_points_is_case_and_whitespace_insensitive_on_name():
    a = _point("Well Pharmacy", "pharmacy", -1.5, 52.0)
    b = _point("  well   PHARMACY ", "pharmacy", -1.5 + NEAR, 52.0)
    assert len(overlays.merge_duplicate_points([a, b])) == 1


def test_merge_duplicate_points_merges_a_chain_of_near_neighbours_transitively():
    # A within range of B, B within range of C, but A more than the radius from C directly: still one site.
    a = _point("Riverside Surgery", "doctors", 0.0, 51.5)
    b = _point("Riverside Surgery", "doctors", 0.0 + NEAR, 51.5)
    c = _point("Riverside Surgery", "doctors", 0.0 + 2 * NEAR, 51.5)
    merged = overlays.merge_duplicate_points([a, b, c])
    assert len(merged) == 1


def test_merge_duplicate_points_is_deterministic_on_a_tie():
    # Equally-filled records: the earliest in the input wins, so a rebuild from the same OSM extract
    # always keeps the same one rather than an arbitrary one.
    a = _point("Corner Pharmacy", "pharmacy", 0.0, 51.5)
    b = _point("Corner Pharmacy", "pharmacy", 0.0 + NEAR, 51.5)
    assert overlays.merge_duplicate_points([a, b]) == [a]
    assert overlays.merge_duplicate_points([b, a]) == [b]


def test_build_osm_overlay_deduplicates_the_points_it_writes(tmp_path):
    dupes = json.dumps({"type": "FeatureCollection", "features": [
        _point("Haywood Hospital", "hospital", -2.15, 53.05),
        _point("Haywood Hospital", "hospital", -2.15 + NEAR, 53.05),
        _point("Ashdale Pharmacy", "pharmacy", -1.9, 52.4),
    ]}).encode()
    runner = FakeRunner(files={"_raw.geojson": dupes, "health.geojson": dupes})
    ctx = make_ctx(tmp_path, runner=runner)
    work = tmp_path / "work"
    work.mkdir()
    health = next(o for o in overlays.OSM_OVERLAYS if o.id == "health")
    out = overlays.build_osm_overlay(ctx, health, ctx.src / "in.pbf", work)
    written = json.loads(out.read_text())
    assert len(written["features"]) == 2
    names = sorted(f["properties"]["name"] for f in written["features"])
    assert names == ["Ashdale Pharmacy", "Haywood Hospital"]


def test_osm_overlay_kept_tags_match_the_spec():
    tags = {o.id: o.tags for o in overlays.OSM_OVERLAYS}
    assert tags["health"] == ("name", "amenity", "healthcare", "emergency", "beds", "operator", "phone", "website", "opening_hours", "wheelchair", "dispensing")
    assert tags["fuel"] == ("name", "brand", "operator", "opening_hours", "phone", "fuel:diesel", "fuel:lpg", "fuel:electricity", "shop")
    assert tags["water"] == ("name", "man_made", "natural", "water", "landuse", "operator", "description")
    assert tags["rail"] == ("name", "railway", "station", "operator", "network", "platforms", "wheelchair")
    assert tags["airports"] == ("name", "aeroway", "aerodrome", "aerodrome:type", "icao", "iata", "operator", "surface", "military")
    assert tags["military"] == ("name", "military", "landuse", "operator", "description", "access")
    assert tags["chemical-sites"] == ("name", "industrial", "landuse", "man_made", "operator", "hazmat", "description")


def test_export_config_for_writes_the_overlay_allow_list(tmp_path):
    ctx = make_ctx(tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    fuel = next(o for o in overlays.OSM_OVERLAYS if o.id == "fuel")
    path = overlays.export_config_for(ctx, fuel, work)
    assert path == work / "fuel-export.json"
    cfg = json.loads(path.read_text())
    assert cfg["include_tags"] == list(fuel.tags)
    template = json.loads((ctx.repo / "tools" / "map-styles" / "export" / "pois.json").read_text())
    assert cfg["attributes"] == template["attributes"] and cfg["area_tags"] is True


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


def test_source_specs_split_on_whitespace_and_read_layer_and_tag():
    specs = overlays.parse_source_specs("https://a/x.zip|zones#z3  https://b/FeatureServer/2#z2\nhttps://c/d.json")
    assert specs == [("https://a/x.zip", "zones", "z3"), ("https://b/FeatureServer/2", None, "z2"), ("https://c/d.json", None, None)]


def test_flood_zones_layer_per_tagged_source(tmp_path):
    runner = FakeRunner(files={"flood_wales_z3.fgb": b"x", "flood_wales_z2.fgb": b"y", "flood_england.fgb": b"z", "flood-zones.pmtiles": b"p"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    ctx.versions.update({"FLOOD_EN_URL": "https://e/en.gpkg", "FLOOD_WA_URL": "https://w/FeatureServer/1#z3 https://w/FeatureServer/2#z2"})
    work = tmp_path / "work"; work.mkdir()
    staged = tmp_path / "staged"; staged.mkdir()
    _, layers = overlays.build_flood_zones(ctx, work, staged)
    assert layers == ["flood_england", "flood_wales_z3", "flood_wales_z2"]
    tippe = runner.find("tippecanoe")[0]
    assert f"flood_wales_z3:{work / 'flood_wales_z3.fgb'}" in tippe and f"flood_wales_z2:{work / 'flood_wales_z2.fgb'}" in tippe
    assert overlays.flood_coverage(layers) == ["england", "wales"]


def test_flood_zones_rejects_an_unknown_tag(tmp_path):
    ctx = make_ctx(tmp_path, fixture=False)
    ctx.versions.update({"FLOOD_SC_URL": "https://s/FeatureServer/0#medium"})
    with pytest.raises(overlays.BuildError, match="tag 'medium'"):
        overlays.build_flood_zones(ctx, tmp_path, tmp_path)


def test_access_land_stamps_region_and_designation(tmp_path):
    runner = FakeRunner(files={"access_england.geojson": POINT_FC, "access_wales_0.geojson": POINT_FC, "access_wales_1.geojson": POINT_FC})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    ctx.versions.update({"ACCESS_EN_URL": "https://e/FeatureServer/0",
                         "ACCESS_WA_URL": "https://w/open.json#open_country https://w/common.json#common_land"})
    work = tmp_path / "work"; work.mkdir()
    staged = tmp_path / "staged"; staged.mkdir()
    kind, name, regions = overlays.build_access_land(ctx, work, staged)
    assert regions == ["england", "wales"]
    features = json.loads((staged / name).read_text())["features"]
    assert [f["properties"]["region"] for f in features] == ["england", "wales", "wales"]
    assert [f["properties"].get("designation") for f in features] == [None, "open_country", "common_land"]


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
        "airports": {"kind": "geojson", "file": "overlays/airports.geojson"},
        "military": {"kind": "pmtiles", "file": "overlays/military.pmtiles"},
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
    assert set(index) == {"footpaths", "health", "fuel", "water", "rail", "chemical-sites", "airports", "military", "flood-zones", "access-land", "nuclear-sites"}
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
