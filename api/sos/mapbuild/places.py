"""Step `places`: OS Open Names (GB) plus OSM place nodes (NI, RoI, IoM, CI) -> places.csv.gz."""
from __future__ import annotations

import csv
import gzip
import io
import json
import zipfile
from pathlib import Path
from typing import Iterable, Iterator

from .common import BBox, BuildError, Context, log, read_geojsonseq
from .osdata import os_fetch
from .osm import NON_GB, REGION_LABELS, export_config, osm_input, region_polygons

LOCAL_TYPES = {"City": "city", "Town": "town", "Village": "village", "Hamlet": "hamlet", "Other Settlement": "other-settlement",
               "Postcode": "postcode", "Named Road": "named-road", "Section Of Named Road": "named-road"}
ROAD_TYPES = ("Named Road", "Section Of Named Road")
OSM_PLACE_KINDS = ("city", "town", "village", "hamlet", "suburb", "locality")
OSM_PLACE_FILTER = "n/place=city,town,village,hamlet,suburb,locality"
COLUMNS = ("name", "kind", "lat", "lon", "region", "postcode")
HEADER_MEMBER = "OS_Open_Names_Header.csv"
CHUNK = 200_000

RawRow = tuple[str, str, float, float, str, str]  # name, kind, x, y, region, postcode (EPSG:27700)


def make_transformer(inverse: bool = False):
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise BuildError("pyproj is required for the places step: pip install -e 'api[maps]'") from exc
    if inverse:
        return Transformer.from_crs(4326, 27700, always_xy=True)
    return Transformer.from_crs(27700, 4326, always_xy=True)


def read_header(zf: zipfile.ZipFile) -> list[str]:
    for member in zf.namelist():
        if member.endswith(HEADER_MEMBER):
            with zf.open(member) as handle:
                return next(csv.reader(io.TextIOWrapper(handle, encoding="utf-8-sig")))
    raise BuildError(f"{HEADER_MEMBER} not found in the OS Open Names zip")


def os_names_rows(zf: zipfile.ZipFile, header: list[str]) -> Iterator[dict]:
    for member in sorted(zf.namelist()):
        if "Data/" not in member or not member.lower().endswith(".csv"):
            continue
        with zf.open(member) as handle:
            yield from csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"), fieldnames=header)


def reduce_os_rows(rows: Iterable[dict], *, os_bbox: tuple[float, float, float, float] | None = None) -> list[RawRow]:
    settlements: list[RawRow] = []
    roads: dict[tuple[str, str], list] = {}
    for row in rows:
        local_type = row.get("LOCAL_TYPE") or ""
        kind = LOCAL_TYPES.get(local_type)
        if kind is None:
            continue
        name = (row.get("NAME1") or "").strip()
        if not name:
            continue
        try:
            x, y = float(row["GEOMETRY_X"]), float(row["GEOMETRY_Y"])
        except (KeyError, TypeError, ValueError):
            continue
        if os_bbox and not (os_bbox[0] <= x <= os_bbox[2] and os_bbox[1] <= y <= os_bbox[3]):
            continue
        region = row.get("REGION") or row.get("COUNTY_UNITARY") or row.get("COUNTRY") or ""
        district = row.get("POSTCODE_DISTRICT") or ""
        if local_type in ROAD_TYPES:
            place = row.get("POPULATED_PLACE") or ""
            acc = roads.setdefault((name, place), [0.0, 0.0, 0, region, district])
            acc[0] += x
            acc[1] += y
            acc[2] += 1
            continue
        settlements.append((name, kind, x, y, region, name if kind == "postcode" else district))
    for (name, place), (sx, sy, n, region, district) in roads.items():
        settlements.append((name, "named-road", sx / n, sy / n, place or region, district))
    return settlements


def transform_rows(rows: list[RawRow], transformer, *, bbox: BBox | None = None) -> list[list]:
    out: list[list] = []
    for start in range(0, len(rows), CHUNK):
        chunk = rows[start:start + CHUNK]
        lons, lats = transformer.transform([r[2] for r in chunk], [r[3] for r in chunk])
        for row, lon, lat in zip(chunk, lons, lats):
            if bbox and not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
                continue
            out.append([row[0], row[1], round(lat, 5), round(lon, 5), row[4], row[5]])
    return out


def os_bbox_for(bbox: BBox, inverse_transformer, margin_m: float = 2000.0) -> tuple[float, float, float, float]:
    xs, ys = inverse_transformer.transform([bbox[0], bbox[2], bbox[0], bbox[2]], [bbox[1], bbox[1], bbox[3], bbox[3]])
    return (min(xs) - margin_m, min(ys) - margin_m, max(xs) + margin_m, max(ys) + margin_m)


def osm_place_rows(features: Iterable[dict], region_label: str) -> list[list]:
    rows: list[list] = []
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        name = (props.get("name") or "").strip()
        if not name or props.get("place") not in OSM_PLACE_KINDS or geom.get("type") != "Point":
            continue
        lon, lat = geom["coordinates"][:2]
        rows.append([name, props["place"], round(lat, 5), round(lon, 5), region_label, ""])
    return rows


def osm_places(ctx: Context, work: Path) -> list[list]:
    work.mkdir(parents=True, exist_ok=True)
    pbf = osm_input(ctx)
    filtered = work / "places.osm.pbf"
    ctx.run(["osmium", "tags-filter", "--overwrite", "-o", str(filtered), str(pbf), OSM_PLACE_FILTER])
    seq = work / "places.geojsonseq"
    ctx.run(["osmium", "export", "--overwrite", "-f", "geojsonseq", "--geometry-types=point",
             "-c", str(export_config(ctx, "places")), "-o", str(seq), str(filtered)])
    if ctx.fixture:
        log.info("[places] fixture bbox is in Great Britain; OSM place nodes are not added")
        return []
    rows: list[list] = []
    polygons = region_polygons(ctx, pbf)
    for region in NON_GB:
        polygon = polygons[region]
        if not json.loads(polygon.read_text())["features"]:
            log.warning("[places] no polygon for %s; its OSM places are skipped", region)
            continue
        clipped = work / f"places_{region}.geojsonseq"
        clipped.unlink(missing_ok=True)
        ctx.run(["ogr2ogr", "-f", "GeoJSONSeq", "-clipsrc", str(polygon), str(clipped), str(seq)])
        if clipped.exists():
            rows.extend(osm_place_rows(read_geojsonseq(clipped), REGION_LABELS[region]))
    return rows


def write_places(path: Path, rows: Iterable[list]) -> int:
    count = 0
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


class PlacesStep:
    id = "places"

    def outputs(self, ctx: Context) -> list[str]:
        return ["places.csv.gz"]

    def run(self, ctx: Context) -> None:
        work = ctx.src / "places-work"
        zip_path = os_fetch(ctx, "OpenNames", "opname_csv_gb.zip")
        transformer = make_transformer()
        os_bbox = os_bbox_for(ctx.bbox, make_transformer(inverse=True)) if ctx.fixture else None
        with zipfile.ZipFile(zip_path) as zf:
            raw = reduce_os_rows(os_names_rows(zf, read_header(zf)), os_bbox=os_bbox)
        gb_rows = transform_rows(raw, transformer, bbox=ctx.bbox if ctx.fixture else None)
        osm_rows = osm_places(ctx, work)
        rows = sorted(gb_rows + osm_rows, key=lambda r: (r[0].lower(), r[1], r[4]))
        if not rows:
            raise BuildError("the places step produced no rows")
        staged = ctx.stage("places.csv.gz")
        count = write_places(staged, rows)
        ctx.commit("places.csv.gz")
        log.info("[places] %d rows (%d OS Open Names, %d OSM)", count, len(gb_rows), len(osm_rows))
        ctx.write_sidecar("places.csv.gz", {"step": self.id, "rows": count, "gb_rows": len(gb_rows), "osm_rows": len(osm_rows),
                                            "columns": list(COLUMNS), "source": "OS Open Names (opname_csv_gb.zip) + OSM place nodes"})
