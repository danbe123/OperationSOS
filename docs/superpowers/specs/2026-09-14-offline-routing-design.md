# Offline route planning, Part A: the routing engine

Date: 2026-09-14. Status: approved in conversation (the owner: "on the map be able to plan trips on
foot using overlays, like footpaths for walking with stops like POI hospital or shop or both support
car bike" → "real path-following routing" → "best route" → OSRM → "should be able for any overlay" as
stop types → stock OSRM profiles, not custom rights-of-way-aware ones).

This is Part A of a two-part feature: the offline routing engine and the API that serves it. Part B (the
trip-planner screen: picking stops from any overlay, mode chips, drawing the route) is a separate spec,
written once Part A exists to build on.

## 1. What is missing

The box has no routing engine by design (`web/src/map/nearby.ts`: "the box has no routing engine, so it
says the bearing, the distance and a Naismith walking time, and leaves the roads to the map"). The
footpaths overlay (`api/sos/mapbuild/overlays.py:build_footpaths`) is real UK rights-of-way data for
display only — nothing turns it into a routable network. Planning an actual trip needs real path-finding
over the same OSM data the map already ships, for three modes (foot, bike, car), through an ordered list
of stops.

## 2. Engine: OSRM, MLD, stock profiles

[OSRM](https://github.com/Project-OSRM/osrm-backend) is a compiled C++ engine with no JVM, ships official
pre-built Linux binaries for both x86_64 and arm64, and has mature `foot.lua`/`bike.lua`/`car.lua`
profiles. It fits this project's "own thin stack, systemd units, no Docker" pattern (spec
`2026-09-03-operation-sos-design.md`) the way GraphHopper (JVM) and Valhalla (heavier, elevation-focused)
do not: `osrm-routed` is one more native binary run as a systemd service, the same shape as
`kiwix-serve`/`llama-server` already are.

The box uses OSRM's **MLD** (Multi-Level Dijkstra) pipeline, not Contraction Hierarchies: MLD gives lower
peak memory on a large extract and — irrelevant to a box that builds its graph once and ships it in an
image, but worth recording — cheaper re-customization if a profile ever changes. Routing uses OSRM's stock
`foot`/`bike`/`car` profiles, unmodified: the owner chose not to layer the footpaths overlay's more precise
public-footpath/bridleway/byway designations on top, so a route may occasionally suggest a path OSM's own
`highway=`/`access=` tagging doesn't distinguish as finely as the UK's legal rights-of-way do. Any
future tightening (feeding PROW designations into custom profiles) is out of scope here.

## 3. Where the graph is built

Three sets of OSRM graph files — one per mode — are extracted, partitioned and customized from
`britain-and-ireland-latest.osm.pbf`, the same 2.6 GB Geofabrik file `api/sos/mapbuild/osm.py` already
downloads and caches (`maps-src/britain-and-ireland-latest.osm.pbf`) for the base map and the footpaths
overlay. No new source data.

**This build step runs on arm64 hardware — the target Pi itself, or an arm64-equivalent build host used
when assembling the box's image — not on the x86_64 dev PC the way `build-maps`/`build-crawl` do.**
OSRM ships official pre-built binaries for both architectures, so nothing needs compiling from source; the
reason to insist on arm64-to-arm64 rather than cross-building on x86_64 and shipping the result is that
OSRM's `.osrm*` graph files are not confirmed portable across architectures — nothing in OSRM's own
documentation states the on-disk graph format is architecture-independent, and getting this wrong would
only surface as `osrm-routed` refusing to start (or worse, loading corrupt data) on the box itself, late
and hard to diagnose. Building on the same architecture the box runs sidesteps the question rather than
gambling on it. If the owner's image-build process turns out to already run on real Pi hardware or an
arm64 QEMU target, this step slots into that; if not, it needs one.

For a UK+Ireland extract on the car profile, published reports put MLD peak memory in the low single-digit
gigabytes (comparable to "a large US state"); the Pi 5 8GB board this box targets has headroom for that
one profile at a time. Build one mode at a time, not concurrently, to keep peak memory down further.

A new PC-CLI-shaped-but-arm64-run subcommand, `sos build-routing [--only foot|bike|car]`, wraps the three
OSRM steps per mode:

```
osrm-extract  -p /usr/share/osrm/profiles/<mode>.lua  britain-and-ireland-latest.osm.pbf
osrm-partition britain-and-ireland-latest.osrm
osrm-customize britain-and-ireland-latest.osrm
```

writing each mode's output set under `core/routing/<mode>/` (e.g. `core/routing/foot/britain-and-ireland-latest.osrm*`).
This mirrors the existing `sos build-crawl`/`sos build-maps`/`sos build-books` family: one more
`PC only` (here, `arm64 only`) build command, reported in the CLI's own docstring the same way.

## 4. How it's served

Three `osrm-routed --algorithm mld` instances, one per mode, each its own systemd unit and port —
`sos-osrm-foot.service` (port 8091), `sos-osrm-bike.service` (port 8092), `sos-osrm-car.service` (port
8093) — following the exact shape of `install/systemd/kiwix-serve.service` and `sos-llama.service`
(`127.0.0.1`-bound, `ExecStart` naming the binary and its data file directly, no wrapper script). Absent
graph files (extended tier not built, or `sos build-routing` not yet run) mean the unit fails to start;
`sos-api` treats that the same way it already treats kiwix or llama being down — a degraded capability,
not a crash.

## 5. The API

`GET /api/route?mode={foot|bike|car}&points=lon,lat;lon,lat;...` (2+ points: origin, any number of
stops in order, destination) proxies to the matching `osrm-routed` instance's own
`/route/v1/{profile}/{coordinates}` endpoint, requesting every point as an OSRM waypoint in one call —
OSRM already returns one continuous route through an ordered list of waypoints, so stops need no
custom multi-leg orchestration on this box's side. The backend reshapes OSRM's response into
`{geometry: GeoJSON LineString, distance_m: number, duration_s: number}`, dropping everything else
OSRM returns (turn-by-turn instructions, alternative routes) since Part B's map-only display doesn't
use them. A mode whose systemd unit isn't running (or is still loading a multi-GB graph — OSRM's own
docs note this can take minutes) is a 503 with a message the frontend can show, not a crash.

## 6. Manifest and image footprint

Each mode's graph set is a `kind: "dir"`, `tier: "core"`, `category: "maps"` manifest item (`dest:
"routing/<mode>"`), `source: {"type": "build", "tool": "build-routing"}` — the same "declared but built
elsewhere" shape `manifest/maps.json`'s other build-only entries already use. `size_bytes` gets filled in
once real graphs exist; until then these three items are placeholders the way `owner-books` already is.

## 7. Out of scope (Part B and beyond)

- The trip-planner screen, stop-picking from overlays, mode chips, drawing the route with
  `sos-route-line` — Part B, a separate spec once Part A is built and provably serves a route.
- Feeding the footpaths overlay's precise PROW designations into custom Lua profiles (declined above).
- Turn-by-turn instructions, alternative routes, live rerouting.
- Elevation-aware routing or ascent/descent figures (OSRM's stock profiles don't use elevation; the
  existing Naismith estimate in `nearby.ts` stays the box's only ascent-aware number).

## 8. Testing

- `api/tests`: `sos build-routing`'s command construction is unit-testable the same way `buildcrawl.py`
  and `buildbooks.py` already are (an injected `run` callable, no real OSRM invocation in CI).
- The `/api/route` proxy is testable against a fixture `osrm-routed` response (a fixed JSON blob) via an
  injected HTTP client, the same pattern `sos.sync`'s tests already use for `httpx.MockTransport`.
- No CI step builds a real graph (multi-GB, arm64-only) — `build-routing`'s own verification (graph loads,
  a known-good route between two fixture coordinates returns a sane distance) runs on real hardware during
  image preparation, not in the PC test suite.
