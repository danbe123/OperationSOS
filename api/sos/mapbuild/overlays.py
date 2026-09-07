"""Step `overlays`: footpaths, OSM point overlays, flood zones, access land, nuclear and chemical sites."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .common import BBox, BuildError, Context, bbox_args, log, validate_geojson
from .osm import export_config, osm_input

SIZE_RULE_BYTES = 5 * 1024 * 1024
MIN_NUCLEAR_SITES = 20
PATH_HIGHWAYS = "w/highway=path,footway,bridleway,track,cycleway,steps"
FOOTPATH_FILTER = '{"footpaths":["any",[">=","$zoom",13],["has","designation"]]}'


@dataclass(frozen=True)
class OsmOverlay:
    id: str
    filters: tuple[str, ...]
    points: bool  # True: ST_PointOnSurface markers; False: keep polygons
    tags: tuple[str, ...]  # the OSM keys kept on every feature (spec section 5); everything else is dropped


OSM_OVERLAYS: tuple[OsmOverlay, ...] = (
    OsmOverlay("health", ("nwr/amenity=hospital,pharmacy,doctors,clinic",), True,
               ("name", "amenity", "healthcare", "emergency", "beds", "operator", "phone", "website", "opening_hours", "wheelchair", "dispensing")),
    OsmOverlay("fuel", ("nwr/amenity=fuel",), True,
               ("name", "brand", "operator", "opening_hours", "phone", "fuel:diesel", "fuel:lpg", "fuel:electricity", "shop")),
    OsmOverlay("water", ("nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works", "nwr/natural=spring"), False,
               ("name", "man_made", "natural", "water", "landuse", "operator", "description")),
    OsmOverlay("rail", ("nwr/railway=station",), True,
               ("name", "railway", "station", "operator", "network", "platforms", "wheelchair")),
    OsmOverlay("chemical-sites", ("nwr/industrial=chemical,refinery,oil",), True,
               ("name", "industrial", "landuse", "man_made", "operator", "hazmat", "description")),
    OsmOverlay("airports", ("nwr/aeroway=aerodrome",), False,
               ("name", "aeroway", "aerodrome", "aerodrome:type", "icao", "iata", "operator", "surface", "military")),
    OsmOverlay("military", ("nwr/military=*", "nwr/landuse=military"), False,
               ("name", "military", "landuse", "operator", "description", "access")),
)
HAND_AUTHORED = {"chemical-sites": "chemical-sites.geojson"}
FLOOD_TAGS = ("z2", "z3", "river", "coastal")
FLOOD_REGIONS = (("england", "FLOOD_EN_URL"), ("wales", "FLOOD_WA_URL"), ("scotland", "FLOOD_SC_URL"),
                 ("ni", "FLOOD_NI_URL"), ("roi", "FLOOD_IE_URL"))
ACCESS_REGIONS = (("england", "ACCESS_EN_URL"), ("wales", "ACCESS_WA_URL"))


@dataclass(frozen=True)
class VectorSource:
    source: str
    open_options: tuple[str, ...] = ()
    layer: str | None = None


def parse_source_specs(value: str) -> list[tuple[str, str | None, str | None]]:
    """`url[|layer][#tag]` entries separated by whitespace: (url, layer, tag) each."""
    out = []
    for entry in value.split():
        body, _, tag = entry.partition("#")
        url, _, layer = body.partition("|")
        out.append((url.strip(), layer.strip() or None, tag.strip() or None))
    return out


def vector_source(ctx: Context, spec: str, name: str) -> VectorSource:
    """Turn one entry into what ogr2ogr reads: /vsizip/ of a cached zip, a paged FeatureServer query, or the URL."""
    url, layer, _ = parse_source_specs(spec)[0]
    if url.lower().endswith(".zip"):
        path = ctx.download(url, f"{name}.zip")
        return VectorSource(f"/vsizip/{path}", (), layer)
    if "/FeatureServer/" in url or "/MapServer/" in url:
        # A value that already carries its own /query?… is used as written, so a service that cannot
        # serialise its polygons whole (SEPA's coastal layer answers 500) can be asked with
        # maxAllowableOffset or any other parameter it needs.
        query = url if "/query?" in url else f"{url.rstrip('/')}/query?where=1%3D1&outFields=*&f=json"
        return VectorSource(query, ("-oo", "FEATURE_SERVER_PAGING=YES"), layer)
    return VectorSource(url, (), layer)


# A paged FeatureServer pull of half a million polygons takes minutes over one connection, and the
# Welsh flood service reset it partway through the first full build. GDAL retries a reset or a 5xx
# itself with these; the loop below starts the whole translation again when it still gives up.
HTTP_RETRY_OPTIONS = ("--config", "GDAL_HTTP_MAX_RETRY", "5", "--config", "GDAL_HTTP_RETRY_DELAY", "10")
HTTP_ATTEMPTS = 3


def ogr_to(ctx: Context, fmt: str, dest: Path, src: VectorSource, *, spat: BBox | None = None) -> None:
    remote = src.source.startswith(("http://", "https://"))
    cmd = ["ogr2ogr", "-f", fmt, "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI"]
    if remote:
        cmd += HTTP_RETRY_OPTIONS
    if spat:
        cmd += ["-spat", *bbox_args(spat)]
    cmd += [*src.open_options, str(dest), src.source]
    if src.layer:
        cmd.append(src.layer)
    for attempt in range(1, (HTTP_ATTEMPTS if remote else 1) + 1):
        dest.unlink(missing_ok=True)
        try:
            ctx.run(cmd)
            return
        except BuildError:
            if attempt == HTTP_ATTEMPTS or not remote:
                raise
            log.warning("[overlays] %s attempt %d failed; trying again", src.source.split("?")[0], attempt)


def region_sources(ctx: Context, regions: tuple[tuple[str, str], ...], *, fixture_sample: str) -> list[tuple[str, str | None, VectorSource]]:
    """(region, tag, source) for every configured entry; a region with two entries yields two rows."""
    if ctx.fixture:
        sample = ctx.repo / "api" / "tests" / "fixtures" / "maps" / "src" / fixture_sample
        return [("england", None, VectorSource(str(sample)))]
    found = []
    for region, key in regions:
        specs = parse_source_specs(ctx.versions.get(key, ""))
        if not specs:
            log.warning("[overlays] %s is blank; %s skipped", key, region)
            continue
        for i, (url, layer, tag) in enumerate(specs):
            found.append((region, tag, vector_source(ctx, f"{url}|{layer or ''}", f"{key.lower()}_{i}")))
    return found


def flood_coverage(layers: list[str]) -> list[str]:
    seen: list[str] = []
    for layer in layers:
        region = layer.removeprefix("flood_").split("_")[0]
        if region not in seen:
            seen.append(region)
    return seen


def load_geojson(path: Path) -> dict:
    obj = json.loads(path.read_text())
    problems = validate_geojson(obj)
    if problems:
        raise BuildError(f"{path}: {'; '.join(problems[:3])}")
    return obj


def merge_feature_collections(collections: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": [f for c in collections for f in c.get("features", [])]}


def build_footpaths(ctx: Context, pbf: Path, work: Path, staged_dir: Path) -> Path:
    filtered = work / "paths.osm.pbf"
    ctx.run(["osmium", "tags-filter", "--overwrite", "-o", str(filtered), str(pbf), PATH_HIGHWAYS])
    seq = work / "paths.geojsonseq"
    ctx.run(["osmium", "export", "--overwrite", "-f", "geojsonseq", "--geometry-types=linestring",
             "-c", str(export_config(ctx, "paths")), "-o", str(seq), str(filtered)])
    out = staged_dir / "footpaths.pmtiles"
    ctx.run(["tippecanoe", "-o", str(out), "-l", "footpaths", "-Z10", "-z15", "-P", "--drop-densest-as-needed",
             "--extend-zooms-if-still-dropping", "--force", "-j", FOOTPATH_FILTER, str(seq)])
    return out


def export_config_for(ctx: Context, overlay: OsmOverlay, work: Path) -> Path:
    """osmium export config for one overlay: the pois.json template with this overlay's own allow-list."""
    template = json.loads((ctx.repo / "tools" / "map-styles" / "export" / "pois.json").read_text())
    template["include_tags"] = list(overlay.tags)
    path = work / f"{overlay.id}-export.json"
    path.write_text(json.dumps(template, indent=2) + "\n")
    return path


def build_osm_overlay(ctx: Context, overlay: OsmOverlay, pbf: Path, work: Path) -> Path:
    filtered = work / f"{overlay.id}.osm.pbf"
    ctx.run(["osmium", "tags-filter", "--overwrite", "-o", str(filtered), str(pbf), *overlay.filters])
    raw = work / f"{overlay.id}_raw.geojson"
    ctx.run(["osmium", "export", "--overwrite", "-f", "geojson", "--add-unique-id=type_id",
             "-c", str(export_config_for(ctx, overlay, work)), "-o", str(raw), str(filtered)])
    if not overlay.points:
        return raw
    out = work / f"{overlay.id}.geojson"
    out.unlink(missing_ok=True)
    ctx.run(["ogr2ogr", "-f", "GeoJSON", str(out), str(raw), "-dialect", "sqlite",
             "-sql", f'SELECT ST_PointOnSurface(geometry) AS geometry, * FROM "{raw.stem}"'])
    return out


def finalise(ctx: Context, overlay_id: str, geojson: Path, staged_dir: Path) -> tuple[str, str]:
    """Copy as GeoJSON, or tile with tippecanoe when the file exceeds 5 MB (spec section 9).

    Applied uniformly to every size-gated overlay, including access-land: whichever side of the
    5 MB line the real measured output lands on decides `kind`, never a hardcoded per-overlay choice."""
    if geojson.stat().st_size <= SIZE_RULE_BYTES:
        shutil.copyfile(geojson, staged_dir / f"{overlay_id}.geojson")
        return "geojson", f"{overlay_id}.geojson"
    out = staged_dir / f"{overlay_id}.pmtiles"
    ctx.run(["tippecanoe", "-o", str(out), "-l", overlay_id, "-zg", "--coalesce-densest-as-needed", "--detect-shared-borders",
             "--extend-zooms-if-still-dropping", "--force", str(geojson)])
    return "pmtiles", f"{overlay_id}.pmtiles"


def build_flood_zones(ctx: Context, work: Path, staged_dir: Path) -> tuple[Path, list[str]]:
    built: list[tuple[str, Path]] = []
    for region, tag, src in region_sources(ctx, FLOOD_REGIONS, fixture_sample="flood-england-sample.geojson"):
        if tag is not None and tag not in FLOOD_TAGS:
            raise BuildError(f"FLOOD_*: tag '{tag}' is not one of {', '.join(FLOOD_TAGS)}")
        layer = f"flood_{region}" + (f"_{tag}" if tag else "")
        fgb = work / f"{layer}.fgb"
        ogr_to(ctx, "FlatGeobuf", fgb, src, spat=ctx.bbox if ctx.fixture else None)
        built.append((layer, fgb))
    if not built:
        raise BuildError("no flood-zone sources configured: set FLOOD_EN_URL, FLOOD_WA_URL, FLOOD_SC_URL, FLOOD_NI_URL or FLOOD_IE_URL")
    out = staged_dir / "flood-zones.pmtiles"
    cmd = ["tippecanoe", "-o", str(out), "-Z8", "-z14", "-P", "--detect-shared-borders", "--coalesce-densest-as-needed",
           "--simplification=6", "--force"]
    for layer, fgb in built:
        cmd += ["-L", f"{layer}:{fgb}"]
    ctx.run(cmd)
    return out, [layer for layer, _ in built]


def build_access_land(ctx: Context, work: Path, staged_dir: Path) -> tuple[str, str, list[str]]:
    collections: list[dict] = []
    regions: list[str] = []
    sources = region_sources(ctx, ACCESS_REGIONS, fixture_sample="access-england-sample.geojson")
    counts: dict[str, int] = {}
    for region, _, _ in sources:
        counts[region] = counts.get(region, 0) + 1
    seen: dict[str, int] = {}
    for region, tag, src in sources:
        if counts[region] > 1:
            i = seen.get(region, 0)
            seen[region] = i + 1
            geojson = work / f"access_{region}_{i}.geojson"
        else:
            geojson = work / f"access_{region}.geojson"
        ogr_to(ctx, "GeoJSON", geojson, src, spat=ctx.bbox if ctx.fixture else None)
        obj = load_geojson(geojson)
        for feature in obj["features"]:
            feature.setdefault("properties", {}).setdefault("region", region)
            if tag:
                feature["properties"].setdefault("designation", tag)
        collections.append(obj)
        if region not in regions:
            regions.append(region)
    if not collections:
        raise BuildError("no access-land sources configured: set ACCESS_EN_URL or ACCESS_WA_URL")
    combined = work / "access-land.geojson"
    combined.write_text(json.dumps(merge_feature_collections(collections)))
    # Same 5 MB rule as every other overlay (correction R3): the real UK+Wales access-land extract
    # measures well over 5 MB, so this crosses to pmtiles on a full build; the fixture sample stays tiny.
    kind, name = finalise(ctx, "access-land", combined, staged_dir)
    return kind, name, regions


def nuclear_sites(ctx: Context) -> dict:
    path = ctx.repo / "tools" / "map-styles" / "data" / "nuclear-sites.geojson"
    if not path.exists():
        raise BuildError(f"{path} is missing")
    obj = load_geojson(path)
    if len(obj["features"]) < MIN_NUCLEAR_SITES:
        raise BuildError(f"nuclear-sites.geojson has {len(obj['features'])} features; at least {MIN_NUCLEAR_SITES} expected")
    for feature in obj["features"]:
        geom = feature["geometry"]
        if geom["type"] != "Point":
            raise BuildError(f"nuclear site {feature['properties'].get('name')!r} is not a Point")
        lon, lat = geom["coordinates"][:2]
        if not (-11 <= lon <= 2.2 and 49.1 <= lat <= 61.2):
            raise BuildError(f"nuclear site {feature['properties'].get('name')!r} lies outside the UK and Ireland bbox")
    return obj


def verify_manifest_kinds(ctx: Context, index: dict[str, dict]) -> None:
    """Production builds only (correction R3): catch a build output whose `kind`/`dest` has drifted from
    manifest/overlays.json. Skipped in fixture mode, where tiny sample data always finalises under the
    5 MB rule regardless of what the full production dataset for that overlay id turns out to be."""
    manifest_path = ctx.repo / "manifest" / "overlays.json"
    if not manifest_path.exists():
        return
    by_id = {item["id"]: item for item in json.loads(manifest_path.read_text())["items"]}
    for overlay_id, entry in index.items():
        item = by_id.get(overlay_id)
        if item is None:
            continue
        want_dest = f"maps/{entry['file']}"
        if item["kind"] != entry["kind"] or item["dest"] != want_dest:
            raise BuildError(
                f"manifest/overlays.json is out of date for {overlay_id!r}: "
                f"manifest says kind={item['kind']!r} dest={item['dest']!r}, "
                f"the build produced kind={entry['kind']!r} dest={want_dest!r}")


class OverlaysStep:
    id = "overlays"

    def outputs(self, ctx: Context) -> list[str]:
        return ["overlays/index.json", "overlays/footpaths.pmtiles", "overlays/flood-zones.pmtiles", "overlays/nuclear-sites.geojson"]

    def run(self, ctx: Context) -> None:
        work = ctx.src / "overlays-work"
        work.mkdir(parents=True, exist_ok=True)
        pbf = osm_input(ctx)
        staged_dir = ctx.stage("overlays")
        staged_dir.mkdir()
        index: dict[str, dict] = {}

        build_footpaths(ctx, pbf, work, staged_dir)
        index["footpaths"] = {"kind": "pmtiles", "file": "overlays/footpaths.pmtiles", "layers": ["footpaths"]}

        for overlay in OSM_OVERLAYS:
            geojson = build_osm_overlay(ctx, overlay, pbf, work)
            if overlay.id in HAND_AUTHORED:
                hand = ctx.repo / "tools" / "map-styles" / "data" / HAND_AUTHORED[overlay.id]
                combined = work / f"{overlay.id}-combined.geojson"
                combined.write_text(json.dumps(merge_feature_collections([load_geojson(geojson), load_geojson(hand)])))
                geojson = combined
            kind, name = finalise(ctx, overlay.id, geojson, staged_dir)
            entry: dict = {"kind": kind, "file": f"overlays/{name}"}
            if kind == "geojson":
                entry["features"] = len(load_geojson(staged_dir / name)["features"])
            else:
                entry["layers"] = [overlay.id]
            index[overlay.id] = entry

        _, layers = build_flood_zones(ctx, work, staged_dir)
        index["flood-zones"] = {"kind": "pmtiles", "file": "overlays/flood-zones.pmtiles", "layers": layers,
                                "coverage": flood_coverage(layers)}
        kind, name, regions = build_access_land(ctx, work, staged_dir)
        index["access-land"] = {"kind": kind, "file": f"overlays/{name}", "coverage": regions}

        nuclear = nuclear_sites(ctx)
        (staged_dir / "nuclear-sites.geojson").write_text(json.dumps(nuclear))
        index["nuclear-sites"] = {"kind": "geojson", "file": "overlays/nuclear-sites.geojson", "features": len(nuclear["features"])}

        for entry in index.values():
            entry["size_bytes"] = (staged_dir / Path(entry["file"]).name).stat().st_size
        if not ctx.fixture:
            verify_manifest_kinds(ctx, index)
        (staged_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
        ctx.commit("overlays")
        log.info("[overlays] %s", ", ".join(f"{k}={v['kind']}" for k, v in index.items()))
        ctx.write_sidecar("overlays", {"step": self.id, "osm_input": pbf.name, "overlays": sorted(index)})
