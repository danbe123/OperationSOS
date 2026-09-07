import json

import httpx
import pytest
import respx

from sos.mapbuild import dem, hillshade
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx
from tests.test_buildmaps_contours import T50_API, T50_ENTRIES, TILE_LIST, _zip

PNG_HEADER = {"tile_type": "png", "minzoom": 5, "maxzoom": 12, "bounds": [-1.56, 50.87, -1.46, 50.97]}


DTM_INFO = {"size": [371, 589], "geoTransform": [-173658.40625, 30.0, 0.0, 6615988.78515625, 0.0, -30.0]}


def _fixture_ctx(tmp_path, header=PNG_HEADER):
    outer = _zip({"data/su/su41.zip": _zip({"SU41.asc": b"ncols 1\n"})})
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(header), "gdalinfo -json": json.dumps(DTM_INFO)},
                        files={"copernicus-tileList.txt": TILE_LIST, "terr50_gagg_gb.zip": outer, "hillshade.pmtiles": b"png-archive"})
    return make_ctx(tmp_path, fixture=True, runner=runner), runner


@respx.mock
def test_hillshade_step_runs_the_spec_pipeline_in_order(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    ctx, runner = _fixture_ctx(tmp_path)
    hillshade.HillshadeStep().run(ctx)
    work = ctx.src / "hillshade-work"
    tools = [c[0] if c[0] not in ("pmtiles", "gdal") else " ".join(c[:2 if c[0] == "pmtiles" else 3])
             for c in runner.calls if c[0] not in ("aria2c", "gdalinfo")]
    assert tools == ["gdalbuildvrt", "gdalbuildvrt", "ogr2ogr", "gdalwarp", "gdal_rasterize", "gdaldem", "gdal raster calc",
                     "gdalwarp", "gdal_translate", "gdaladdo", "pmtiles convert", "pmtiles show"]
    land = runner.find("ogr2ogr")[0]
    assert land == ["ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:3857", "-spat", "-1.56", "50.87", "-1.46", "50.97",
                    "-clipsrc", "-1.56", "50.87", "-1.46", "50.97", "-makevalid", "-nlt", "PROMOTE_TO_MULTI",
                    str(work / "land.gpkg"), f"/vsizip/{ctx.src / 'land-polygons-split-4326.zip'}/land-polygons-split-4326/land_polygons.shp"]
    warp = runner.find("gdalwarp")[0]
    assert warp[1:12] == ["-overwrite", "-t_srs", "EPSG:3857", "-tr", "30", "30", "-r", "bilinear", "-dstnodata", "-9999", "-te"]
    assert warp[12:18] == ["-1.56", "50.87", "-1.46", "50.97", "-te_srs", "EPSG:4326"]
    assert "-cutline" not in warp
    assert warp[-3:] == [str(work / "glo30.vrt"), str(work / "t50.vrt"), str(work / "dtm3857.tif")], "later inputs win: OS last"
    assert runner.find("gdalinfo")[0] == ["gdalinfo", "-json", str(work / "dtm3857.tif")]
    mask = runner.find("gdal_rasterize")[0]
    assert mask[1:9] == ["-burn", "1", "-init", "0", "-ot", "Byte", "-a_srs", "EPSG:3857"]
    assert mask[mask.index("-te") + 1:mask.index("-te") + 5] == ["-173658.40625", "6598318.78515625", "-162528.40625", "6615988.78515625"], \
        "the mask shares the mosaic's grid: extent from its geotransform at full precision"
    assert mask[mask.index("-ts") + 1:mask.index("-ts") + 3] == ["371", "589"]
    assert mask[-2:] == [str(work / "land.gpkg"), str(work / "land-mask.tif")]
    shade = runner.find("gdaldem")[0]
    assert shade[1:12] == ["hillshade", "-compute_edges", "-z", "1", "-s", "1", "-az", "315", "-alt", "45", "-co"]
    assert shade[-2:] == [str(work / "dtm3857.tif"), str(work / "hillshade-raw.tif")]
    calc = runner.find("gdal", "raster", "calc")[0]
    assert calc[calc.index("-i"):calc.index("-i") + 4] == ["-i", f"A={work / 'hillshade-raw.tif'}", "-i", f"B={work / 'land-mask.tif'}"]
    assert calc[calc.index("--calc") + 1] == "A*(B==1)" and calc[calc.index("--nodata") + 1] == "0", "shaded sea becomes 0, gdaldem's nodata"
    assert calc[-2:] == ["-o", str(work / "hillshade.tif")]
    translate = runner.find("gdal_translate")[0]
    alpha = runner.find("gdalwarp")[1]
    assert alpha[:4] == ["gdalwarp", "-overwrite", "-srcnodata", "0"] and "-dstalpha" in alpha
    assert alpha[-2:] == [str(work / "hillshade.tif"), str(work / "hillshade-alpha.tif")]
    assert translate == ["gdal_translate", "-of", "MBTILES", "-co", "TILE_FORMAT=PNG", "-co", "ZOOM_LEVEL_STRATEGY=LOWER",
                         str(work / "hillshade-alpha.tif"), str(work / "hillshade.mbtiles")]
    assert runner.find("gdaladdo")[0] == ["gdaladdo", "-r", "average", str(work / "hillshade.mbtiles"), "2", "4", "8", "16", "32", "64", "128"]
    assert runner.find("pmtiles", "convert")[0] == ["pmtiles", "convert", str(work / "hillshade.mbtiles"), str(ctx.incoming / "hillshade.pmtiles")]
    assert (ctx.out / "hillshade.pmtiles").read_bytes() == b"png-archive"
    side = json.loads((ctx.out / "hillshade.json").read_text())
    assert side["sources"] == ["glo30.vrt", "t50.vrt"] and side["header"]["tile_type"] == "png"
    assert side["land_mask"] == "land-polygons-split-4326.zip"


@respx.mock
def test_land_mask_is_the_osm_land_polygons_clipped_to_the_bbox(tmp_path):
    ctx, runner = _fixture_ctx(tmp_path)
    work = ctx.src / "hillshade-work"
    path = dem.land_mask(ctx, work)
    assert path == work / "land.gpkg"
    assert runner.find("aria2c")[0][-3:] == ["-o", "land-polygons-split-4326.zip", "https://example.test/land-polygons-split-4326.zip"]
    clip = runner.find("ogr2ogr")[0]
    assert clip[-2:] == [str(path), f"/vsizip/{ctx.src / 'land-polygons-split-4326.zip'}/land-polygons-split-4326/land_polygons.shp"]
    assert clip[clip.index("-clipsrc") + 1:clip.index("-clipsrc") + 5] == ["-1.56", "50.87", "-1.46", "50.97"]


@respx.mock
def test_hillshade_step_rejects_non_png_archive(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    ctx, _ = _fixture_ctx(tmp_path, header=dict(PNG_HEADER, tile_type="mvt"))
    with pytest.raises(BuildError, match="png"):
        hillshade.HillshadeStep().run(ctx)
    assert not (ctx.out / "hillshade.pmtiles").exists()
