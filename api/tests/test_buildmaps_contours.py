import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import contours, dem, osm
from sos.mapbuild.common import FIXTURE_BBOX, SPEC_BBOX, BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx

T50_API = "https://api.os.uk/downloads/v1/products/Terrain50/downloads"
T50_ENTRIES = [
    {"md5": "feba9008db55cdcb5c5e5b7896e3428b", "size": 161706566, "fileName": "terr50_gagg_gb.zip",
     "url": "https://api.os.uk/downloads/v1/products/Terrain50/downloads?area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect",
     "format": "ASCII Grid and GML (Grid)", "area": "GB"},
    {"md5": "fa3fed543cfa2073863b4170194e13b7", "size": 1070803333, "fileName": "terr50_mbtiles_gb.zip",
     "url": "https://api.os.uk/downloads/v1/products/Terrain50/downloads?area=GB&format=Vector+Tiles&subformat=%28MBTiles%29&redirect",
     "format": "Vector Tiles", "subformat": "(MBTiles)", "area": "GB"},
]
T50_META = {"vector_layers": [{"id": "contour_line", "fields": {"height": "Number", "id": "String"}, "minzoom": 9, "maxzoom": 14},
                              {"id": "spot_height", "fields": {"height": "Number"}}, {"id": "land_water_boundary", "fields": {}}]}
HEADER = {"tile_type": "mvt", "minzoom": 9, "maxzoom": 14, "bounds": [-9, 49.7, 2, 61]}
TILE_LIST = b"Copernicus_DSM_COG_10_N50_00_W002_00_DEM\nCopernicus_DSM_COG_10_N50_00_W001_00_DEM\nCopernicus_DSM_COG_10_N53_00_W006_00_DEM\n"


def _zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_copernicus_names_cover_the_spec_rows_and_columns():
    names = dem.copernicus_names(SPEC_BBOX)
    assert len(names) == 8 * 14
    assert names[0] == "Copernicus_DSM_COG_10_N49_00_W011_00_DEM"
    assert names[-1] == "Copernicus_DSM_COG_10_N56_00_E002_00_DEM"
    assert dem.copernicus_names(FIXTURE_BBOX) == ["Copernicus_DSM_COG_10_N50_00_W002_00_DEM"]


def test_fetch_copernicus_downloads_only_squares_present_in_the_bucket(tmp_path):
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    paths = dem.fetch_copernicus(ctx, ctx.bbox)
    assert paths == [ctx.src / "copernicus" / "Copernicus_DSM_COG_10_N50_00_W002_00_DEM.tif"]
    urls = [c[-1] for c in runner.find("aria2c")]
    assert urls == ["https://example.test/dem/tileList.txt",
                    "https://example.test/dem/Copernicus_DSM_COG_10_N50_00_W002_00_DEM/Copernicus_DSM_COG_10_N50_00_W002_00_DEM.tif"]
    ctx2 = make_ctx(tmp_path / "b", fixture=False, runner=FakeRunner(files={"copernicus-tileList.txt": b"nothing\n"}))
    with pytest.raises(BuildError, match="no Copernicus"):
        dem.fetch_copernicus(ctx2, ctx2.bbox)


@respx.mock
def test_terr50_asc_dir_unpacks_nested_zips_once(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    inner_hp = _zip({"HP40.asc": b"ncols 200\n", "HP40.gml": b"<gml/>"})
    inner_su = _zip({"SU41.asc": b"ncols 200\n"})
    outer = _zip({"data/hp/hp40_OST50GRID_20230601.zip": inner_hp, "data/su/su41_OST50GRID_20230601.zip": inner_su, "doc/licence.txt": b"OGL"})
    runner = FakeRunner(files={"terr50_gagg_gb.zip": outer})
    ctx = make_ctx(tmp_path, runner=runner)
    root = dem.terr50_asc_dir(ctx)
    assert sorted(p.name for p in root.glob("*.asc")) == ["HP40.asc", "SU41.asc"]
    (root / "HP40.asc").write_bytes(b"kept")
    assert dem.terr50_asc_dir(ctx) == root and (root / "HP40.asc").read_bytes() == b"kept"


def test_osni_dtm_blank_url_returns_none_with_warning(tmp_path, caplog):
    ctx = make_ctx(tmp_path, versions={"OSNI_DTM_URL": ""})
    assert dem.osni_dtm(ctx) is None
    assert "OSNI_DTM_URL is blank" in caplog.text
    ctx2 = make_ctx(tmp_path / "b", versions={"OSNI_DTM_URL": "https://example.test/osni_dtm50.tif"})
    assert dem.osni_dtm(ctx2) == ctx2.src / "osni-dtm50.tif"


@respx.mock
def test_dem_vrts_are_built_in_later_wins_order(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    outer = _zip({"data/su/su41.zip": _zip({"SU41.asc": b"ncols 1\n"}), "data/su/su42.zip": _zip({"SU42.asc": b"ncols 1\n"})})
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST, "terr50_gagg_gb.zip": outer})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner, versions={"OSNI_DTM_URL": "https://example.test/osni.tif"})
    work = tmp_path / "work"
    vrts = dem.dem_vrts(ctx, work)
    assert [v.name for v in vrts] == ["glo30.vrt", "t50.vrt"], "OSNI is skipped when the bbox misses Northern Ireland"
    calls = runner.find("gdalbuildvrt")
    assert calls[0][:6] == ["gdalbuildvrt", "-overwrite", "-vrtnodata", "-9999", "-input_file_list", str(work / "glo30.txt")]
    assert calls[1][:10] == ["gdalbuildvrt", "-overwrite", "-vrtnodata", "-9999", "-a_srs", "EPSG:27700", "-oo", "DATATYPE=Float32",
                             "-input_file_list", str(work / "t50.txt")], "grids with only whole-metre values open as Int32 and would be skipped"
    for call in calls:
        assert call[2:4] == ["-vrtnodata", "-9999"], "gaps between grids must read as nodata, not 0 m sea, or they overwrite earlier sources"
    assert (work / "t50.txt").read_text().splitlines() == [str(ctx.src / "terr50_asc" / "SU41.asc"), str(ctx.src / "terr50_asc" / "SU42.asc")]


@respx.mock
def test_dem_vrts_include_osni_for_full_bbox(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner, versions={"OSNI_DTM_URL": "https://example.test/osni.tif"})
    (ctx.src / "terr50_asc").mkdir()
    (ctx.src / "terr50_asc" / ".done").touch()
    (ctx.src / "terr50_asc" / "SU41.asc").write_bytes(b"x")
    vrts = dem.dem_vrts(ctx, tmp_path / "work")
    assert [v.name for v in vrts] == ["glo30.vrt", "osni.vrt", "t50.vrt"]
    osni = runner.find("gdalbuildvrt")[1]
    assert osni[2:6] == ["-vrtnodata", "-9999", "-a_srs", "EPSG:29902"] and osni[-1] == str(ctx.src / "osni-dtm50.tif")


def test_nongb_dtm_vrt_warps_osni_to_4326_and_puts_it_last(tmp_path):
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner, versions={"OSNI_DTM_URL": "https://example.test/osni.tif"})
    work = tmp_path / "work"
    vrt = dem.nongb_dtm_vrt(ctx, work)
    assert vrt == work / "nongb-4326.vrt"
    warp = runner.find("gdalwarp")[0]
    assert "-s_srs" in warp and warp[warp.index("-s_srs") + 1] == "EPSG:29902" and warp[warp.index("-t_srs") + 1] == "EPSG:4326"
    build = runner.find("gdalbuildvrt")[0]
    assert build[-1] == str(work / "osni-4326.tif") and build[-2].endswith("Copernicus_DSM_COG_10_N53_00_W006_00_DEM.tif")
    assert "-resolution" in build and build[build.index("-resolution") + 1] == "highest"


def test_contour_height_field_prefers_known_names_then_numeric():
    assert contours.contour_height_field(T50_META) == "height"
    assert contours.contour_height_field({"vector_layers": [{"id": "contour_line", "fields": {"PROP_VALUE": "Number"}}]}) == "PROP_VALUE"
    assert contours.contour_height_field({"vector_layers": [{"id": "contour_line", "fields": {"name": "String", "elev_m": "Number"}}]}) == "elev_m"
    with pytest.raises(BuildError, match="no numeric"):
        contours.contour_height_field({"vector_layers": [{"id": "contour_line", "fields": {"name": "String"}}]})
    with pytest.raises(BuildError, match="contour_line"):
        contours.contour_height_field({"vector_layers": []})


def test_select_region_features_matches_iso_codes_and_northern_ireland():
    features = [
        {"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "2", "ISO3166-1": "IE", "name": "Ireland"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "4", "name": "Northern Ireland"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"type": "Feature", "properties": {"boundary": "historic", "ISO3166-1": "IM", "name": "Isle of Man"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "4", "name": "Wales"}, "geometry": {"type": "Polygon", "coordinates": []}},
    ]
    found = osm.select_region_features(features)
    assert set(found) == {"roi", "ni"}
    assert found["roi"]["properties"]["name"] == "Ireland"


def test_region_polygons_runs_osmium_and_writes_one_file_per_region(tmp_path):
    seq = "\x1e" + json.dumps({"type": "Feature", "properties": {"boundary": "administrative", "ISO3166-1": "JE", "name": "Jersey"},
                               "geometry": {"type": "Polygon", "coordinates": [[[-2.2, 49.1], [-2.0, 49.1], [-2.0, 49.3], [-2.2, 49.1]]]}}) + "\n"
    runner = FakeRunner(files={"admin.geojsonseq": seq.encode()})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    paths = osm.region_polygons(ctx, ctx.src / "bi.osm.pbf")
    assert set(paths) == {"roi", "iom", "jersey", "guernsey", "ni"}
    assert json.loads(paths["jersey"].read_text())["features"][0]["properties"]["name"] == "Jersey"
    assert json.loads(paths["roi"].read_text())["features"] == []
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "r/admin_level=2,4" and tags[-2] == str(ctx.src / "bi.osm.pbf")
    export = runner.find("osmium", "export")[0]
    assert "--geometry-types=polygon" in export and export[export.index("-c") + 1].endswith("tools/map-styles/export/regions.json")


def test_nongb_cutline_fixture_is_the_bbox_polygon(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    path = osm.nongb_cutline(ctx, None)
    ring = json.loads(path.read_text())["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == [-1.56, 50.87] and ring[2] == [-1.46, 50.97]


def test_osm_input_fixture_extracts_bbox_from_hampshire(tmp_path):
    runner = FakeRunner(files={"fixture.osm.pbf": b"pbf"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    assert osm.osm_input(ctx) == ctx.src / "fixture.osm.pbf"
    assert runner.find("aria2c")[0][-1] == "https://example.test/hampshire-latest.osm.pbf"
    extract = runner.find("osmium", "extract")[0]
    assert extract[extract.index("-b") + 1] == "-1.56,50.87,-1.46,50.97" and extract[-1] == str(ctx.src / "hampshire-latest.osm.pbf")
    full = make_ctx(tmp_path / "f", fixture=False, runner=FakeRunner())
    assert osm.osm_input(full) == full.src / "britain-and-ireland-latest.osm.pbf"


@respx.mock
def test_contours_step_assembles_the_pipeline_in_fixture_mode(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    runner = FakeRunner(
        outputs={"pmtiles show": lambda cmd: json.dumps(HEADER if "--header-json" in cmd else T50_META)},
        files={"terr50_mbtiles_gb.zip": _zip({"data/terr50_gb.mbtiles": b"sqlite"}), "copernicus-tileList.txt": TILE_LIST,
               "contours-gb-full.pmtiles": b"gb", "contours-gb.pmtiles": b"gbx", "contours-nongb.pmtiles": b"ng", "contours.pmtiles": b"merged"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    contours.ContoursStep().run(ctx)
    tools = [c[0] for c in runner.calls if c[0] not in ("aria2c", "pmtiles")]
    assert tools == ["gdalbuildvrt", "gdalwarp", "gdal_contour", "tippecanoe", "tile-join"]
    work = ctx.src / "contours-work"
    assert runner.find("pmtiles", "convert")[0][2] == str(ctx.src / "terr50_mbtiles" / "data" / "terr50_gb.mbtiles")
    assert runner.find("pmtiles", "extract")[0][-1] == "--bbox=-1.56,50.87,-1.46,50.97"
    warp = runner.find("gdalwarp")[0]
    assert warp[warp.index("-cutline") + 1] == str(ctx.src / "regions" / "nongb-cutline.geojson") and "-crop_to_cutline" in warp
    contour = runner.find("gdal_contour")[0]
    assert contour[1:9] == ["-i", "10", "-a", "height", "-snodata", "-9999", "-f", "FlatGeobuf"]
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:9] == ["-o", str(work / "contours-nongb.pmtiles"), "-l", "contour_line", "-Z11", "-z14", "-P", "--drop-densest-as-needed"]
    join = runner.find("tile-join")[0]
    assert join == ["tile-join", "-o", str(ctx.incoming / "contours.pmtiles"), "-pk", "--force",
                    str(work / "contours-gb.pmtiles"), str(work / "contours-nongb.pmtiles")]
    assert (ctx.out / "contours.pmtiles").read_bytes() == b"merged"
    side = json.loads((ctx.out / "contours.json").read_text())
    assert side["height_field"] == "height" and side["layers"] == ["contour_line", "land_water_boundary", "spot_height"]
