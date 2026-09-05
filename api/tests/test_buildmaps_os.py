import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import osdata
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx

API = "https://api.os.uk/downloads/v1/products/OpenZoomstack/downloads"
ENTRIES = [
    {"md5": "19c18967b2d83e7eff4bfc0a61f4fc28", "size": 4301453983,
     "url": "https://api.os.uk/downloads/v1/products/OpenZoomstack/downloads?area=GB&format=GeoPackage&redirect",
     "format": "GeoPackage", "area": "GB", "fileName": "OS_Open_Zoomstack.zip"},
    {"md5": "04c5ebcfa98447fab9925803dcbf7497", "size": 2852712448,
     "url": "https://api.os.uk/downloads/v1/products/OpenZoomstack/downloads?area=GB&format=Vector+Tiles&subformat=%28MBTiles%29&redirect",
     "format": "Vector Tiles", "subformat": "(MBTiles)", "area": "GB", "fileName": "OS_Open_Zoomstack.mbtiles"},
]
OS_LAYERS = ["airports", "boundaries", "buildings", "contours", "etl", "foreshore", "greenspaces", "names",
             "national_parks", "rail", "railwaystations", "roads", "sea", "sites", "surfacewater", "urban_areas",
             "waterlines", "woodland"]
HEADER = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 14, "bounds": [-9.0, 49.75, 2.0, 61.0]}


def _show(cmd):
    return json.dumps(HEADER if "--header-json" in cmd else {"vector_layers": [{"id": l, "fields": {}} for l in OS_LAYERS]})


@respx.mock
def test_os_fetch_picks_the_named_file_and_downloads_with_md5(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    path = osdata.os_fetch(ctx, "OpenZoomstack", "OS_Open_Zoomstack.mbtiles")
    assert path == ctx.src / "OS_Open_Zoomstack.mbtiles" and path.exists()
    cmd = runner.calls[0]
    assert cmd[0] == "aria2c" and cmd[-1] == ENTRIES[1]["url"]
    assert "--checksum=md5=04c5ebcfa98447fab9925803dcbf7497" in cmd


def test_pick_download_error_lists_available_names():
    with pytest.raises(BuildError, match="terr50_mbtiles_gb.zip.*OS_Open_Zoomstack.mbtiles"):
        osdata.pick_download(ENTRIES, "terr50_mbtiles_gb.zip")


@respx.mock
def test_os_downloads_non_200_is_a_build_error(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(503))
    with pytest.raises(BuildError, match="503"):
        osdata.os_downloads(make_ctx(tmp_path), "OpenZoomstack")


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_unzip_single_extracts_once_and_finds_one_match(tmp_path):
    z = tmp_path / "terr50_mbtiles_gb.zip"
    z.write_bytes(_zip_bytes({"data/terr50_gb.mbtiles": b"sqlite", "doc/readme.txt": b"hi"}))
    dest = tmp_path / "terr50_mbtiles"
    found = osdata.unzip_single(z, "*.mbtiles", dest)
    assert found == dest / "data" / "terr50_gb.mbtiles" and found.read_bytes() == b"sqlite"
    (dest / "data" / "terr50_gb.mbtiles").write_bytes(b"touched")
    assert osdata.unzip_single(z, "*.mbtiles", dest).read_bytes() == b"touched", "must not re-extract"
    with pytest.raises(BuildError, match="found 0"):
        osdata.unzip_single(z, "*.gpkg", dest)


@respx.mock
def test_os_step_full_mode_converts_straight_into_staging(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner(outputs={"pmtiles show": _show}, files={"os-zoomstack.pmtiles": b"pm"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    osdata.OsZoomstackStep().run(ctx)
    convert = runner.find("pmtiles", "convert")
    assert convert == [["pmtiles", "convert", str(ctx.src / "OS_Open_Zoomstack.mbtiles"), str(ctx.incoming / "os-zoomstack.pmtiles")]]
    assert not runner.find("pmtiles", "extract")
    assert (ctx.out / "os-zoomstack.pmtiles").read_bytes() == b"pm"
    side = json.loads((ctx.out / "os-zoomstack.json").read_text())
    assert side["layers"] == OS_LAYERS and side["header"]["maxzoom"] == 14


@respx.mock
def test_os_step_fixture_mode_converts_once_then_extracts_bbox(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner(outputs={"pmtiles show": _show},
                        files={"os-zoomstack-full.pmtiles": b"full", "os-zoomstack.pmtiles": b"pm"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner, force=True)
    osdata.OsZoomstackStep().run(ctx)
    osdata.OsZoomstackStep().run(ctx)
    assert len(runner.find("pmtiles", "convert")) == 1, "the full conversion is cached in the source dir"
    extract = runner.find("pmtiles", "extract")[0]
    assert extract == ["pmtiles", "extract", str(ctx.src / "os-zoomstack-full.pmtiles"),
                       str(ctx.incoming / "os-zoomstack.pmtiles"), "--bbox=-1.56,50.87,-1.46,50.97"]


@respx.mock
def test_os_step_fails_when_roads_layer_is_missing(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner(outputs={"pmtiles show": lambda cmd: json.dumps(HEADER if "--header-json" in cmd else {"vector_layers": [{"id": "sea", "fields": {}}]})},
                        files={"os-zoomstack.pmtiles": b"pm"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    with pytest.raises(BuildError, match="roads"):
        osdata.OsZoomstackStep().run(ctx)
    assert not (ctx.out / "os-zoomstack.pmtiles").exists()
