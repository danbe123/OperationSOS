"""Step `hillshade`: DTM mosaic in EPSG:3857 -> gdaldem hillshade -> MBTiles PNG8 -> gdaladdo -> PMTiles."""
from __future__ import annotations

from .common import BuildError, Context, bbox_args, pmtiles_header
from .dem import dem_vrts

PIPELINE = ("gdalwarp -t_srs EPSG:3857 -tr 30 30 (Copernicus, OSNI, OS Terrain 50; later inputs win) -> "
            "gdaldem hillshade -compute_edges -z 1 -s 1 -az 315 -alt 45 -> gdal_translate MBTILES PNG8 -> "
            "gdaladdo 2..128 -> pmtiles convert")


class HillshadeStep:
    id = "hillshade"

    def outputs(self, ctx: Context) -> list[str]:
        return ["hillshade.pmtiles"]

    def run(self, ctx: Context) -> None:
        work = ctx.src / "hillshade-work"
        work.mkdir(parents=True, exist_ok=True)
        vrts = dem_vrts(ctx, work)
        dtm = work / "dtm3857.tif"
        ctx.run(["gdalwarp", "-overwrite", "-t_srs", "EPSG:3857", "-tr", "30", "30", "-r", "bilinear", "-dstnodata", "-9999",
                 "-te", *bbox_args(ctx.bbox), "-te_srs", "EPSG:4326", "-multi", "-wo", "NUM_THREADS=ALL_CPUS",
                 "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "BIGTIFF=YES",
                 *[str(v) for v in vrts], str(dtm)])
        shade = work / "hillshade.tif"
        ctx.run(["gdaldem", "hillshade", "-compute_edges", "-z", "1", "-s", "1", "-az", "315", "-alt", "45",
                 "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "BIGTIFF=YES", str(dtm), str(shade)])
        mbtiles = work / "hillshade.mbtiles"
        mbtiles.unlink(missing_ok=True)
        ctx.run(["gdal_translate", "-of", "MBTILES", "-co", "TILE_FORMAT=PNG8", "-co", "ZOOM_LEVEL_STRATEGY=LOWER",
                 str(shade), str(mbtiles)])
        ctx.run(["gdaladdo", "-r", "average", str(mbtiles), "2", "4", "8", "16", "32", "64", "128"])
        staged = ctx.stage("hillshade.pmtiles")
        ctx.run(["pmtiles", "convert", str(mbtiles), str(staged)])
        header = pmtiles_header(ctx, staged)
        if header.get("tile_type") != "png":
            raise BuildError(f"hillshade archive tile type is {header.get('tile_type')!r}, expected png")
        ctx.commit("hillshade.pmtiles")
        ctx.write_sidecar("hillshade.pmtiles", {"step": self.id, "sources": [v.name for v in vrts],
                                                "header": header, "pipeline": PIPELINE})
