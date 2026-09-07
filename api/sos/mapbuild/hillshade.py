"""Step `hillshade`: DTM mosaic in EPSG:3857 -> gdaldem hillshade -> MBTiles PNG8 -> gdaladdo -> PMTiles."""
from __future__ import annotations

import json
from pathlib import Path

from .common import BuildError, Context, bbox_args, pmtiles_header
from .dem import DTM_NODATA, LAND_POLYGONS_ZIP, dem_vrts, land_mask

PIPELINE = ("gdalwarp -t_srs EPSG:3857 -tr 30 30 (Copernicus, OSNI, OS Terrain 50; later inputs win; gaps are nodata) -> "
            "gdaldem hillshade -compute_edges -z 1 -s 1 -az 315 -alt 45 -> gdal raster calc x OSM land mask (sea is nodata) -> "
            "gdalwarp -dstalpha (sea transparent) -> gdal_translate MBTILES PNG -> gdaladdo 2..128 -> pmtiles convert")


def _info(ctx: Context, raster: Path) -> dict:
    return json.loads(ctx.run(["gdalinfo", "-json", str(raster)], capture=True).stdout)


def raster_extent(ctx: Context, raster: Path) -> list[str]:
    """`-te xmin ymin xmax ymax` of a raster at full precision, so a mask rasterised with it shares the grid exactly."""
    info = _info(ctx, raster)
    gt = info["geoTransform"]
    width, height = info["size"]
    return [repr(float(v)) for v in (gt[0], gt[3] + height * gt[5], gt[0] + width * gt[1], gt[3])]


def raster_size(ctx: Context, raster: Path) -> list[str]:
    return [str(v) for v in _info(ctx, raster)["size"]]


class HillshadeStep:
    id = "hillshade"

    def outputs(self, ctx: Context) -> list[str]:
        return ["hillshade.pmtiles"]

    def run(self, ctx: Context) -> None:
        work = ctx.src / "hillshade-work"
        work.mkdir(parents=True, exist_ok=True)
        vrts = dem_vrts(ctx, work)
        land = land_mask(ctx, work)
        dtm = work / "dtm3857.tif"
        ctx.run(["gdalwarp", "-overwrite", "-t_srs", "EPSG:3857", "-tr", "30", "30", "-r", "bilinear", "-dstnodata", DTM_NODATA,
                 "-te", *bbox_args(ctx.bbox), "-te_srs", "EPSG:4326", "-multi", "-wo", "NUM_THREADS=ALL_CPUS",
                 "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "BIGTIFF=YES",
                 *[str(v) for v in vrts], str(dtm)])
        # A 1/0 land mask on exactly the mosaic's grid, then the shaded sea is zeroed (0 is gdaldem's nodata) so
        # those pixels are transparent in the tiles. gdalwarp -cutline is not used: it rejects the coastline
        # as self-intersecting once transformed to pixel space and then silently writes an empty raster.
        mask = work / "land-mask.tif"
        ctx.run(["gdal_rasterize", "-burn", "1", "-init", "0", "-ot", "Byte", "-a_srs", "EPSG:3857",
                 "-te", *raster_extent(ctx, dtm), "-ts", *raster_size(ctx, dtm),
                 "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", str(land), str(mask)])
        raw = work / "hillshade-raw.tif"
        ctx.run(["gdaldem", "hillshade", "-compute_edges", "-z", "1", "-s", "1", "-az", "315", "-alt", "45",
                 "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "BIGTIFF=YES", str(dtm), str(raw)])
        shade = work / "hillshade.tif"
        ctx.run(["gdal", "raster", "calc", "--overwrite", "-i", f"A={raw}", "-i", f"B={mask}", "--calc", "A*(B==1)",
                 "--nodata", "0", "--ot", "UInt8", "--co", "TILED=YES", "--co", "COMPRESS=DEFLATE", "--co", "BIGTIFF=YES",
                 "-o", str(shade)])
        # The tiles must carry the transparency, not just the GeoTIFF: written straight from a one-band
        # raster the MBTiles held sea as opaque black, which the map drew at 35 % over the water as a
        # teal wash that ended in a jagged step wherever the tile coverage ended. An alpha band made
        # from the nodata makes the sea see-through in every tile and overview.
        alpha = work / "hillshade-alpha.tif"
        ctx.run(["gdalwarp", "-overwrite", "-srcnodata", "0", "-dstalpha", "-multi", "-wo", "NUM_THREADS=ALL_CPUS",
                 "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "BIGTIFF=YES", str(shade), str(alpha)])
        mbtiles = work / "hillshade.mbtiles"
        mbtiles.unlink(missing_ok=True)
        ctx.run(["gdal_translate", "-of", "MBTILES", "-co", "TILE_FORMAT=PNG", "-co", "ZOOM_LEVEL_STRATEGY=LOWER",
                 str(alpha), str(mbtiles)])
        ctx.run(["gdaladdo", "-r", "average", str(mbtiles), "2", "4", "8", "16", "32", "64", "128"])
        staged = ctx.stage("hillshade.pmtiles")
        ctx.run(["pmtiles", "convert", str(mbtiles), str(staged)])
        header = pmtiles_header(ctx, staged)
        if header.get("tile_type") != "png":
            raise BuildError(f"hillshade archive tile type is {header.get('tile_type')!r}, expected png")
        ctx.commit("hillshade.pmtiles")
        ctx.write_sidecar("hillshade.pmtiles", {"step": self.id, "sources": [v.name for v in vrts],
                                                "land_mask": LAND_POLYGONS_ZIP, "header": header, "pipeline": PIPELINE})
