import json

import httpx
import pytest
import respx

from sos.mapbuild import hillshade
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx
from tests.test_buildmaps_contours import T50_API, T50_ENTRIES, TILE_LIST, _zip

PNG_HEADER = {"tile_type": "png", "minzoom": 5, "maxzoom": 12, "bounds": [-1.56, 50.87, -1.46, 50.97]}


def _fixture_ctx(tmp_path, header=PNG_HEADER):
    outer = _zip({"data/su/su41.zip": _zip({"SU41.asc": b"ncols 1\n"})})
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(header)},
                        files={"copernicus-tileList.txt": TILE_LIST, "terr50_gagg_gb.zip": outer, "hillshade.pmtiles": b"png-archive"})
    return make_ctx(tmp_path, fixture=True, runner=runner), runner


@respx.mock
def test_hillshade_step_runs_the_spec_pipeline_in_order(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    ctx, runner = _fixture_ctx(tmp_path)
    hillshade.HillshadeStep().run(ctx)
    work = ctx.src / "hillshade-work"
    tools = [c[0] if c[0] != "pmtiles" else " ".join(c[:2]) for c in runner.calls if c[0] != "aria2c"]
    assert tools == ["gdalbuildvrt", "gdalbuildvrt", "gdalwarp", "gdaldem", "gdal_translate", "gdaladdo",
                     "pmtiles convert", "pmtiles show"]
    warp = runner.find("gdalwarp")[0]
    assert warp[1:12] == ["-overwrite", "-t_srs", "EPSG:3857", "-tr", "30", "30", "-r", "bilinear", "-dstnodata", "-9999", "-te"]
    assert warp[12:18] == ["-1.56", "50.87", "-1.46", "50.97", "-te_srs", "EPSG:4326"]
    assert warp[-3:] == [str(work / "glo30.vrt"), str(work / "t50.vrt"), str(work / "dtm3857.tif")], "later inputs win: OS last"
    shade = runner.find("gdaldem")[0]
    assert shade[1:12] == ["hillshade", "-compute_edges", "-z", "1", "-s", "1", "-az", "315", "-alt", "45", "-co"]
    assert shade[-2:] == [str(work / "dtm3857.tif"), str(work / "hillshade.tif")]
    translate = runner.find("gdal_translate")[0]
    assert translate == ["gdal_translate", "-of", "MBTILES", "-co", "TILE_FORMAT=PNG8", "-co", "ZOOM_LEVEL_STRATEGY=LOWER",
                         str(work / "hillshade.tif"), str(work / "hillshade.mbtiles")]
    assert runner.find("gdaladdo")[0] == ["gdaladdo", "-r", "average", str(work / "hillshade.mbtiles"), "2", "4", "8", "16", "32", "64", "128"]
    assert runner.find("pmtiles", "convert")[0] == ["pmtiles", "convert", str(work / "hillshade.mbtiles"), str(ctx.incoming / "hillshade.pmtiles")]
    assert (ctx.out / "hillshade.pmtiles").read_bytes() == b"png-archive"
    side = json.loads((ctx.out / "hillshade.json").read_text())
    assert side["sources"] == ["glo30.vrt", "t50.vrt"] and side["header"]["tile_type"] == "png"


@respx.mock
def test_hillshade_step_rejects_non_png_archive(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    ctx, _ = _fixture_ctx(tmp_path, header=dict(PNG_HEADER, tile_type="mvt"))
    with pytest.raises(BuildError, match="png"):
        hillshade.HillshadeStep().run(ctx)
    assert not (ctx.out / "hillshade.pmtiles").exists()
