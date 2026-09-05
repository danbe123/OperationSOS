"""OpenStreetMap input (Geofabrik PBF or the fixture extract) and region polygons derived from it."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .common import BuildError, Context, bbox_polygon, bbox_str, log, read_geojsonseq

# region id -> (property, value) on the OSM admin boundary relation
REGIONS: dict[str, tuple[str, str]] = {
    "roi": ("ISO3166-1", "IE"),
    "iom": ("ISO3166-1", "IM"),
    "jersey": ("ISO3166-1", "JE"),
    "guernsey": ("ISO3166-1", "GG"),
    "ni": ("name", "Northern Ireland"),
}
NON_GB = ("roi", "ni", "iom", "jersey", "guernsey")
REGION_LABELS = {"ni": "Northern Ireland", "roi": "Ireland", "iom": "Isle of Man", "jersey": "Jersey", "guernsey": "Guernsey"}


def osm_input(ctx: Context) -> Path:
    if not ctx.fixture:
        return ctx.download(ctx.version("GEOFABRIK_PBF_URL"), "britain-and-ireland-latest.osm.pbf")
    regional = ctx.download(ctx.version("GEOFABRIK_FIXTURE_PBF_URL"), "hampshire-latest.osm.pbf")
    clipped = ctx.src / "fixture.osm.pbf"
    if not clipped.exists() or ctx.force:
        ctx.run(["osmium", "extract", "--overwrite", "-s", "complete_ways", "-b", bbox_str(ctx.bbox),
                 "-o", str(clipped), str(regional)])
    return clipped


def export_config(ctx: Context, name: str) -> Path:
    return ctx.repo / "tools" / "map-styles" / "export" / f"{name}.json"


def select_region_features(features: Iterable[dict]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for feature in features:
        props = feature.get("properties") or {}
        if props.get("boundary") != "administrative":
            continue
        for region, (key, value) in REGIONS.items():
            if region not in found and props.get(key) == value:
                found[region] = feature
    return found


def region_polygons(ctx: Context, pbf: Path) -> dict[str, Path]:
    out_dir = ctx.src / "regions"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {region: out_dir / f"{region}.geojson" for region in REGIONS}
    if all(p.exists() for p in paths.values()) and not ctx.force:
        return paths
    admin = out_dir / "admin.osm.pbf"
    ctx.run(["osmium", "tags-filter", "--overwrite", "-o", str(admin), str(pbf), "r/admin_level=2,4"])
    seq = out_dir / "admin.geojsonseq"
    ctx.run(["osmium", "export", "--overwrite", "-f", "geojsonseq", "--geometry-types=polygon",
             "-c", str(export_config(ctx, "regions")), "-o", str(seq), str(admin)])
    found = select_region_features(read_geojsonseq(seq)) if seq.exists() else {}
    for region, path in paths.items():
        feature = found.get(region)
        if feature is None:
            log.warning("[osm] no admin boundary for %s in %s", region, pbf.name)
        path.write_text(json.dumps({"type": "FeatureCollection", "features": [feature] if feature else []}))
    return paths


def nongb_cutline(ctx: Context, pbf: Path | None) -> Path:
    """Polygons of the areas whose terrain comes from Copernicus/OSNI rather than OS Terrain 50.
    In fixture mode the whole fixture bbox counts as non-GB so gdal_contour is exercised."""
    path = ctx.src / "regions" / "nongb-cutline.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    if ctx.fixture:
        path.write_text(json.dumps(bbox_polygon(ctx.bbox)))
        return path
    if pbf is None:
        raise BuildError("nongb_cutline needs the OSM PBF outside fixture mode")
    features: list[dict] = []
    for region, region_path in region_polygons(ctx, pbf).items():
        if region in NON_GB:
            features.extend(json.loads(region_path.read_text())["features"])
    if not features:
        raise BuildError("no non-GB region polygons were found (admin boundaries missing from the PBF)")
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return path
