"""Step `contours`: OS Terrain 50 vector tiles (GB) plus gdal_contour over the non-GB DTM, merged with tile-join."""
from __future__ import annotations

from .common import BuildError, Context, bbox_str, pmtiles_header, pmtiles_metadata, vector_layer_ids
from .dem import nongb_dtm_vrt
from .osdata import os_fetch, unzip_single
from .osm import nongb_cutline, osm_input

PREFERRED_HEIGHT_FIELDS = ("height", "HEIGHT", "PROP_VALUE", "prop_value", "elevation", "ELEVATION")
CONTOUR_INTERVAL_M = "10"


def contour_height_field(metadata: dict) -> str:
    for layer in metadata.get("vector_layers", []):
        if layer.get("id") != "contour_line":
            continue
        fields = layer.get("fields", {})
        for name in PREFERRED_HEIGHT_FIELDS:
            if name in fields:
                return name
        numeric = [name for name, kind in fields.items() if kind == "Number"]
        if numeric:
            return numeric[0]
        raise BuildError(f"contour_line has no numeric height field: {fields}")
    raise BuildError("the OS Terrain 50 tiles have no contour_line layer")


class ContoursStep:
    id = "contours"

    def outputs(self, ctx: Context) -> list[str]:
        return ["contours.pmtiles"]

    def run(self, ctx: Context) -> None:
        work = ctx.src / "contours-work"
        work.mkdir(parents=True, exist_ok=True)
        mbtiles = unzip_single(os_fetch(ctx, "Terrain50", "terr50_mbtiles_gb.zip"), "*.mbtiles", ctx.src / "terr50_mbtiles")
        gb_full = ctx.src / "contours-gb-full.pmtiles"
        if not gb_full.exists():
            ctx.run(["pmtiles", "convert", str(mbtiles), str(gb_full)])
        gb = gb_full
        if ctx.fixture:
            gb = work / "contours-gb.pmtiles"
            ctx.run(["pmtiles", "extract", str(gb_full), str(gb), f"--bbox={bbox_str(ctx.bbox)}"])
        height = contour_height_field(pmtiles_metadata(ctx, gb))

        dtm = nongb_dtm_vrt(ctx, work)
        cutline = nongb_cutline(ctx, None if ctx.fixture else osm_input(ctx))
        clipped = work / "nongb-clip.tif"
        ctx.run(["gdalwarp", "-overwrite", "-t_srs", "EPSG:4326", "-r", "bilinear", "-dstnodata", "-9999",
                 "-cutline", str(cutline), "-crop_to_cutline", "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
                 str(dtm), str(clipped)])
        fgb = work / "nongb-contours.fgb"
        fgb.unlink(missing_ok=True)
        ctx.run(["gdal_contour", "-i", CONTOUR_INTERVAL_M, "-a", height, "-snodata", "-9999", "-f", "FlatGeobuf",
                 str(clipped), str(fgb)])
        nongb = work / "contours-nongb.pmtiles"
        ctx.run(["tippecanoe", "-o", str(nongb), "-l", "contour_line", "-Z11", "-z14", "-P", "--drop-densest-as-needed",
                 "--force", str(fgb)])

        staged = ctx.stage("contours.pmtiles")
        ctx.run(["tile-join", "-o", str(staged), "-pk", "--force", str(gb), str(nongb)])
        layers = sorted(vector_layer_ids(pmtiles_metadata(ctx, staged)))
        if "contour_line" not in layers:
            raise BuildError(f"merged contours have no contour_line layer: {layers}")
        header = pmtiles_header(ctx, staged)
        ctx.commit("contours.pmtiles")
        ctx.write_sidecar("contours.pmtiles", {
            "step": self.id, "height_field": height, "layers": layers, "interval_m": 10,
            "gb_source": "OS Terrain 50 vector tiles (terr50_mbtiles_gb.zip)",
            "non_gb_source": "gdal_contour over Copernicus GLO-30 (OSNI on top where configured)",
            "header": header})
