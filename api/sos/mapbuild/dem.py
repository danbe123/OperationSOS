"""Digital terrain sources: Copernicus GLO-30 COGs, OS Terrain 50 ASCII grids and the OSNI 50 m DTM."""
from __future__ import annotations

import io
import math
import zipfile
from collections.abc import Iterable
from pathlib import Path

from .common import BBox, BuildError, Context, bbox_args, bbox_intersects, log
from .osdata import os_fetch, unzip_single

COPERNICUS_MAX_LAT = 57  # rows N49..N56 cover RoI, NI, IoM and CI; north of 57 N is Great Britain (OS Terrain 50)
NI_BBOX: BBox = (-8.2, 54.0, -5.4, 55.4)
OSNI_SRS = "EPSG:29902"  # TM65 / Irish Grid
T50_SRS = "EPSG:27700"
# Every source stores open sea as 0 m (Copernicus) or about -0.7 m (OS Terrain 50), and a VRT reads the gaps
# between its grids as 0 too, so without a nodata value the whole rectangle around a source shades as flat
# ground and the later source's gaps overwrite the earlier one. -9999 is below any real elevation.
DTM_NODATA = "-9999"
LAND_POLYGONS_ZIP = "land-polygons-split-4326.zip"
LAND_POLYGONS_SHP = "land-polygons-split-4326/land_polygons.shp"


def copernicus_name(lat: int, lon: int) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"


def copernicus_names(bbox: BBox, *, max_lat: int = COPERNICUS_MAX_LAT) -> list[str]:
    names = []
    for lat in range(math.floor(bbox[1]), min(math.ceil(bbox[3]), max_lat)):
        for lon in range(math.floor(bbox[0]), math.ceil(bbox[2])):
            names.append(copernicus_name(lat, lon))
    return names


def fetch_copernicus(ctx: Context, bbox: BBox) -> list[Path]:
    base = ctx.version("COPERNICUS_DEM_BASE")
    listing = set(ctx.download(f"{base}/tileList.txt", "copernicus-tileList.txt").read_text().split())
    paths = []
    for name in copernicus_names(bbox):
        if name not in listing:
            continue  # the bucket omits squares that are entirely ocean
        paths.append(ctx.download(f"{base}/{name}/{name}.tif", f"copernicus/{name}.tif"))
    if not paths:
        raise BuildError(f"no Copernicus GLO-30 tiles intersect {list(bbox)}")
    return paths


def terr50_asc_dir(ctx: Context) -> Path:
    """Unpack terr50_gagg_gb.zip (an outer zip of per-10 km inner zips) into one flat directory of .asc grids."""
    zip_path = os_fetch(ctx, "Terrain50", "terr50_gagg_gb.zip")
    root = ctx.src / "terr50_asc"
    marker = root / ".done"
    if marker.exists():
        return root
    root.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path) as outer:
        for member in outer.namelist():
            if not member.lower().endswith(".zip"):
                continue
            with zipfile.ZipFile(io.BytesIO(outer.read(member))) as inner:
                for name in inner.namelist():
                    if name.lower().endswith(".asc"):
                        (root / Path(name).name).write_bytes(inner.read(name))
                        count += 1
    if count == 0:
        raise BuildError(f"{zip_path.name} contained no .asc grids")
    marker.touch()
    log.info("[dem] unpacked %d OS Terrain 50 grids", count)
    return root


def osni_dtm(ctx: Context) -> Path | None:
    url = ctx.versions.get("OSNI_DTM_URL", "")
    if not url:
        log.warning("[dem] OSNI_DTM_URL is blank; Northern Ireland relief comes from Copernicus GLO-30")
        return None
    suffix = Path(url.split("?")[0]).suffix.lower() or ".tif"
    downloaded = ctx.download(url, f"osni-dtm50{suffix}")
    if suffix != ".zip":
        return downloaded
    dest = ctx.src / "osni-dtm50"
    for pattern in ("*.tif", "*.asc"):
        try:
            return unzip_single(downloaded, pattern, dest)
        except BuildError:
            continue
    raise BuildError("the OSNI DTM zip contains no single .tif or .asc")


def _input_list(work: Path, name: str, paths: Iterable[Path]) -> Path:
    listing = work / name
    listing.write_text("\n".join(str(p) for p in paths) + "\n")
    return listing


def dem_vrts(ctx: Context, work: Path) -> list[Path]:
    """Per-source VRTs in gdalwarp order (later inputs win): Copernicus, OSNI, then OS Terrain 50."""
    work.mkdir(parents=True, exist_ok=True)
    vrts: list[Path] = []
    glo = work / "glo30.vrt"
    ctx.run(["gdalbuildvrt", "-overwrite", "-vrtnodata", DTM_NODATA, "-input_file_list",
             str(_input_list(work, "glo30.txt", fetch_copernicus(ctx, ctx.bbox))), str(glo)])
    vrts.append(glo)
    osni = osni_dtm(ctx)
    if osni is not None and bbox_intersects(ctx.bbox, NI_BBOX):
        osni_vrt = work / "osni.vrt"
        ctx.run(["gdalbuildvrt", "-overwrite", "-vrtnodata", DTM_NODATA, "-a_srs", OSNI_SRS, str(osni_vrt), str(osni)])
        vrts.append(osni_vrt)
    grids = sorted(terr50_asc_dir(ctx).glob("*.asc"))
    if not grids:
        raise BuildError("no OS Terrain 50 .asc grids found")
    t50 = work / "t50.vrt"
    # A grid whose values happen to be whole metres opens as Int32 and gdalbuildvrt drops it as a mixed type.
    ctx.run(["gdalbuildvrt", "-overwrite", "-vrtnodata", DTM_NODATA, "-a_srs", T50_SRS, "-oo", "DATATYPE=Float32",
             "-input_file_list", str(_input_list(work, "t50.txt", grids)), str(t50)])
    vrts.append(t50)
    return vrts


def land_mask(ctx: Context, work: Path) -> Path:
    """OSM land polygons clipped to the bbox, in the mosaic's EPSG:3857, so the hillshade step can burn nodata into
    the sea: without this the 0 m sea shades as a flat grey box around each source."""
    work.mkdir(parents=True, exist_ok=True)
    zip_path = ctx.download(ctx.version("LAND_POLYGONS_URL"), LAND_POLYGONS_ZIP)
    out = work / "land.gpkg"
    out.unlink(missing_ok=True)
    ctx.run(["ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:3857", "-spat", *bbox_args(ctx.bbox), "-clipsrc", *bbox_args(ctx.bbox),
             "-makevalid", "-nlt", "PROMOTE_TO_MULTI", str(out), f"/vsizip/{zip_path}/{LAND_POLYGONS_SHP}"])
    return out


def nongb_dtm_vrt(ctx: Context, work: Path) -> Path:
    """One EPSG:4326 VRT over the non-GB sources for gdal_contour: Copernicus with OSNI warped on top."""
    work.mkdir(parents=True, exist_ok=True)
    inputs = [str(p) for p in fetch_copernicus(ctx, ctx.bbox)]
    osni = osni_dtm(ctx)
    if osni is not None and bbox_intersects(ctx.bbox, NI_BBOX):
        warped = work / "osni-4326.tif"
        ctx.run(["gdalwarp", "-overwrite", "-s_srs", OSNI_SRS, "-t_srs", "EPSG:4326", "-r", "bilinear",
                 "-dstnodata", "-9999", str(osni), str(warped)])
        inputs.append(str(warped))
    vrt = work / "nongb-4326.vrt"
    ctx.run(["gdalbuildvrt", "-overwrite", "-resolution", "highest", str(vrt), *inputs])
    return vrt
