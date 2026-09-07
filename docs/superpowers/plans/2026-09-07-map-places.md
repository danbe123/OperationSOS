# Map places Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The map's overlays are always in view as chips, there is one base map, airports and military bases are separate overlays, every overlay keeps the OSM facts a household needs, flood zones and access land cover every nation that publishes them, and tapping a place opens a card that says what it is, how far it is and what to expect there.

**Architecture:** The build (`api/sos/mapbuild/overlays.py`) gains a per-overlay tag allow-list, the split overlays, and a source grammar that lets one region come from several datasets (each stamped as its own tippecanoe layer or `designation`). The API gains `GET /api/map/places`, rendered from a new `playbooks/map/places.yaml`. The frontend replaces the Layers panel with a chip row, drops the base choice, maps every feature to a place kind in `describe.ts`, and opens a `PlaceCard` panel on tap.

**Tech Stack:** Python 3 / FastAPI / pytest (`api/.venv`), osmium + ogr2ogr + tippecanoe (build), React 19 + MapLibre + vitest (`web/`), YAML content validated by jsonschema.

**Spec:** `docs/superpowers/specs/2026-09-07-map-places-design.md`

## Global Constraints

- Overlay ids after this plan: `footpaths, access-land, flood-zones, health, fuel, water, rail, nuclear-sites, chemical-sites, airports, military` (in that manifest order; `airports-military` no longer exists anywhere in the repo except in docs that record history).
- `military` colour `#8c564b`, icon `shield`; `airports` keeps colour `#7f7f7f`, icon `airport`.
- Chip short labels, in config order: `Footpaths`, `Access land`, `Flood zones`, `Health`, `Fuel`, `Water`, `Rail`, `Nuclear`, `Chemical`, `Airports`, `Military`, then `Contours`, `Hillshade`.
- Place kinds: `hospital, pharmacy, gp, clinic, fuel, water-works, reservoir, spring, rail-station, airport, military, nuclear, chemical, flood-zone, footpath, access-land`; each `expect` is 40 to 120 words of Markdown with at least one guide link (`page:`, `module:` or `card:`).
- Hover tooltip shows the name and the type line only; the tap opens the card.
- Property values pass through as strings; a tag missing in OSM is simply absent.
- Region ids: `england, wales, scotland, ni, roi, iom, ci`.
- Tests: `api/.venv/bin/python -m pytest api/tests -q` and `pnpm --dir web exec tsc --noEmit` and `pnpm --dir web test` must pass at the end of every task; `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios` must print `OK`.
- Commit after every task; never leave the tree with a failing suite.
- No user setup: the card and chips work with nothing typed in; distance falls back to the map centre when there is no home.

---

## File structure

| File | Responsibility |
|---|---|
| `api/sos/mapbuild/overlays.py` | overlay table with kept tags; regional source grammar; flood layer tags; access designation stamping |
| `tools/map-styles/export/pois.json` | stays as the template; per-overlay export configs are written to the work dir |
| `install/versions.env` | regional source values |
| `manifest/overlays.json`, `manifest/schema.json` | split items; `coverage_note` |
| `api/sos/routers/map.py` | `coverage_note` in `/map/config`; `GET /map/places` |
| `api/sos/map_places.py` (new) | load and validate `playbooks/map/places.yaml` |
| `playbooks/map/places.yaml`, `playbooks/map/schema.json` (new) | what to expect at each kind of place |
| `web/src/map/LayerChips.tsx` (new) | chip row |
| `web/src/map/describe.ts` | kinds, type lines, richer rows, flood layer tags |
| `web/src/map/PlaceCard.tsx` (new) | the card |
| `web/src/map/tooltip.ts` | hover-only popup; tap callback |
| `web/src/screens/Map.tsx` | wiring; no base; card panel |

---

### Task 1: Split airports and military, keep richer tags, update manifest and fixtures

**Files:**
- Modify: `api/sos/mapbuild/overlays.py:17-33` (OsmOverlay, OSM_OVERLAYS, build_osm_overlay)
- Modify: `api/sos/mapbuild/verify.py:130` (docstring only: "access-land/airports/military/water")
- Modify: `manifest/overlays.json` (replace the `airports-military` item with two items)
- Modify: `tools/map-styles/layers/overlays.json` (sources and layers for `airports` and `military`)
- Modify: `playbooks/scenarios/invasion.md`, `playbooks/scenarios/nuclear-war.md`, `playbooks/scenarios/volcanic.md`
- Modify: `api/tests/test_buildmaps_overlays.py`, `api/tests/test_buildmaps_styles.py`, `api/tests/test_buildmaps_fixture_outputs.py`, `api/tests/test_buildmaps_verify.py`, `api/tests/test_manifest_content.py`
- Modify fixtures: `api/tests/fixtures/manifest/overlays.json`, `api/tests/fixtures/maps/build.json`, `api/tests/fixtures/maps/overlays.json`, `api/tests/fixtures/maps/overlays/index.json`; rename `api/tests/fixtures/maps/overlays/airports-military.geojson` to `airports.geojson` and add `military.geojson` (same empty FeatureCollection)

**Interfaces:**
- Produces: `OsmOverlay(id, filters, points, tags)`; `OSM_OVERLAYS` with ids `health, fuel, water, rail, chemical-sites, airports, military`; `export_config_for(ctx, overlay, work) -> Path`.

- [ ] **Step 1: Write the failing build tests**

Replace `test_osm_overlay_table_matches_the_spec` in `api/tests/test_buildmaps_overlays.py` with:

```python
def test_osm_overlay_table_matches_the_spec():
    table = {o.id: (o.filters, o.points) for o in overlays.OSM_OVERLAYS}
    assert set(table) == {"health", "fuel", "water", "rail", "chemical-sites", "airports", "military"}
    assert table["health"] == (("nwr/amenity=hospital,pharmacy,doctors,clinic",), True)
    assert table["fuel"] == (("nwr/amenity=fuel",), True)
    assert table["water"] == (("nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works", "nwr/natural=spring"), False)
    assert table["rail"] == (("nwr/railway=station",), True)
    assert table["chemical-sites"] == (("nwr/industrial=chemical,refinery,oil",), True)
    assert table["airports"] == (("nwr/aeroway=aerodrome",), False)
    assert table["military"] == (("nwr/military=*", "nwr/landuse=military"), False)


def test_osm_overlay_kept_tags_match_the_spec():
    tags = {o.id: o.tags for o in overlays.OSM_OVERLAYS}
    assert tags["health"] == ("name", "amenity", "healthcare", "emergency", "beds", "operator", "phone", "website", "opening_hours", "wheelchair", "dispensing")
    assert tags["fuel"] == ("name", "brand", "operator", "opening_hours", "phone", "fuel:diesel", "fuel:lpg", "fuel:electricity", "shop")
    assert tags["water"] == ("name", "man_made", "natural", "water", "landuse", "operator", "description")
    assert tags["rail"] == ("name", "railway", "station", "operator", "network", "platforms", "wheelchair")
    assert tags["airports"] == ("name", "aeroway", "aerodrome", "aerodrome:type", "icao", "iata", "operator", "surface", "military")
    assert tags["military"] == ("name", "military", "landuse", "operator", "description", "access")
    assert tags["chemical-sites"] == ("name", "industrial", "landuse", "man_made", "operator", "hazmat", "description")


def test_export_config_for_writes_the_overlay_allow_list(tmp_path):
    ctx = make_ctx(tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    fuel = next(o for o in overlays.OSM_OVERLAYS if o.id == "fuel")
    path = overlays.export_config_for(ctx, fuel, work)
    assert path == work / "fuel-export.json"
    cfg = json.loads(path.read_text())
    assert cfg["include_tags"] == list(fuel.tags)
    template = json.loads((ctx.repo / "tools" / "map-styles" / "export" / "pois.json").read_text())
    assert cfg["attributes"] == template["attributes"] and cfg["area_tags"] is True
```

In `test_build_osm_overlay_points_use_point_on_surface_and_polygons_do_not`, change the export assertion to `export[export.index("-c") + 1].endswith("health-export.json")` and the water tags-filter assertion to `tags[-4:] == ["nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works", "nwr/natural=spring"]`. In `test_verify_manifest_kinds_passes_against_the_real_merged_manifest` replace the `airports-military` index line with `"airports": {"kind": "pmtiles", "file": "overlays/airports.pmtiles"}, "military": {"kind": "pmtiles", "file": "overlays/military.pmtiles"},`. In `test_overlays_step_end_to_end_fixture` the expected index key set gains `airports` and `military` and loses `airports-military`.

- [ ] **Step 2: Run them to see them fail**

Run: `api/.venv/bin/python -m pytest api/tests/test_buildmaps_overlays.py -q`
Expected: failures on `tags`, `export_config_for`, the id set.

- [ ] **Step 3: Implement the table and the per-overlay export config**

In `api/sos/mapbuild/overlays.py`:

```python
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


def export_config_for(ctx: Context, overlay: OsmOverlay, work: Path) -> Path:
    """osmium export config for one overlay: the pois.json template with this overlay's own allow-list."""
    template = json.loads((ctx.repo / "tools" / "map-styles" / "export" / "pois.json").read_text())
    template["include_tags"] = list(overlay.tags)
    path = work / f"{overlay.id}-export.json"
    path.write_text(json.dumps(template, indent=2) + "\n")
    return path
```

and in `build_osm_overlay` use `"-c", str(export_config_for(ctx, overlay, work))` instead of `export_config(ctx, "pois")`. Nothing else in the step changes: the loop over `OSM_OVERLAYS` already builds every entry.

Note on `clinic`: the health filter gains `clinic` so the `clinic` place kind has features; the frontend's `HEALTH_TYPES` already names it.

- [ ] **Step 4: Split the manifest item, the style fragment and the scenarios**

In `manifest/overlays.json` replace the `airports-military` item with two items in its place, copying every field of the old item and changing only these:

```json
{ "id": "airports", "title": "Airports and airfields", "priority": 79,
  "source": {"type": "build", "tool": "build-maps", "artifact": "overlays/airports.pmtiles"},
  "dest": "maps/overlays/airports.pmtiles",
  "description": "Every aerodrome in OpenStreetMap, with its type, codes and operator where mapped.",
  "overlay": {"id": "airports", "kind": "pmtiles", "default_on": false, "coverage": ["england","wales","scotland","ni","roi","iom","ci"], "color": "#7f7f7f", "icon": "airport"} }
{ "id": "military", "title": "Military bases and land", "priority": 80,
  "source": {"type": "build", "tool": "build-maps", "artifact": "overlays/military.pmtiles"},
  "dest": "maps/overlays/military.pmtiles",
  "description": "Barracks, airfields, naval bases, ranges and danger areas from OpenStreetMap.",
  "overlay": {"id": "military", "kind": "pmtiles", "default_on": false, "coverage": ["england","wales","scotland","ni","roi","iom","ci"], "color": "#8c564b", "icon": "shield"} }
```

Keep `size_bytes` and `as_at` from the old item on both (Task 8 refreshes them after the build). Do the same in `api/tests/fixtures/manifest/overlays.json` with `geojson` kind, `overlays/airports.geojson` and `overlays/military.geojson` artifacts.

In `tools/map-styles/layers/overlays.json` replace the `airports-military` source with `"airports": {"type": "vector", "url": "pmtiles:///maps/overlays/airports.pmtiles"}` and `"military": {"type": "vector", "url": "pmtiles:///maps/overlays/military.pmtiles"}`, and the two `airports-military-*` layers with four: `airports-fill` (fill `#555555`, opacity 0.35), `airports-label` (as the old label, minzoom 9, filter has name), `military-fill` (fill `#8b0000`, opacity 0.35), `military-label` (text colour `#3a0000`). Source-layer names equal the overlay ids.

Scenarios: `invasion.md` front matter `overlays: [military, airports, rail, footpaths, fuel]` and its link `map:?overlay=military&overlay=airports&overlay=rail&overlay=fuel` with text "Military and airfield overlays"; `nuclear-war.md` `overlays: [nuclear-sites, military, airports, health, water]` and `map:?overlay=nuclear-sites&overlay=military&overlay=airports`; `volcanic.md` `overlays: [health, airports]` and both links `map:?overlay=airports` / `map:?overlay=airports&overlay=health`.

- [ ] **Step 5: Fixtures and the remaining tests**

- `api/tests/fixtures/maps/overlays/index.json`: replace the `airports-military` entry with `"airports": {"kind": "geojson", "file": "overlays/airports.geojson", "features": 0, "size_bytes": 45}` and the same for `military`.
- `git mv api/tests/fixtures/maps/overlays/airports-military.geojson api/tests/fixtures/maps/overlays/airports.geojson` and `cp` it to `military.geojson`.
- `api/tests/fixtures/maps/overlays.json` and `build.json`: replace `airports-military` with `airports` and `military` in every list and the `overlay_sizes` map (45 each).
- `api/tests/test_manifest_content.py`: `OVERLAY_IDS` ends `"nuclear-sites", "chemical-sites", "airports", "military"`; the coverage loop names `airports` and `military`.
- `api/tests/test_buildmaps_fixture_outputs.py:33` tuple gains both ids, loses the old one.
- `api/tests/test_buildmaps_styles.py:109,159`: replace the `airports-military` keys with `airports` (same kinds/files pattern).
- `api/tests/test_buildmaps_verify.py:163` docstring: name the new ids.

- [ ] **Step 6: Run everything**

Run: `api/.venv/bin/python -m pytest api/tests -q` then `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios` then `grep -rn "airports-military" --include=*.py --include=*.json --include=*.md --include=*.yaml . | grep -v node_modules | grep -v docs/`.
Expected: all pass; `OK 119 documents`; grep finds nothing outside `docs/` (the frontend is Task 5).

- [ ] **Step 7: Commit**

```bash
git add -A api/sos/mapbuild api/tests manifest/overlays.json tools/map-styles/layers/overlays.json playbooks/scenarios
git commit -m "build: split airports and military overlays and keep the tags the card needs"
```

---

### Task 2: Regional flood and access sources, layer tags and coverage notes

**Files:**
- Modify: `api/sos/mapbuild/overlays.py:34-81,137-172` (regions, `vector_source`, `region_sources`, `build_flood_zones`, `build_access_land`, index coverage)
- Modify: `install/versions.env:36-44`
- Modify: `manifest/schema.json` (`$defs.overlay.properties.coverage_note`), `manifest/overlays.json` (flood-zones and access-land coverage and notes)
- Modify: `api/sos/routers/map.py:40-44` (`coverage_note` in the overlay dict)
- Test: `api/tests/test_buildmaps_overlays.py`, `api/tests/test_manifest_content.py`, `api/tests/test_map_router.py` (or wherever `/map/config` is tested: `grep -ln "map/config" api/tests/*.py`)

**Interfaces:**
- Produces: source spec grammar `url[|layer][#tag]`, several per value separated by whitespace; flood tippecanoe layers named `flood_<region>` or `flood_<region>_<tag>` with tag in `z2, z3, river, coastal`; access features carry `region` and, from a tagged source, `designation` = tag; index `coverage` lists regions once each; `Overlay.coverage_note: str | null`.

- [ ] **Step 1: Failing tests**

Add to `api/tests/test_buildmaps_overlays.py` (use the existing `make_ctx`/`FakeRunner` helpers and the `POINT_FC` constant; look at `test_build_flood_zones_*` for how `ctx.versions` is set):

```python
def test_source_specs_split_on_whitespace_and_read_layer_and_tag():
    specs = overlays.parse_source_specs("https://a/x.zip|zones#z3  https://b/FeatureServer/2#z2\nhttps://c/d.json")
    assert specs == [("https://a/x.zip", "zones", "z3"), ("https://b/FeatureServer/2", None, "z2"), ("https://c/d.json", None, None)]


def test_flood_zones_layer_per_tagged_source(tmp_path):
    runner = FakeRunner(files={"flood_wales_z3.fgb": b"x", "flood_wales_z2.fgb": b"y", "flood_england.fgb": b"z", "flood-zones.pmtiles": b"p"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    ctx.versions.update({"FLOOD_EN_URL": "https://e/en.gpkg", "FLOOD_WA_URL": "https://w/FeatureServer/1#z3 https://w/FeatureServer/2#z2"})
    work = tmp_path / "work"; work.mkdir()
    staged = tmp_path / "staged"; staged.mkdir()
    _, layers = overlays.build_flood_zones(ctx, work, staged)
    assert layers == ["flood_england", "flood_wales_z3", "flood_wales_z2"]
    tippe = runner.find("tippecanoe")[0]
    assert f"flood_wales_z3:{work / 'flood_wales_z3.fgb'}" in tippe and f"flood_wales_z2:{work / 'flood_wales_z2.fgb'}" in tippe
    assert overlays.flood_coverage(layers) == ["england", "wales"]


def test_flood_zones_rejects_an_unknown_tag(tmp_path):
    ctx = make_ctx(tmp_path, fixture=False)
    ctx.versions.update({"FLOOD_SC_URL": "https://s/FeatureServer/0#medium"})
    with pytest.raises(overlays.BuildError, match="tag 'medium'"):
        overlays.build_flood_zones(ctx, tmp_path, tmp_path)


def test_access_land_stamps_region_and_designation(tmp_path):
    runner = FakeRunner(files={"access_england.geojson": POINT_FC, "access_wales_0.geojson": POINT_FC, "access_wales_1.geojson": POINT_FC})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    ctx.versions.update({"ACCESS_EN_URL": "https://e/FeatureServer/0",
                         "ACCESS_WA_URL": "https://w/open.json#open_country https://w/common.json#common_land"})
    work = tmp_path / "work"; work.mkdir()
    staged = tmp_path / "staged"; staged.mkdir()
    kind, name, regions = overlays.build_access_land(ctx, work, staged)
    assert regions == ["england", "wales"]
    features = json.loads((staged / name).read_text())["features"]
    assert [f["properties"]["region"] for f in features] == ["england", "wales", "wales"]
    assert [f["properties"].get("designation") for f in features] == [None, "open_country", "common_land"]
```

Where the fake runner writes files: check how `FakeRunner(files=...)` matches names (by suffix) so `flood_wales_z3.fgb` and `access_wales_0.geojson` are produced when `ogr2ogr` is "run"; adjust the file keys to the runner's rule.

In `api/tests/test_manifest_content.py::test_overlay_ids_and_objects` change the two coverage lines to `ov["access-land"]["coverage"] == ["england", "wales"]` (unchanged) and `ov["flood-zones"]["coverage"] == ["england", "wales", "scotland", "roi"]`, and add `assert ov["flood-zones"]["coverage_note"] and ov["access-land"]["coverage_note"]`, and inside the loop `assert ov.get("coverage_note") is None or isinstance(ov["coverage_note"], str)`.

In the `/map/config` test add: an overlay whose `overlay_json` carries `"coverage_note": "England and Wales only"` comes back with `coverage_note` equal to it, and one without comes back `None`.

- [ ] **Step 2: Run to see them fail**

Run: `api/.venv/bin/python -m pytest api/tests/test_buildmaps_overlays.py api/tests/test_manifest_content.py -q`
Expected: `parse_source_specs`, `flood_coverage` missing; coverage assertion fails.

- [ ] **Step 3: Implement the grammar and the layers**

```python
FLOOD_TAGS = ("z2", "z3", "river", "coastal")
FLOOD_REGIONS = (("england", "FLOOD_EN_URL"), ("wales", "FLOOD_WA_URL"), ("scotland", "FLOOD_SC_URL"),
                 ("ni", "FLOOD_NI_URL"), ("roi", "FLOOD_IE_URL"))
ACCESS_REGIONS = (("england", "ACCESS_EN_URL"), ("wales", "ACCESS_WA_URL"))


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
    ...  # body unchanged from today, using url and layer


def region_sources(ctx: Context, regions, *, fixture_sample: str) -> list[tuple[str, str | None, VectorSource]]:
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
```

`build_flood_zones`: for each `(region, tag, src)`: if `tag` is not None and not in `FLOOD_TAGS` raise `BuildError(f"FLOOD_*: tag '{tag}' is not one of {', '.join(FLOOD_TAGS)}")`; layer name `flood_{region}` + (`_{tag}` if tag); fgb `work / f"{layer}.fgb"`; `-L f"{layer}:{fgb}"`. Return the layer list. In `OverlaysStep.run` set `"coverage": flood_coverage(layers)`.

`build_access_land`: enumerate sources; geojson path `work / f"access_{region}_{i}.geojson"` when a region has more than one entry (keep `access_{region}.geojson` when it has one, so the fixture test stays as is); stamp `feature["properties"].setdefault("region", region)` and, when `tag`, `setdefault("designation", tag)`; `regions` lists each region once in order.

Update the docstring comment in `install/versions.env` above the values:

```
# Vector sources for ogr2ogr: a URL ending .zip (GPKG, Shapefile or GeoJSON inside), a GeoJSON/GPKG URL, or an
# ArcGIS FeatureServer layer URL (.../FeatureServer/<n>). Append |<layer> to name a layer and #<tag> to label
# the dataset: flood tags z2, z3 (planning zones), river, coastal (extents at 1 in 100 / 1 in 200) become their
# own map layer; access tags become the feature's designation. Several entries in one value, space-separated.
# Blank: region skipped. Northern Ireland's flood extents are not open data (DfI licenses them commercially).
```

and the values (verify each with `curl -s '<url>?f=pjson' | head -c 400` for FeatureServer layers, `curl -sI <zip>` for zips, and `ogrinfo -so -q '/vsizip//vsicurl/<zip>'` for the shapefile zips; if a zip holds more than one layer, name the flood-extent layer with `|<layer>`; if SEPA's service has a layer other than 0, use it):

```
FLOOD_WA_URL="https://services-eu1.arcgis.com/KB6uNVj5ZcJr7jUP/arcgis/rest/services/Flood_Map_for_Planning/FeatureServer/1#z3 https://services-eu1.arcgis.com/KB6uNVj5ZcJr7jUP/arcgis/rest/services/Flood_Map_for_Planning/FeatureServer/2#z2"
FLOOD_SC_URL="https://map.sepa.org.uk/server/rest/services/Open/River_Flooding_Medium_Likelihood/FeatureServer/0#river https://map.sepa.org.uk/server/rest/services/Open/Coastal_Flooding_Medium_Likelihood/FeatureServer/0#coastal"
FLOOD_NI_URL=
FLOOD_IE_URL="https://s3.eu-west-1.amazonaws.com/catalogue.floodinfo.opw/cfram/esds_floodmap_ext_f_c.zip#river https://s3.eu-west-1.amazonaws.com/catalogue.floodinfo.opw/cfram/esds_floodmap_ext_c_c.zip#coastal"
ACCESS_WA_URL="https://datamap.gov.wales/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire-nrw:NRW_OPEN_COUNTRY_2014&outputFormat=application/json#open_country https://datamap.gov.wales/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire-nrw:NRW_COMMON_LAND_2014&outputFormat=application/json#common_land"
```

Licences, for the manifest: Wales and Scotland OGL v3; Ireland CC BY-NC-ND 4.0 (OPW). Set the flood-zones item's `licence` to `"OGL v3 (Environment Agency, Natural Resources Wales, SEPA); CC BY-NC-ND 4.0 (OPW, Ireland)"` and access-land's to `"OGL v3 (Natural England, Natural Resources Wales)"`.

- [ ] **Step 4: Schema, manifest notes, API**

`manifest/schema.json` `$defs.overlay.properties` gains `"coverage_note": {"type": ["string", "null"]}`.

`manifest/overlays.json`:
- flood-zones `overlay.coverage`: `["england", "wales", "scotland", "roi"]`; `coverage_note`: `"No flood map for Northern Ireland (its flood maps are not open data), the Isle of Man or the Channel Islands."`
- access-land `coverage_note`: `"England and Wales only. Scotland has a right of responsible access to almost all land; Northern Ireland, Ireland, the Isle of Man and the Channel Islands have no open-access designation."`

`api/sos/routers/map.py` `overlays_list`: add `"coverage_note": o.get("coverage_note")` to the dict.

- [ ] **Step 5: Run and commit**

Run: `api/.venv/bin/python -m pytest api/tests -q`
Expected: pass.

```bash
git add api/sos/mapbuild/overlays.py api/sos/routers/map.py api/tests install/versions.env manifest
git commit -m "build: flood and access sources for Wales, Scotland and Ireland, with coverage notes"
```

---

### Task 3: Place guidance content and `GET /api/map/places`

**Files:**
- Create: `playbooks/map/schema.json`, `playbooks/map/places.yaml`
- Create: `api/sos/map_places.py`
- Modify: `api/sos/content.py:514-517` (call `map_places.validate_places` after the kits), `api/sos/routers/map.py` (endpoint), `playbooks/README.md` (a "Map places" section after "Kits")
- Test: `api/tests/test_map_places.py` (new)

**Interfaces:**
- Produces: `map_places.load_places(path) -> dict[str, PlaceKind]` with `PlaceKind(kind, title, expect, link)`; `map_places.validate_places(playbooks_dir, zim_ids, doc_ids, slugs, overlay_ids, items_by_id=None, kiwix_check=None, doc_check=None) -> list[str]`; `GET /api/map/places` → `{ "<kind>": {"title": str, "html": str, "link": {"href": str, "title": str}} }`.

- [ ] **Step 1: Failing tests**

```python
# api/tests/test_map_places.py
import json
from pathlib import Path

import pytest
import yaml

from sos import map_places
from sos.content import validate_tree
from sos.manifest import load_manifests

REPO = Path(__file__).resolve().parents[2]
PB = REPO / "playbooks"
KINDS = ["hospital", "pharmacy", "gp", "clinic", "fuel", "water-works", "reservoir", "spring", "rail-station",
         "airport", "military", "nuclear", "chemical", "flood-zone", "footpath", "access-land"]


def test_places_yaml_has_every_kind_with_guidance_and_a_link():
    places = map_places.load_places(PB / "map" / "places.yaml")
    assert sorted(places) == sorted(KINDS)
    for kind, place in places.items():
        words = len(place.expect.split())
        assert 40 <= words <= 120, (kind, words)
        assert "](page:" in place.expect or "](module:" in place.expect or "](card:" in place.expect, kind
        assert place.link.split(":")[0] in {"page", "module", "card"}, kind
        assert place.title


def test_places_validate_clean_against_the_real_tree():
    items = load_manifests(REPO / "manifest")
    overlay_ids = {i.overlay.id for i in items if i.overlay}
    assert validate_tree(PB, items, overlay_ids) == []


def test_places_validation_reports_a_bad_link_and_a_missing_kind(tmp_path):
    src = yaml.safe_load((PB / "map" / "places.yaml").read_text())
    src["places"]["fuel"]["link"] = "page:no-such-page"
    del src["places"]["spring"]
    folder = tmp_path / "map"
    folder.mkdir()
    (folder / "places.yaml").write_text(yaml.safe_dump(src))
    (folder / "schema.json").write_text((PB / "map" / "schema.json").read_text())
    slugs = {"page": {"fuel-and-power"}, "module": set(), "card": set(), "scenario": set()}
    errors = map_places.validate_places(tmp_path, set(), set(), slugs, set())
    assert any("no-such-page" in e for e in errors)
    assert any("spring" in e and "missing" in e for e in errors)


def test_places_endpoint_renders_html(client):
    body = client.get("/api/map/places").json()
    assert sorted(body) == sorted(KINDS)
    fuel = body["fuel"]
    assert fuel["title"] and fuel["html"].startswith("<p>") and 'href="/' in fuel["html"]
    assert fuel["link"]["href"].startswith("/") and fuel["link"]["title"]
```

Use whatever fixture the other router tests use for `client` (see `api/tests/conftest.py`).

- [ ] **Step 2: Run to see them fail**

Run: `api/.venv/bin/python -m pytest api/tests/test_map_places.py -q`
Expected: `ModuleNotFoundError: sos.map_places`.

- [ ] **Step 3: Schema and content**

`playbooks/map/schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Operation SOS map places",
  "description": "playbooks/map/places.yaml: what to expect at each kind of place on the map. Rules in playbooks/README.md.",
  "type": "object",
  "required": ["places"],
  "additionalProperties": false,
  "properties": {
    "places": {
      "type": "object",
      "propertyNames": {"pattern": "^[a-z][a-z-]*$"},
      "additionalProperties": {
        "type": "object",
        "required": ["title", "expect", "link"],
        "additionalProperties": false,
        "properties": {
          "title": {"type": "string", "minLength": 3, "maxLength": 60},
          "expect": {"type": "string", "minLength": 200},
          "link": {"type": "string", "pattern": "^(page|module|card):[a-z0-9-]+$"}
        }
      }
    }
  }
}
```

`playbooks/map/places.yaml`: `places:` with the sixteen kinds. Before writing, list the guides you may link: `ls playbooks/pages playbooks/modules playbooks/cards` and read the ones you cite (fuel and power, water, shelter, evacuation, nuclear, chemical, flooding, navigation, medical). Each `expect` is one Markdown paragraph, 40 to 120 words, plain UK English, present tense, second person, no bullet lists, ending with one guide link; `link` is the guide to open from the card's button. The substance per kind, from the spec:

- hospital: A&E stays open on generators for days but non-urgent care stops; go only for a life-threatening problem; take medicines and a list of them; phone lines may be down.
- pharmacy: closes without power or staff; may dispense an emergency supply of a regular medicine; cash.
- gp: shut in most emergencies; NHS 111 or the medical cards instead.
- clinic: walk-in and urgent treatment centres take injuries that are not life-threatening; check opening hours before walking.
- fuel: pumps need mains power, most close in a blackout; cash may be the only payment; the 30 litre rule and queue behaviour.
- water-works: not a place to fetch water; treated water in an outage comes from bowsers and bottled-water stations the company announces.
- reservoir: raw water is not safe to drink untreated; filter and boil or disinfect; steep banks and cold water.
- spring: the best raw source there is, still treat it; upstream of any farm or road.
- rail-station: a landmark and a roof, not a service; trains stop early in most emergencies.
- airport: closes to the public in a crisis; a target in war; an evacuation hub only under official instruction.
- military: not a refuge; armed guards turn people away; in an invasion or nuclear scenario a target to move away from.
- nuclear: the REPPIR emergency planning zone; go in, stay in, tune in; stable iodine only when told.
- chemical: the plume rule: indoors, windows shut, or move crosswind and upwind; do not drive into a cloud.
- flood-zone: what zone 2 and 3 mean for staying or leaving; six inches of moving water, a car in two feet.
- footpath: the access law in one line; a way out when roads are blocked; wet ground and dark.
- access-land: open country you may cross on foot; no camping right in England and Wales; the Scottish code.

Cite a figure only where a guide already carries it, and take the figure from that guide.

- [ ] **Step 4: Loader and validator**

```python
# api/sos/map_places.py
"""Map places: what to expect at each kind of place on the map (map places spec, 2026-09-07).

One YAML file, playbooks/map/places.yaml, loaded here, validated for `sos validate-playbooks` and served by
GET /api/map/places as HTML the frontend never has to parse."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import jsonschema
import yaml

KINDS = ("hospital", "pharmacy", "gp", "clinic", "fuel", "water-works", "reservoir", "spring", "rail-station",
         "airport", "military", "nuclear", "chemical", "flood-zone", "footpath", "access-land")


@dataclass(frozen=True)
class PlaceKind:
    kind: str
    title: str
    expect: str
    link: str


def load_places(path: Path | str) -> dict[str, PlaceKind]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {k: PlaceKind(k, str(v.get("title", "")), str(v.get("expect", "")), str(v.get("link", "")))
            for k, v in (raw.get("places") or {}).items() if isinstance(v, dict)}


def validate_places(playbooks_dir, zim_ids, doc_ids, slugs, overlay_ids, items_by_id=None, kiwix_check=None, doc_check=None) -> list[str]:
    from sos import content  # deferred: content imports this module
    folder = Path(playbooks_dir) / "map"
    path = folder / "places.yaml"
    if not path.exists():
        return []
    rel = "map/places.yaml"
    schema_path = folder / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{rel}: cannot parse: {exc}".splitlines()[0]]
    validator = jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    errors = [f"{rel}: {'/'.join(str(p) for p in e.path) or 'file'}: {e.message}" for e in validator.iter_errors(raw)]
    places = load_places(path)
    errors += [f"{rel}: places: '{k}' is missing" for k in KINDS if k not in places]
    for kind, place in places.items():
        errors += [e.replace(rel, f"{rel}: {kind}", 1) for e in content._check_links(rel, place.expect, zim_ids, doc_ids, slugs, overlay_ids)]
        errors += [e.replace(rel, f"{rel}: {kind}", 1) for e in content._check_links(rel, f"[x]({place.link})", zim_ids, doc_ids, slugs, overlay_ids)]
    return errors
```

(`import json` at the top.) Read `content._check_links` first and match its real signature. In `content.validate_tree`, after the kits call add:

```python
    from sos import map_places
    errors += map_places.validate_places(playbooks_dir, zim_ids, doc_ids, slugs, overlay_ids, items_by_id,
                                         kiwix_check=kiwix_check, doc_check=doc_check)
```

- [ ] **Step 5: Endpoint**

In `api/sos/routers/map.py`:

```python
from fastapi import Request
from sos import content as content_mod, map_places


@router.get("/map/places")
def map_places_guidance(request: Request):
    settings = request.app.state.settings
    resolver = request.app.state.content.resolver
    out = {}
    for kind, place in map_places.load_places(settings.playbooks / "map" / "places.yaml").items():
        html = content_mod.render_markdown(place.expect, resolver)
        out[kind] = {"title": place.title, "html": html, "link": {"href": resolver(place.link), "title": _link_title(request, place.link)}}
    return out
```

`_link_title` looks the target up in `request.app.state.content` (`list("page")`/`list("module")`/`list("card")` by slug) and returns its title, falling back to the slug humanised. Check `settings.playbooks` is the attribute name in `sos/config.py`.

- [ ] **Step 6: README and run**

`playbooks/README.md`: after "## Kits" add "## Map places" — where the file lives, the sixteen kinds, the word range, the link rule, the schema.

Run: `api/.venv/bin/python -m pytest api/tests -q` and the validator.
Expected: pass, `OK`.

```bash
git add playbooks/map playbooks/README.md api/sos/map_places.py api/sos/content.py api/sos/routers/map.py api/tests/test_map_places.py
git commit -m "content: what to expect at each kind of place, served as /api/map/places"
```

---

### Task 4: Chips in view, one base, two terrain chips

**Files:**
- Create: `web/src/map/LayerChips.tsx`
- Delete: `web/src/map/LayerPanel.tsx`
- Modify: `web/src/screens/Map.tsx` (remove `BASE_KEY`, `baseId`, its effect and the Layers button and panel; render `LayerChips`; `terrain` state), `web/src/map/MapView.tsx` (no `baseId`; `terrain: {contours, hillshade}`), `web/src/map/layers.ts` (`setTerrainLayerVisible`), `web/src/map/overlays.ts` (`coverageNote` honours `coverage_note`), `web/src/api/types.ts` (`coverage_note`), `web/src/icons.tsx` (`plane`, `train`), `web/src/screens/map.css`
- Test: `web/tests/screens/map.test.tsx`, `web/tests/map/overlays.test.ts`, `web/tests/map/layers.test.ts`, `web/tests/fixtures/api.ts`, `web/e2e/map.spec.ts`

**Interfaces:**
- Produces: `LayerChips({ config, overlaysOn, onToggle, terrain, onTerrain })`; `CHIP_LABELS: Record<string,string>`; `chipIcon(id): IconName`; `MapViewProps.terrain: { contours: boolean; hillshade: boolean }`; `setTerrainLayerVisible(map, id: 'sos-contours' | 'sos-hillshade', on)`.

- [ ] **Step 1: Failing tests**

Replace the two tests "toggles overlays from the layer panel…" and "switching base keeps overlays…" in `web/tests/screens/map.test.tsx` with:

```tsx
  it('shows one chip per overlay, in order, and toggles the layer and the URL', async () => {
    mockApis();
    const user = userEvent.setup();
    const { router } = renderRoute('/map');
    const chips = await screen.findByRole('group', { name: 'Map layers' });
    const names = within(chips).getAllByRole('button').map((b) => b.textContent);
    expect(names).toEqual(['Health', 'Footpaths', 'Access land', 'Flood zones', 'Contour labels', 'Contours', 'Hillshade']);
    const health = within(chips).getByRole('button', { name: 'Health' });
    expect(health).toHaveAttribute('aria-pressed', 'false');
    await user.click(health);
    expect(health).toHaveAttribute('aria-pressed', 'true');
    expect(lastMap().visibility('sos-overlay-health-point')).toBe('visible');
    expect(router.state.location.search).toContain('overlay=footpaths&overlay=health');
    expect(within(chips).getByRole('button', { name: 'Footpaths' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(chips).getByRole('button', { name: 'Flood zones' })).toBeDisabled();
    expect(within(chips).getByRole('button', { name: 'Access land' })).toHaveAttribute('title', 'No data for Scotland, Northern Ireland, Republic of Ireland, Isle of Man, Channel Islands');
    await user.click(within(chips).getByRole('button', { name: 'Hillshade' }));
    expect(lastMap().visibility('sos-hillshade')).toBe('none');
    expect(lastMap().visibility('sos-contours')).toBe('visible');
    expect(screen.queryByRole('button', { name: /Layers/ })).toBeNull();
    expect(screen.queryByRole('radio')).toBeNull();
  });

  it('always loads the OpenStreetMap style, whatever was stored before', async () => {
    mockApis();
    localStorage.setItem('sos.mapBase', 'os');
    renderRoute('/map');
    await screen.findByRole('group', { name: 'Map layers' });
    await act(async () => {});
    expect(lastMap().style.name).toBe('/maps/styles/osm-field.json');
  });
```

Every other test in that file that waits on `screen.findByRole('button', { name: /Layers/ })` now waits on `screen.findByRole('group', { name: 'Map layers' })`. The "hovering an overlay feature shows a tooltip that survives a base switch" test becomes "…survives a theme switch": drive the theme through `useTheme`'s provider the way `web/tests/screens/settings.test.tsx` (or the theme tests) does, assert `map.setStyle` was called with `/maps/styles/osm-mono.json` and the tooltip still opens.

In `web/tests/map/overlays.test.ts` add: `expect(coverageNote({ ...accessLand, coverage_note: 'England and Wales only.' })).toBe('England and Wales only.')`. In `web/tests/fixtures/api.ts` add `coverage_note: null` to every overlay (the type makes it required).

In `web/tests/map/layers.test.ts` add a test that `setTerrainLayerVisible(map, 'sos-hillshade', false)` hides only that layer.

`web/e2e/map.spec.ts` first test: drop the base switch; click `page.getByRole('group', { name: 'Map layers' }).getByRole('button', { name: 'Health' })`, expect the URL and layer, click again, expect hidden.

- [ ] **Step 2: Run to see them fail**

Run: `pnpm --dir web test -- tests/screens/map.test.tsx tests/map/overlays.test.ts tests/map/layers.test.ts`
Expected: no group named "Map layers"; `coverage_note` type error.

- [ ] **Step 3: Chips**

```tsx
// web/src/map/LayerChips.tsx
import type { MapConfig } from '../api/types';
import { Icon, type IconName } from '../icons';
import { coverageNote } from './overlays';

/** The short word on a chip; the manifest titles stay long for search and the card. */
export const CHIP_LABELS: Record<string, string> = {
  footpaths: 'Footpaths', 'access-land': 'Access land', 'flood-zones': 'Flood zones', health: 'Health', fuel: 'Fuel',
  water: 'Water', rail: 'Rail', 'nuclear-sites': 'Nuclear', 'chemical-sites': 'Chemical', airports: 'Airports', military: 'Military',
};
const CHIP_ICONS: Record<string, IconName> = {
  footpaths: 'boot', 'access-land': 'leaf', 'flood-zones': 'waves', health: 'medical', fuel: 'bolt', water: 'drop', rail: 'train',
  'nuclear-sites': 'radiation', 'chemical-sites': 'flask', airports: 'plane', military: 'shield',
};
export function chipIcon(id: string): IconName {
  return CHIP_ICONS[id] ?? 'layers';
}

export type Terrain = { contours: boolean; hillshade: boolean };

/** Every layer, always on screen: one chip per overlay in config order, then the two terrain chips.
 * A chip that cannot be turned on (not built for this box) is disabled and says why in its title. */
export function LayerChips({ config, overlaysOn, onToggle, terrain, onTerrain }: {
  config: MapConfig; overlaysOn: string[]; onToggle: (id: string, on: boolean) => void;
  terrain: Terrain; onTerrain: (t: Terrain) => void;
}) {
  return (
    <div className="map-chips no-print" role="group" aria-label="Map layers">
      {config.overlays.map((o) => {
        const on = overlaysOn.includes(o.id);
        const note = o.available ? coverageNote(o) : 'Not installed on this box';
        return (
          <button key={o.id} type="button" className={on ? 'map-chip active' : 'map-chip'} aria-pressed={on} disabled={!o.available}
            title={note ?? undefined} onClick={() => onToggle(o.id, !on)}>
            <Icon name={chipIcon(o.id)} size={16} />
            <span className="map-chip-dot" style={{ background: o.color }} aria-hidden="true" />
            <span>{CHIP_LABELS[o.id] ?? o.title}</span>
          </button>
        );
      })}
      {config.terrain.contours && (
        <button type="button" className={terrain.contours ? 'map-chip active' : 'map-chip'} aria-pressed={terrain.contours}
          onClick={() => onTerrain({ ...terrain, contours: !terrain.contours })}><Icon name="mountain" size={16} /><span>Contours</span></button>
      )}
      {config.terrain.hillshade && (
        <button type="button" className={terrain.hillshade ? 'map-chip active' : 'map-chip'} aria-pressed={terrain.hillshade}
          onClick={() => onTerrain({ ...terrain, hillshade: !terrain.hillshade })}><Icon name="sun" size={16} /><span>Hillshade</span></button>
      )}
    </div>
  );
}
```

Icons: add to `web/src/icons.tsx` a `plane` (a simple aircraft silhouette path) and a `train` (a carriage outline with two wheels) in the file's existing style, and add both to `IconName` if the type is a union of keys.

CSS (`map.css`, under the toolbar rules):

```css
/* Every layer in view: a chip row under the tools, scrolling sideways on a phone with the same edge
   fade the tools strip has. A pressed chip is filled; a chip the box cannot turn on is dimmed. */
.map-chips { display: flex; gap: 6px; padding: 0 var(--gutter) 6px; overflow-x: auto; scrollbar-width: thin; flex: 0 0 auto;
  mask-image: linear-gradient(to right, #000 calc(100% - 24px), transparent); }
.map-chip { flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 4px 10px;
  border: 1px solid var(--line-strong); border-radius: var(--radius-pill); background: var(--panel); color: var(--ink); font: inherit; }
.map-chip.active { background: var(--ink); color: var(--ground); }
.map-chip:disabled { opacity: 0.45; }
.map-chip-dot { width: 10px; height: 10px; border-radius: 50%; border: 1px solid var(--line-strong); }
.map-chip.active .map-chip-dot { border-color: var(--ground); }
```

Check the token names (`--panel`, `--ink`, `--ground`, `--line-strong`, `--radius-pill`) exist in `web/src/theme/*.css`; use the ones that do.

- [ ] **Step 4: One base and the terrain pair**

`Map.tsx`: delete `BASE_KEY`, `baseId`, `setBaseId`, the `localStorage` effect, `'layers'` from `Panel`, the Layers button, the `LayerPanel` import and render, and the `legend` stays (print). Replace `const [terrainOn, setTerrainOn] = useState(true)` with `const [terrain, setTerrain] = useState<Terrain>({ contours: true, hillshade: true })`. Render `<LayerChips config={config} overlaysOn={overlaysOn} onToggle={(id, on) => setOverlayOverride(on ? [...overlaysOn, id] : overlaysOn.filter((x) => x !== id))} terrain={terrain} onTerrain={setTerrain} />` between the toolbar and `.map-host`, only when `config && overlaysOn`.

`MapView.tsx`: drop `baseId` from the props; `styleUrl` = `config.bases.find((b) => b.id === 'osm' && b.available) ?? config.bases.find((b) => b.available)` then `?.styles[theme]`; replace `terrainOn` with `terrain` and wherever `setTerrainVisible(map, terrainOn)` ran, run `setTerrainLayerVisible(map, 'sos-contours', terrain.contours); setTerrainLayerVisible(map, 'sos-hillshade', terrain.hillshade)`; keep `setTerrainVisible` exported for anything else that uses it (grep first; delete it if nothing does).

`layers.ts`:

```ts
export function setTerrainLayerVisible(map: MlMap, id: 'sos-contours' | 'sos-hillshade', on: boolean): void {
  if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
}
```

`overlays.ts`:

```ts
export function coverageNote(overlay: Overlay): string | null {
  if (overlay.coverage_note) return overlay.coverage_note;
  const missing = Object.keys(REGIONS).filter((r) => !overlay.coverage.includes(r));
  return missing.length ? `No data for ${missing.map((r) => REGIONS[r]).join(', ')}` : null;
}
```

`types.ts` `Overlay` gains `coverage_note: string | null`.

- [ ] **Step 5: Run and commit**

Run: `pnpm --dir web exec tsc --noEmit && pnpm --dir web test`
Expected: pass (the two known flaky files may need a rerun on their own).

```bash
git add -A web/src web/tests web/e2e
git commit -m "map: layers as chips in view, one base map, contours and hillshade apart"
```

---

### Task 5: Describe every feature as a kind with a type line and richer rows

**Files:**
- Modify: `web/src/map/describe.ts`
- Test: `web/tests/map/describe.test.ts`

**Interfaces:**
- Produces: `FeatureDescription = { title: string; overlay: string; typeLine: string; kind: PlaceKind | null; rows: [string, string][] }`; `export type PlaceKind = 'hospital' | 'pharmacy' | 'gp' | 'clinic' | 'fuel' | 'water-works' | 'reservoir' | 'spring' | 'rail-station' | 'airport' | 'military' | 'nuclear' | 'chemical' | 'flood-zone' | 'footpath' | 'access-land'`; `OVERLAY_TITLES` with `airports` and `military`.

- [ ] **Step 1: Failing tests**

In `web/tests/map/describe.test.ts`: `MANIFEST_IDS` becomes the eleven ids. Replace the `airports-military` block with:

```ts
  it('airports: type line from the aerodrome type, codes and operator as rows, kind airport', () => {
    const d = describeFeature('airports', { name: 'Southampton Airport', aeroway: 'aerodrome', 'aerodrome:type': 'international', iata: 'SOU', icao: 'EGHI', operator: 'AGS Airports' });
    expect(d.title).toBe('Southampton Airport');
    expect(d.typeLine).toBe('International airport');
    expect(d.kind).toBe('airport');
    expect(d.rows).toEqual([['Type', 'International airport'], ['Code', 'SOU / EGHI'], ['Run by', 'AGS Airports']]);
    expect(describeFeature('airports', { aeroway: 'aerodrome', military: 'airfield', name: 'RAF Brize Norton' }).typeLine).toBe('Military airfield');
    expect(describeFeature('airports', { aeroway: 'aerodrome' }).title).toBe('Airport or airfield');
  });

  it('military: barracks, naval bases and danger areas, kind military', () => {
    expect(describeFeature('military', { military: 'barracks', name: 'Marchwood', operator: 'British Army', access: 'no' })).toMatchObject({
      title: 'Marchwood', typeLine: 'Barracks', kind: 'military', rows: [['Type', 'Barracks'], ['Run by', 'British Army'], ['Access', 'No public access']],
    });
    expect(describeFeature('military', { military: 'naval_base' }).typeLine).toBe('Naval base');
    expect(describeFeature('military', { military: 'danger_area' }).typeLine).toBe('Military danger area');
    expect(describeFeature('military', { landuse: 'military' }).typeLine).toBe('Military land');
    expect(describeFeature('military', { military: 'radar_station' }).typeLine).toBe('Military land (radar station)');
  });

  it('health: A&E, beds, dispensing, wheelchair and website; kinds per amenity', () => {
    const d = describeFeature('health', { name: 'Southampton General Hospital', amenity: 'hospital', emergency: 'yes', beds: '1200', wheelchair: 'yes', website: 'https://uhs.nhs.uk', operator: 'UHS NHS FT' });
    expect(d.typeLine).toBe('Hospital · emergency department');
    expect(d.kind).toBe('hospital');
    expect(d.rows).toEqual([['Type', 'Hospital'], ['Emergency department', 'Yes'], ['Run by', 'UHS NHS FT'], ['Beds', '1200'], ['Wheelchair access', 'Yes'], ['Website', 'https://uhs.nhs.uk']]);
    expect(describeFeature('health', { amenity: 'pharmacy', dispensing: 'yes' })).toMatchObject({ kind: 'pharmacy', rows: [['Type', 'Pharmacy'], ['Dispenses prescriptions', 'Yes']] });
    expect(describeFeature('health', { amenity: 'doctors' }).kind).toBe('gp');
    expect(describeFeature('health', { amenity: 'clinic' }).kind).toBe('clinic');
    expect(describeFeature('health', { healthcare: 'hospital', emergency: 'yes' }).kind).toBe('hospital');
  });

  it('fuel: brand in the type line, what it sells and whether it has a shop', () => {
    const d = describeFeature('fuel', { name: 'Tesco Bursledon', brand: 'Tesco', 'fuel:diesel': 'yes', 'fuel:lpg': 'no', 'fuel:electricity': 'yes', shop: 'convenience', opening_hours: '24/7' });
    expect(d.typeLine).toBe('Fuel station · Tesco');
    expect(d.kind).toBe('fuel');
    expect(d.rows).toEqual([['Type', 'Fuel station'], ['Brand', 'Tesco'], ['Diesel', 'Yes'], ['LPG', 'No'], ['Electric charging', 'Yes'], ['Shop', 'Convenience'], ['Opening hours', 'Open 24 hours a day, every day']]);
  });

  it('water: works, reservoirs and springs are three kinds', () => {
    expect(describeFeature('water', { man_made: 'water_works', operator: 'Southern Water' })).toMatchObject({ kind: 'water-works', typeLine: 'Water treatment works', rows: [['Type', 'Water treatment works'], ['Run by', 'Southern Water']] });
    expect(describeFeature('water', { water: 'reservoir', name: 'Bewl Water' })).toMatchObject({ kind: 'reservoir', typeLine: 'Reservoir' });
    expect(describeFeature('water', { natural: 'spring', description: 'Chalk spring' })).toMatchObject({ kind: 'spring', typeLine: 'Spring', rows: [['Type', 'Spring'], ['Note', 'Chalk spring']] });
  });

  it('rail: operator in the type line, platforms and step-free access', () => {
    const d = describeFeature('rail', { name: 'Eastleigh', railway: 'station', operator: 'South Western Railway', network: 'National Rail', platforms: '4', wheelchair: 'limited' });
    expect(d.typeLine).toBe('Railway station · South Western Railway');
    expect(d.kind).toBe('rail-station');
    expect(d.rows).toEqual([['Type', 'Railway station'], ['Network', 'National Rail'], ['Train operator', 'South Western Railway'], ['Platforms', '4'], ['Wheelchair access', 'Limited']]);
  });

  it('flood layers carry the region and the zone or the extent kind in their name', () => {
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_wales_z3' })).toMatchObject({ title: 'Flood zone 3', kind: 'flood-zone', rows: expect.arrayContaining([['Flood zone', '3'], ['Region', 'Wales']]) });
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_scotland_river' })).toMatchObject({ title: 'River flood risk area', rows: expect.arrayContaining([['Chance of flooding', 'Medium: a 1 in 200 or greater chance of river flooding in any year (SEPA)'], ['Region', 'Scotland']]) });
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_roi_coastal' })).toMatchObject({ title: 'Coastal flood risk area', rows: expect.arrayContaining([['Chance of flooding', 'A 1 in 200 or greater chance of sea flooding in any year (OPW)'], ['Region', 'Republic of Ireland']]) });
    expect(describeFeature('flood-zones', { layer: 'Flood Zone 2' }, { sourceLayer: 'flood_england' }).title).toBe('Flood zone 2');
  });

  it('access land from a tagged Welsh source reads its designation', () => {
    expect(describeFeature('access-land', { region: 'wales', designation: 'open_country' })).toMatchObject({ kind: 'access-land', rows: expect.arrayContaining([['Designation', 'Open country (CROW Act)'], ['Region', 'Wales']]) });
    expect(describeFeature('access-land', { region: 'wales', designation: 'common_land' }).rows[0]).toEqual(['Designation', 'Registered common land']);
  });

  it('every overlay maps to a kind; an unknown overlay has none', () => {
    expect(describeFeature('nuclear-sites', { type: 'power-station', status: 'operating' })).toMatchObject({ kind: 'nuclear', typeLine: 'Nuclear power station · Operating' });
    expect(describeFeature('chemical-sites', { industrial: 'refinery' }).kind).toBe('chemical');
    expect(describeFeature('footpaths', { designation: 'public_footpath' })).toMatchObject({ kind: 'footpath', typeLine: 'Public footpath' });
    expect(describeFeature('whatever', {}).kind).toBeNull();
  });
```

Keep the older health/fuel/rail/footpath/access/flood assertions that still hold; delete the ones that asserted rows this task changes (address rows stay when `addr:*` is present, but the build no longer keeps them, so no test should depend on them).

- [ ] **Step 2: Run to see them fail**

Run: `pnpm --dir web test -- tests/map/describe.test.ts`

- [ ] **Step 3: Implement**

In `describe.ts`:
- `OVERLAY_TITLES`: remove `airports-military`; add `airports: 'Airports and airfields'`, `military: 'Military bases and land'`.
- Add `PlaceKind` and extend `FeatureDescription` with `typeLine` and `kind`. Every `describe*` returns `{ title, typeLine, kind, rows }`.
- `describeHealth`: type from `amenity` then `healthcare`; `emergency=yes` → `typeLine = `${type} · emergency department``, kind `hospital` when amenity is hospital or emergency is yes, `pharmacy`, `gp` for `doctors`, `clinic` for clinic; rows in order: Type, Emergency department, Run by, Phone, Opening hours (from `commonRows`, which loses its address and capacity rows), Beds, Dispenses prescriptions, Wheelchair access, Website. Keep the order the test states: `['Type'], ['Emergency department'], ...commonRows, ['Beds'], ['Wheelchair access'], ['Website']` with `Dispenses prescriptions` right after Type for a pharmacy — so: Type, Emergency department, Dispenses prescriptions, then commonRows (Run by, Phone, Opening hours), then Beds, Wheelchair access, Website.
- `commonRows`: Run by (`operator`), Phone, Opening hours only.
- `describeFuel`: Type, Brand, Diesel, LPG, Electric charging (each only when the tag exists, `yesNo`), Shop (humanised), then commonRows minus operator when it equals the brand; `typeLine` = `Fuel station · <brand>` when there is a brand.
- `describeWater`: kinds `water-works` (`man_made=water_works`), `reservoir` (`water=reservoir` or `landuse=reservoir`), `spring` (`natural=spring`); `description` → `['Note', …]`.
- `describeRail`: `typeLine` = `<type> · <operator>` when there is an operator; rows Type, Network, Train operator, Platforms, Wheelchair access, then Phone/Opening hours if present.
- `describeAirport` (overlay `airports`) and `describeMilitary` (overlay `military`): split the old function; `access` → `['Access', ACCESS_VALUES[...]]`; `description` → Note; a military feature with only `landuse=military` reads "Military land".
- `describeNuclear`: `typeLine` = `<type> · <status>`; kind `nuclear`. `describeChemical`: kind `chemical`; `hazmat` → `['Hazardous materials', yesNo]`, `description` → Note.
- Footpath kind `footpath`, typeLine = the type; access land kind `access-land`; `accessDesignation` lowercases and replaces `_` with a space before matching.
- Flood: parse `sourceLayer` as `flood_<region>[_<tag>]`; tag `z2`/`z3` fixes the zone; `river` → title "River flood risk area" and chance "Medium: a 1 in 200 or greater chance of river flooding in any year (SEPA)" for scotland or "A 1 in 100 or greater chance of river flooding in any year (OPW)" for roi; `coastal` → "Coastal flood risk area" and "A 1 in 200 or greater chance of sea flooding in any year (SEPA)" / "(OPW)"; no tag → today's behaviour from the properties. `regionName` takes the first segment after the prefix. Kind `flood-zone`.
- `describeFeature` default branch: `kind: null`, `typeLine: overlay`.

- [ ] **Step 4: Run, then check the tooltip test file still passes**

Run: `pnpm --dir web exec tsc --noEmit && pnpm --dir web test -- tests/map`
Expected: pass (tooltip tests construct `FeatureDescription` literals: add `typeLine` and `kind` to them).

```bash
git add web/src/map/describe.ts web/tests/map
git commit -m "map: every feature is a kind with a type line and the rows the card shows"
```

---

### Task 6: The place card

**Files:**
- Create: `web/src/map/PlaceCard.tsx`
- Modify: `web/src/map/tooltip.ts` (hover shows title and type line only; `onTap` callback), `web/src/map/MapView.tsx` (`onFeatureTap` prop), `web/src/screens/Map.tsx` (panel `'place'`, card state, actions, Nearby rows open the card, "Nearby from here"), `web/src/api/client.ts` and `web/src/api/types.ts` (`mapPlaces`), `web/src/screens/map.css`
- Test: `web/tests/map/tooltip.test.ts`, `web/tests/screens/map.test.tsx`, `web/tests/fixtures/api.ts` (`mapPlaces` fixture), `web/e2e/map.spec.ts` (the hover test becomes hover-then-tap-opens-the-card)

**Interfaces:**
- Consumes: `FeatureDescription` from Task 5; `GET /api/map/places` from Task 3.
- Produces: `TappedPlace = FeatureDescription & { lat: number; lon: number; overlayId: string }`; `attachFeatureTooltip(map, overlays, onTap: (place: TappedPlace | null) => void)`; `PlaceCard({ place, from, fromLabel, guidance, onClose, onRoute, onPin, onNearby })`; `api.mapPlaces(): Promise<Record<string, PlaceGuidance>>` with `PlaceGuidance = { title: string; html: string; link: { href: string; title: string } }`.

- [ ] **Step 1: Failing tests**

`web/tests/map/tooltip.test.ts`: the hover test asserts the popup holds the title and the type line and no `dl`; a new test "a tap on a feature hands the place to onTap and closes the popup; a tap on empty map hands null" using the FakeMap's `fire('click', …)` helper the existing pin test uses.

`web/tests/screens/map.test.tsx` add:

```tsx
  it('tapping a feature opens the place card with the type, the distance from the centre, the rows, the guidance and three actions', async () => {
    mockApis();
    vi.spyOn(api, 'mapPlaces').mockResolvedValue(mapPlaces);
    const user = userEvent.setup();
    renderRoute('/map?lat=50.9379&lon=-1.4708&z=14&overlay=health');
    await screen.findByRole('group', { name: 'Map layers' });
    await act(async () => {});
    const map = lastMap();
    map.renderedFeatures = [{ layer: { id: 'sos-overlay-health-point' }, source: 'sos-overlay-health', properties: { name: 'Southampton General Hospital', amenity: 'hospital', emergency: 'yes', beds: '1200' } }];
    await act(async () => { map.fire('click', { point: { x: 10, y: 10 }, lngLat: { lng: -1.4353, lat: 50.9333 }, originalEvent: { pointerType: 'touch' } }); });
    const card = await screen.findByRole('dialog', { name: 'Place' });
    expect(within(card).getByRole('heading', { name: 'Southampton General Hospital' })).toBeInTheDocument();
    expect(within(card).getByText('Hospital · emergency department')).toBeInTheDocument();
    expect(within(card).getByText(/from the map centre, about \d+ min on foot/)).toBeInTheDocument();
    expect(within(card).getByText('Beds')).toBeInTheDocument();
    expect(within(card).getByText(/A&E stays open/)).toBeInTheDocument();
    expect(within(card).getByRole('link', { name: 'Medical' })).toHaveAttribute('href', '/m/medical');
    await user.click(within(card).getByRole('button', { name: 'Route from the centre' }));
    expect(screen.getByTestId('map-readout')).toHaveTextContent('Southampton General Hospital:');
    await user.click(within(card).getByRole('button', { name: 'Pin this place' }));
    expect(screen.getByRole('dialog', { name: 'Pins' })).toBeInTheDocument();
    expect(screen.getByLabelText('Pin name')).toHaveValue('Southampton General Hospital');
  });

  it('a Nearby row opens the card for that place and the card can search nearby from it', async () => {
    mockApis();
    vi.spyOn(api, 'mapPlaces').mockResolvedValue(mapPlaces);
    vi.spyOn(api, 'nearby').mockResolvedValue(nearby);
    const user = userEvent.setup();
    renderRoute('/map');
    await user.click(await screen.findByRole('button', { name: /Nearby/ }));
    await user.click(await screen.findByRole('button', { name: /Southampton General Hospital/ }));
    const card = screen.getByRole('dialog', { name: 'Place' });
    expect(within(card).getByText('Emergency department')).toBeInTheDocument();
    await user.click(within(card).getByRole('button', { name: 'Nearby from here' }));
    expect(screen.getByRole('dialog', { name: 'Nearby' })).toHaveTextContent('From Southampton General Hospital');
  });
```

Look at `web/tests/map/fakeMap.ts` for the real names of the rendered-features hook and `fire`; use those. Add to `web/tests/fixtures/api.ts` a `mapPlaces` object with `hospital` (`html: '<p>A&E stays open on generators for a few days… <a href="/m/medical">Medical</a></p>'`, `link: { href: '/m/medical', title: 'Medical' }`) and `fuel`, and a `nearby` fixture if none exists (see `tests/map/panel.test.tsx` for the shape).

- [ ] **Step 2: Run to see them fail**

Run: `pnpm --dir web test -- tests/screens/map.test.tsx tests/map/tooltip.test.ts`

- [ ] **Step 3: Tooltip: hover only, tap out**

`tooltip.ts`: `renderDescription` renders `title` and `typeLine` only (keep the function name; drop the `dl`). `attachFeatureTooltip(map, overlays, onTap)`: `onClick` → `hide()`; if a feature was hit, `onTap({ ...describeMapFeature(feature, overlays()), overlayId, lat: e.lngLat.lat, lon: e.lngLat.lng })`, else `onTap(null)`. Remove `pinned`. `describeMapFeature` keeps its signature.

`MapView.tsx`: new prop `onFeatureTap: (place: TappedPlace | null) => void`; pass `(p) => propsRef.current.onFeatureTap(p)` to `attachFeatureTooltip`.

- [ ] **Step 4: The card**

```tsx
// web/src/map/PlaceCard.tsx
import type { PlaceGuidance } from '../api/types';
import { Icon } from '../icons';
import { gridRef } from './grid';
import { bearingDeg, distanceKm, formatBearing, formatDistance, formatWalk, naismithMinutes, type LngLat } from './measure';
import { MapPanel } from './MapPanel';
import type { TappedPlace } from './tooltip';

/** Where the distance is measured from: home when the box has one, else the middle of the map. */
export type From = LngLat & { label: 'home' | 'the map centre' };

export function distanceLine(place: LngLat, from: From): string {
  const km = distanceKm(from, place);
  return `${formatDistance(km)} ${formatBearing(bearingDeg(from, place))} from ${from.label}, about ${formatWalk(naismithMinutes(km))} on foot`;
}

export function PlaceCard({ place, from, guidance, onClose, onRoute, onPin, onNearby }: {
  place: TappedPlace; from: From; guidance: PlaceGuidance | null;
  onClose: () => void; onRoute: () => void; onPin: () => void; onNearby: () => void;
}) {
  const rows = place.rows.filter(([label]) => label !== 'Type');
  return (
    <MapPanel
      label="Place" title={place.title} onClose={onClose}
      lead={
        <>
          <p className="map-lead-line">{place.typeLine}</p>
          <p className="map-lead-answer">{distanceLine(place, from)}</p>
          <p className="map-lead-line">{gridRef(place.lat, place.lon).text}</p>
        </>
      }
      actions={
        <>
          <button type="button" className="btn btn-small" onClick={onRoute}><Icon name="compass" size={18} /><span>Route from {from.label === 'home' ? 'home' : 'the centre'}</span></button>
          <button type="button" className="btn btn-small" onClick={onPin}><Icon name="pin" size={18} /><span>Pin this place</span></button>
          <button type="button" className="btn btn-small" onClick={onNearby}><Icon name="search" size={18} /><span>Nearby from here</span></button>
        </>
      }
    >
      {rows.length > 0 && (
        <section>
          <h3>What it has</h3>
          <dl className="place-rows">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
        </section>
      )}
      {guidance && (
        <section>
          <h3>What to expect here</h3>
          <div className="place-expect" dangerouslySetInnerHTML={{ __html: guidance.html }} />
          <a className="btn" href={guidance.link.href}>{guidance.link.title}</a>
        </section>
      )}
    </MapPanel>
  );
}
```

Links inside the HTML must navigate like every other rendered guide: find how `web/src/screens/Kit.tsx` (or `Page.tsx`) turns `dangerouslySetInnerHTML` anchors into router navigation (a `useHtmlLinks`-style hook or a click handler) and use the same thing here; the `<a className="btn">` becomes a router `<Link>` if that is what the app does elsewhere.

`Map.tsx`:
- `Panel` gains `'place'`; state `const [place, setPlace] = useState<TappedPlace | null>(null)`; `const placesQ = useQuery(() => api.mapPlaces(), [])`.
- `onFeatureTap={(p) => { if (measuring) return; setPlace(p); setPanel(p ? 'place' : panel === 'place' ? 'none' : panel); }}`.
- `from`: `homePoint ? { ...homePoint, label: 'home' } : { lat: view.lat, lon: view.lon, label: 'the map centre' }`.
- Render `{panel === 'place' && place && <PlaceCard place={place} from={from} guidance={place.kind ? placesQ.data?.[place.kind] ?? null : null} onClose={() => { setPanel('none'); setPlace(null); }} onRoute={() => setRouteTo({ title: place.title, lat: place.lat, lon: place.lon })} onPin={() => { setPendingPin({ lat: place.lat, lon: place.lon }); setPinTitle(place.title); setPanel('pins'); }} onNearby={() => { setNearbyOrigin('place'); setNearbyLabel(place.title); setNearbyAt({ lat: place.lat, lon: place.lon }); setPanel('nearby'); }} />}`.
- `nearbyOrigin` becomes `'home' | 'centre' | 'place'` with `nearbyLabel` state; the Nearby lead line says `From <strong>{nearbyLabel}</strong>, <grid>` for a place.
- Nearby rows: the `nearby-go` buttons call `openFromNearby(f, p)` which flies to the place and sets `place` to `{ title: placeName(p.name, f.title), typeLine: f.title, overlay: f.title, overlayId: f.id, kind: NEARBY_KIND[f.id] ?? null, rows: [], lat: p.lat, lon: p.lon }` and `setPanel('place')`, with `NEARBY_KIND: Record<string, PlaceKind> = { 'emergency-department': 'hospital', pharmacy: 'pharmacy', gp: 'gp', fuel: 'fuel', 'water-works': 'water-works' }` in `nearby.ts`.
- `api/client.ts`: `mapPlaces: () => request<Record<string, PlaceGuidance>>('GET', '/map/places')`; `types.ts`: `PlaceGuidance`.

CSS: `.place-rows` as `.map-tip-rows` was (two-column grid, one column under 480 px); `.place-expect p { margin: 0 0 8px; }`; `.map-panel section { display: flex; flex-direction: column; gap: 6px; }`.

- [ ] **Step 5: e2e**

`web/e2e/map.spec.ts` hover test: keep the hover assertions on the title and the type line (no `dd`); then `page.mouse.click(at.x, at.y)` and expect `page.getByRole('dialog', { name: 'Place' })` to contain "Southampton General Hospital" and "What to expect here"; a click on empty map closes it.

- [ ] **Step 6: Run and commit**

Run: `pnpm --dir web exec tsc --noEmit && pnpm --dir web test`
Expected: pass.

```bash
git add -A web/src web/tests web/e2e
git commit -m "map: tap a place for a card with what it has, how far it is and what to expect"
```

---

### Task 7: Rebuild the overlays and styles on this PC (controller runs this, not a subagent)

- [ ] Start the build in the background as soon as Task 2 lands: `cd /home/dan/OperationSOS && (setsid nohup api/.venv/bin/sos build-maps --steps overlays --force > ~/sos-content/maps-src/overlays-build.log 2>&1 < /dev/null &)`. It filters the whole extract seven times and pages three FeatureServers; allow an hour or more. Watch `tail -3 ~/sos-content/maps-src/overlays-build.log`.
- [ ] If `verify_manifest_kinds` fails because `airports` or `military` finalised as geojson, change that item's `kind`, `dest` and `source.artifact` in `manifest/overlays.json` (and drop its source and layers from `tools/map-styles/layers/overlays.json`), then rerun `--steps overlays --force` (the work-dir intermediates are reused).
- [ ] Then `api/.venv/bin/sos build-maps --steps styles verify --force` and copy `~/sos-content/maps/overlays`, `~/sos-content/maps/styles` into the dev content root the dev stack serves (see `.dev/full-manifest` and `dev/run-dev.sh` for the path), and refresh `size_bytes` and `as_at` on every overlay item from `~/sos-content/maps/overlays/index.json` (a five-line Python loop).
- [ ] Sample the built data: `ogrinfo -al -so` on the geojson outputs and `pmtiles show` on the pmtiles; confirm `emergency`, `beds`, `brand`, `fuel:diesel`, `icao` now appear, and that `flood-zones.pmtiles` lists layers `flood_england, flood_wales_z3, flood_wales_z2, flood_scotland_river, flood_scotland_coastal, flood_roi_river, flood_roi_coastal` and `access-land` coverage `england, wales`.

---

### Task 8: Finish: bundle, screenshots, docs

- [ ] `pnpm --dir web build`; restart the API (`kill -TERM $(pgrep -f 'run-dev\.[s]h')`, then start it as the memory file says); screenshot `/map?lat=50.933&lon=-1.435&z=14&overlay=health` at 390 px and 1024 px with a tapped hospital, and `/map?overlay=flood-zones&lat=52.4&lon=-3.5&z=9` (Wales) with the Playwright script under `web/`; look at them.
- [ ] `docs/superpowers/specs/2026-09-03-operation-sos-design.md`: where it describes the Layers panel and the base choice, rewrite to the chips and the single base; note the split ids and `coverage_note`.
- [ ] Update the memory file `project_operation_sos_dev_stack.md` with the overlay rebuild command and its duration, and the source grammar.
- [ ] Final commit.

---

## Self-review

- Spec coverage: §2 chips (Task 4), §3 one base (Task 4), §4 split and rebuild (Tasks 1, 7), §5 richer data (Task 1), §6 card and places.yaml and endpoint (Tasks 3, 5, 6), §7 Nearby (Task 6), §8 tests (each task), plus the coverage question (Task 2). Keyboard Enter on a focused map feature is not built: map features are not focusable; the Nearby rows are the keyboard path to a card.
- Names used across tasks: `OsmOverlay.tags`, `export_config_for`, `parse_source_specs`, `flood_coverage`, `coverage_note`, `FeatureDescription.typeLine/kind`, `TappedPlace`, `attachFeatureTooltip(map, overlays, onTap)`, `LayerChips`, `Terrain`, `setTerrainLayerVisible`, `api.mapPlaces`, `PlaceGuidance`. Each is defined in the task that produces it and named the same where consumed.
