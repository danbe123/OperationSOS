# Operation SOS Maps Pipeline (sub-plan 04) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `sos build-maps`, the PC-only pipeline that turns Protomaps, Ordnance Survey, OSNI, Copernicus, OpenStreetMap, flood-agency and Organic Maps sources into the verified `/maps/*` tree (`uk-ie.pmtiles`, `os-zoomstack.pmtiles`, `contours.pmtiles`, `hillshade.pmtiles`, styles, sprites, glyphs, overlays, `places.csv.gz`, phone packs), plus `manifest/maps.json`, `tools/map-styles/`, and the committed `--fixture` outputs under `api/tests/fixtures/maps/` that the frontend, Playwright and the API tests run against.

**Architecture:** `api/sos/buildmaps.py` is the `sos build-maps` entry point: argparse wiring, tool check, a step registry, staging (`<out>/.incoming/` then `rename(2)`), idempotence and logging. Each pipeline stage is one small module under `api/sos/mapbuild/` exposing a `Step` object (`id`, `outputs(ctx)`, `run(ctx)`) that only assembles and runs external commands through `ctx.run(...)`, so every stage is unit-tested with a recording fake runner and no network. `tools/map-styles/` holds the Node style generator (`@protomaps/basemaps`), MapLibre layer fragments, osmium export configs and hand-authored site lists. A final `verify` step runs `pmtiles verify` on every archive, checks the base map bbox, zoom and probe tiles, checks that every style source resolves to a produced file, and writes sizes into the manifest.

**Tech Stack:** Python 3.12 (`httpx`, `pyproj` as the PC-only `maps` extra), pytest + respx, go-pmtiles 1.31.2, tippecanoe 2.79 (`tile-join`), osmium-tool 1.19, GDAL 3.13 (`ogr2ogr`, `gdalwarp`, `gdaldem`, `gdal_translate`, `gdaladdo`, `gdalbuildvrt`, `gdal_contour`), aria2c 1.37, Node 22 + pnpm with `@protomaps/basemaps` 5.7.2 and `@maplibre/maplibre-gl-style-spec` 26.4.1 (tests only), `node --test`.

**Spec:** `docs/superpowers/specs/2026-09-03-operation-sos-design.md` (section 9 Maps, section 13 `sos build-maps`, section 14 Build pipelines row, section 15 milestone 3). Overview: `docs/superpowers/plans/2026-09-03-00-overview.md` (repository layout, manifest item shape, `MapConfig`, URL conventions and the CLI table are locked).

**Deviations:** (1) The spec says the OS styles are "rewritten with jq"; `jq` is not installed on the PC and there is no sudo, so the identical transformation is implemented in Python (`sos.mapbuild.styles.rewrite_os_style`) and unit-tested; the overview does not name jq, so no contract changes. (2) The overview lists a single `api/sos/buildmaps.py`; the pipeline has nine stages and would exceed 2,000 lines in one file, so `buildmaps.py` keeps the CLI, registry and staging and each stage lives in `api/sos/mapbuild/<stage>.py` (stated reason: file size and per-stage testability). (3) The spec's Hillshade row lists the DTM sources as "OS Terrain 50, OSNI, Copernicus (later inputs win)"; `gdalwarp` puts the last input on top, so the command passes them as `glo30.vrt osni.vrt t50.vrt` (Copernicus first, OS last) exactly as review finding 77 specifies, so OS and OSNI data win where they exist. (4) Spec section 13 says `--fixture` runs "in under five minutes and is the CI test"; the OS inputs are 2.9 GB and 1.1 GB single files with no regional download, so `--fixture` runs on the PC against a source cache (`SOS_MAPS_SRC`, default `~/sos-content/maps-src`, filled on the first run) and finishes in under five minutes with a warm cache; CI runs the mocked pytest suite plus `test_buildmaps_fixture_outputs.py` over the committed fixture files, and `make fixtures` regenerates them.

## Global Constraints

- Python 3.12 or newer; Node 22 or newer; pnpm for `tools/map-styles`. No Docker. No runtime dependency on the internet on the box (the pipeline itself runs on the PC and needs the internet).
- No CDN references in any produced style: every `sources.*.url` is `pmtiles:///maps/<file>`, `sprite` is `/maps/sprites/...`, `glyphs` is `/maps/fonts/{fontstack}/{range}.pbf`.
- Map files are written to `<out>/.incoming/` and moved into place with `rename(2)` (`os.replace`), so open viewers never see a partial file.
- Base map: `pmtiles extract https://build.protomaps.com/<YYYYMMDD>.pmtiles uk-ie.pmtiles --bbox=-11,49.1,2.2,61.2 --download-threads=8`, build pinned in `install/versions.env` (`PROTOMAPS_BUILD=20260902`); the build fails if no zoom-12 tile covers St Helier (49.19, -2.11) or Lerwick (60.15, -1.15).
- `--fixture` uses the 0.1° bbox `-1.56,50.87,-1.46,50.97` (Southampton Water; contains OS HQ 50.9379, -1.4708); `api/tests/fixtures/maps/test.pmtiles` must be under 5 MiB (measured 4.9 MB on build 20260902).
- Any overlay whose GeoJSON exceeds 5 MB is tiled with tippecanoe and declared `pmtiles`.
- Every PMTiles output passes `pmtiles verify`; every `source-layer` in an OS style is asserted present in `os-zoomstack.pmtiles`; `Arial Unicode MS Regular` is removed from every `text-font` stack.
- Manifest items follow the overview shape exactly; `kind` for the outputs: `pmtiles`, `style`, `sprites`, `glyphs`, `places`, `mwm`, `apk`; `dest` is relative to the tier root (`maps/...`).
- British English in every authored string; product name "Operation SOS", short name "SOS"; never "NOMAD".
- Every commit passes `make test`. Tests never touch the network (respx for `httpx`, a fake runner for subprocesses).
- All tools run from the `sos-maps` micromamba env plus `~/.local/bin`; the CLI prints the activation hint when a tool is missing.

---

## File structure

| Path | Responsibility |
|---|---|
| `api/sos/buildmaps.py` | `sos build-maps` CLI: `add_arguments`, `main`, `run`, step registry, `run_steps` (idempotence, logging) |
| `api/sos/mapbuild/__init__.py` | package marker |
| `api/sos/mapbuild/common.py` | `Context` (out/src/bbox/staging/sidecars/downloads/`run`), `BuildError`, tool check, `versions.env` reader, PMTiles helpers, GeoJSON helpers |
| `api/sos/mapbuild/base.py` | step `base`: Protomaps extract + `check_base` |
| `api/sos/mapbuild/osdata.py` | OS Downloads API client, `os_fetch`, `unzip_single`; step `os` (Zoomstack → `os-zoomstack.pmtiles`) |
| `api/sos/mapbuild/styles.py` | step `styles`: Node generator, asset vendoring, OS style rewrite, `styles/index.json`, layer fragments |
| `api/sos/mapbuild/osm.py` | OSM PBF input (full or fixture extract), region polygons, non-GB cutline |
| `api/sos/mapbuild/dem.py` | Copernicus GLO-30 tiles, OS Terrain 50 ASCII grids, OSNI DTM, per-source VRTs |
| `api/sos/mapbuild/contours.py` | step `contours` |
| `api/sos/mapbuild/hillshade.py` | step `hillshade` |
| `api/sos/mapbuild/overlays.py` | step `overlays`: footpaths, OSM POI overlays, flood zones, access land, nuclear and chemical sites, size rule, `overlays/index.json` |
| `api/sos/mapbuild/places.py` | step `places`: OS Open Names + OSM place nodes → `places.csv.gz` |
| `api/sos/mapbuild/packs.py` | step `packs`: Organic Maps `.mwm`, APK, `packs/index.html`, `packs/index.json` |
| `api/sos/mapbuild/verify.py` | step `verify`: `pmtiles verify`, base checks, style sources, sizes → manifest, fixture manifest |
| `api/tests/mapbuild_helpers.py` | `FakeRunner`, `make_ctx` shared by the build-maps tests |
| `api/tests/test_buildmaps_*.py` | one test module per task |
| `api/tests/fixtures/maps/src/*.geojson` | tiny committed flood and access-land samples used by `--fixture` |
| `api/tests/fixtures/maps/` | committed `--fixture` outputs (`test.pmtiles`, `os-zoomstack.pmtiles`, `contours.pmtiles`, `hillshade.pmtiles`, `overlays/`, `styles/`, `sprites/`, `fonts/`, `places.csv.gz`, `packs/index.*`) |
| `api/tests/fixtures/manifest/maps.json` | fixture manifest written by `--fixture` (dests point at the fixture files) |
| `tools/map-styles/package.json`, `pnpm-lock.yaml` | pinned `@protomaps/basemaps` 5.7.2, dev `@maplibre/maplibre-gl-style-spec` 26.4.1 |
| `tools/map-styles/build-styles.mjs` | generates `osm-light.json`, `osm-dark.json`, `osm-vault.json` |
| `tools/map-styles/build-styles.test.mjs` | `node --test` style validity tests |
| `tools/map-styles/layers/*.json` | MapLibre fragments (`contours`, `hillshade`, `footpaths`, `flood-zones`, `overlays`) copied to `styles/layers/` |
| `tools/map-styles/export/*.json` | osmium export configs (`paths`, `pois`, `places`, `regions`) |
| `tools/map-styles/data/nuclear-sites.geojson`, `data/chemical-sites.geojson` | hand-authored site lists (nuclear seeded here only if plan 03 has not created it) |
| `manifest/maps.json` | the twelve map items |
| `install/versions.env` | maps block (`PROTOMAPS_BUILD`, asset commits, Organic Maps tag/APK/sha256, source URLs) |
| `.gitignore` | exceptions so the fixture PMTiles and glyphs are committed |

Output tree produced under `<out>` (mirrored by the fixture directory, where the base is `test.pmtiles`):

```
uk-ie.pmtiles  uk-ie.json           os-zoomstack.pmtiles  os-zoomstack.json
contours.pmtiles  contours.json     hillshade.pmtiles  hillshade.json
styles/{index.json, osm-light.json, osm-dark.json, osm-vault.json, os-outdoor.json, os-night.json, layers/*.json}
sprites/v4/{light,dark}{,@2x}.{json,png}   sprites/os/sprites{,@2x,@3x}.{json,png}
fonts/<face>/<range>.pbf   (Noto Sans Regular|Medium|Italic, Source Sans Pro Regular|Bold|Italic|SemiBold, Open Sans Regular)
overlays/{index.json, footpaths.pmtiles, flood-zones.pmtiles, nuclear-sites.geojson, health.geojson, fuel.geojson, rail.geojson, chemical-sites.geojson, water.pmtiles, airports-military.pmtiles, access-land.(geojson|pmtiles)}
places.csv.gz  places.json
packs/{index.html, index.json, <id>.mwm..., OrganicMaps-26082718-web-release.apk}
build.json
```

Step registry order (also the default `--steps`): `base os contours hillshade overlays places packs styles verify` (`styles` runs after `overlays` because it prunes the overlay layer fragment by the built overlay kinds and reads the contours sidecar for the height attribute name; the task order below follows the assignment, not the registry). Each step skips itself when all of its declared outputs exist unless `--force` is given; `verify` always runs when selected.

---

### Task 1: `buildmaps.py` skeleton, context, staging, tool check and CLI wiring

**Files:**
- Create: `api/sos/buildmaps.py`
- Create: `api/sos/mapbuild/__init__.py`
- Create: `api/sos/mapbuild/common.py`
- Create: `api/tests/__init__.py` (empty; only if plan 01 did not create it, so `from tests.mapbuild_helpers import ...` resolves with `api/` on `sys.path`)
- Create: `api/tests/mapbuild_helpers.py`
- Create: `api/tests/test_buildmaps_cli.py`
- Modify: `api/sos/cli.py` (the `build-maps` subparser that plan 01 left as "not implemented")
- Modify: `api/pyproject.toml` (add the `maps` optional dependency group)
- Modify: `install/versions.env` (append the maps block; create the file with only this block if plan 01's file is not present yet)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `sos.cli.main(argv)` argparse CLI with subparsers (plan 01); `install/versions.env` `KEY=VALUE` lines (plan 01).
- Produces (used by every later task):
  - `sos.mapbuild.common.Context(out, src, fixture, force, build, versions, repo, runner)` with `bbox: BBox`, `base_name: str`, `incoming: Path`, `version(key) -> str`, `run(cmd, *, cwd=None, capture=False, binary=False) -> CompletedProcess`, `output(name) -> Path`, `stage(name) -> Path`, `commit(name) -> Path`, `write_sidecar(name, data) -> Path`, `sidecar(name) -> dict | None`, `download(url, name, *, sha256=None, md5=None) -> Path`.
  - `BuildError`, `BBox`, `SPEC_BBOX`, `FIXTURE_BBOX`, `FIXTURE_MAX_BYTES`, `MICROMAMBA_HINT`, `REQUIRED_TOOLS`, `bbox_str`, `bbox_args`, `bbox_intersects`, `bbox_polygon`, `lonlat_to_tile`, `check_tools`, `read_versions`, `repo_root`, `dir_size`, `sidecar_path`, `sha256_file`, `real_runner`, `fetch_github_tarball(ctx, owner_repo, sha) -> Path`, `pmtiles_header(ctx, path) -> dict`, `pmtiles_metadata(ctx, path) -> dict`, `vector_layer_ids(metadata) -> set[str]`, `tile_exists(ctx, path, z, x, y) -> bool`, `pmtiles_verify(ctx, path)`, `read_geojsonseq(path) -> list[dict]`, `validate_geojson(obj) -> list[str]`.
  - `sos.buildmaps.STEP_IDS`, `all_steps() -> list`, `select_steps(ids) -> list`, `run_steps(ctx, ids)`, `add_arguments(parser)`, `run(args) -> int`, `main(argv=None) -> int`.
  - `api/tests/mapbuild_helpers.py`: `FakeRunner(outputs=None, files=None)` with `.calls`, `.find(*prefix)`; `make_ctx(tmp_path, *, fixture=True, runner=None, versions=None, force=False, build="20260902") -> Context`; `REPO` (repo root path).

- [ ] **Step 1: Write the failing tests**

`api/tests/mapbuild_helpers.py`:

```python
"""Test doubles for the build-maps pipeline: a recording runner and a Context factory."""
from __future__ import annotations

import subprocess
from pathlib import Path

from sos.mapbuild.common import Context

REPO = Path(__file__).resolve().parents[2]

DEFAULT_VERSIONS = {
    "PROTOMAPS_BUILD": "20260902",
    "PROTOMAPS_BUILDS_BASE": "https://build.protomaps.com",
    "PROTOMAPS_BASEMAPS_NPM": "5.7.2",
    "BASEMAPS_ASSETS_COMMIT": "028c18f713baecad011301ff7a69acc39bcc2ae7",
    "OS_ZOOMSTACK_STYLES_COMMIT": "d23143b4a36435680eda99b4febb3187398f594f",
    "OS_DOWNLOADS_API": "https://api.os.uk/downloads/v1",
    "GEOFABRIK_PBF_URL": "https://example.test/britain-and-ireland-latest.osm.pbf",
    "GEOFABRIK_FIXTURE_PBF_URL": "https://example.test/hampshire-latest.osm.pbf",
    "COPERNICUS_DEM_BASE": "https://example.test/dem",
    "OSNI_DTM_URL": "",
    "ORGANICMAPS_TAG": "2026.08.27-18-android",
    "ORGANICMAPS_CDN": "https://example.test/maps",
    "ORGANICMAPS_APK_URL": "https://example.test/OrganicMaps-26082718-web-release.apk",
    "ORGANICMAPS_APK_SHA256": "1f19229d95b731862349d504b150dad63eb405caa83e98c96bfe93b7acae3c7a",
    "FLOOD_EN_URL": "",
    "FLOOD_WA_URL": "",
    "FLOOD_SC_URL": "",
    "FLOOD_NI_URL": "",
    "FLOOD_IE_URL": "",
    "ACCESS_EN_URL": "",
    "ACCESS_WA_URL": "",
}


class FakeRunner:
    """Records every command. `outputs` maps "tool subcommand" to stdout (str, bytes or a callable of the
    command). `files` maps a path suffix to bytes: any command token ending with that suffix is created
    with those bytes, and an aria2c command creates `-d/-o` with the bytes keyed by the `-o` name."""

    def __init__(self, outputs: dict[str, object] | None = None, files: dict[str, bytes] | None = None):
        self.outputs = outputs or {}
        self.files = files or {}
        self.calls: list[list[str]] = []

    def __call__(self, cmd, *, cwd=None, capture=False, binary=False):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        if cmd[0] == "aria2c":
            directory = Path(cmd[cmd.index("-d") + 1])
            name = cmd[cmd.index("-o") + 1]
            directory.mkdir(parents=True, exist_ok=True)
            (directory / name).write_bytes(self.files.get(name, b"downloaded"))
        else:
            for token in cmd:
                for suffix, data in self.files.items():
                    if "/" in token and token.endswith(suffix):
                        Path(token).parent.mkdir(parents=True, exist_ok=True)
                        Path(token).write_bytes(data)
        out = self.outputs.get(" ".join(cmd[:2]), "")
        if callable(out):
            out = out(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    def find(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.calls if c[: len(prefix)] == list(prefix)]


def make_ctx(tmp_path: Path, *, fixture: bool = True, runner=None, versions: dict[str, str] | None = None,
             force: bool = False, build: str = "20260902") -> Context:
    out = tmp_path / "out"
    src = tmp_path / "src"
    out.mkdir(parents=True, exist_ok=True)
    src.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_VERSIONS)
    merged.update(versions or {})
    return Context(out=out, src=src, fixture=fixture, force=force, build=build, versions=merged,
                   repo=REPO, runner=runner or FakeRunner())
```

`api/tests/test_buildmaps_cli.py`:

```python
import json
from pathlib import Path

import pytest

from sos import buildmaps
from sos.mapbuild import common
from sos.mapbuild.common import BuildError, Context, read_versions, lonlat_to_tile
from tests.mapbuild_helpers import FakeRunner, make_ctx


def test_missing_tools_exit_2_with_micromamba_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(buildmaps, "check_tools", lambda: ["tippecanoe", "pmtiles"])
    rc = buildmaps.main(["--out", str(tmp_path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "tippecanoe" in err and "pmtiles" in err
    assert "micromamba activate sos-maps" in err


def test_check_tools_lists_only_missing():
    missing = common.check_tools(which=lambda t: None if t in ("osmium", "gdalwarp") else "/usr/bin/" + t)
    assert missing == ["osmium", "gdalwarp"]


def test_read_versions_parses_env_file(tmp_path):
    env = tmp_path / "versions.env"
    env.write_text('# comment\nPROTOMAPS_BUILD=20260902\nORGANICMAPS_TAG="2026.08.27-18-android"\n\nBROKEN LINE\n')
    assert read_versions(env) == {"PROTOMAPS_BUILD": "20260902", "ORGANICMAPS_TAG": "2026.08.27-18-android"}
    assert read_versions(tmp_path / "missing.env") == {}


def test_context_version_raises_on_blank(tmp_path):
    ctx = make_ctx(tmp_path, versions={"OSNI_DTM_URL": ""})
    with pytest.raises(BuildError, match="OSNI_DTM_URL"):
        ctx.version("OSNI_DTM_URL")
    assert ctx.version("PROTOMAPS_BUILDS_BASE") == "https://build.protomaps.com"


def test_fixture_context_uses_fixture_bbox_and_name(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    assert ctx.bbox == (-1.56, 50.87, -1.46, 50.97)
    assert ctx.base_name == "test.pmtiles"
    full = make_ctx(tmp_path, fixture=False)
    assert full.bbox == (-11.0, 49.1, 2.2, 61.2)
    assert full.base_name == "uk-ie.pmtiles"
    assert common.bbox_str(full.bbox) == "-11,49.1,2.2,61.2"


def test_stage_then_commit_renames_into_place(tmp_path):
    ctx = make_ctx(tmp_path)
    staged = ctx.stage("overlays/health.geojson")
    assert staged == ctx.incoming / "overlays" / "health.geojson"
    staged.write_text("{}")
    final = ctx.commit("overlays/health.geojson")
    assert final == ctx.out / "overlays" / "health.geojson"
    assert final.read_text() == "{}"
    assert not staged.exists()


def test_commit_replaces_existing_directory(tmp_path):
    ctx = make_ctx(tmp_path)
    (ctx.out / "styles").mkdir()
    (ctx.out / "styles" / "old.json").write_text("old")
    d = ctx.stage("styles")
    d.mkdir()
    (d / "new.json").write_text("new")
    ctx.commit("styles")
    assert sorted(p.name for p in (ctx.out / "styles").iterdir()) == ["new.json"]


def test_sidecar_records_size_and_data(tmp_path):
    ctx = make_ctx(tmp_path)
    ctx.stage("x.pmtiles").write_bytes(b"12345")
    ctx.commit("x.pmtiles")
    side = ctx.write_sidecar("x.pmtiles", {"step": "base"})
    assert side == ctx.out / "x.json"
    data = json.loads(side.read_text())
    assert data["output"] == "x.pmtiles" and data["size_bytes"] == 5 and data["step"] == "base"
    assert "built_at" in data
    assert ctx.sidecar("x.pmtiles")["size_bytes"] == 5
    assert ctx.sidecar("missing.pmtiles") is None
    assert common.sidecar_path(Path("/m/places.csv.gz")) == Path("/m/places.json")
    assert common.sidecar_path(Path("/m/styles")) == Path("/m/styles.json")


def test_download_uses_aria2c_and_caches(tmp_path):
    runner = FakeRunner(files={"a.zip": b"zipbytes"})
    ctx = make_ctx(tmp_path, runner=runner)
    path = ctx.download("https://example.test/a.zip", "a.zip", md5="abc")
    assert path == ctx.src / "a.zip" and path.read_bytes() == b"zipbytes"
    cmd = runner.calls[0]
    assert cmd[0] == "aria2c" and "-c" in cmd and "--checksum=md5=abc" in cmd
    assert cmd[cmd.index("-d") + 1] == str(ctx.src) and cmd[cmd.index("-o") + 1] == "a.zip"
    assert cmd[-1] == "https://example.test/a.zip"
    ctx.download("https://example.test/a.zip", "a.zip")
    assert len(runner.calls) == 1, "second download must be served from the cache"


def test_download_into_subdirectory(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    path = ctx.download("https://example.test/t.tif", "copernicus/t.tif", sha256="ff" * 32)
    assert path == ctx.src / "copernicus" / "t.tif" and path.exists()
    cmd = runner.calls[0]
    assert cmd[cmd.index("-d") + 1] == str(ctx.src / "copernicus")
    assert "--checksum=sha-256=" + "ff" * 32 in cmd


def test_lonlat_to_tile_known_points():
    assert lonlat_to_tile(49.19, -2.11, 12) == (2023, 1403)   # St Helier
    assert lonlat_to_tile(60.15, -1.15, 12) == (2034, 1186)   # Lerwick
    assert lonlat_to_tile(50.9, -1.4, 10) == (508, 343)


def test_pmtiles_helpers_parse_header_metadata_and_tiles(tmp_path):
    header = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 15, "bounds": [-11, 49.1, 2.2, 61.2]}
    meta = {"vector_layers": [{"id": "roads", "fields": {}}, {"id": "water", "fields": {}}]}
    runner = FakeRunner(outputs={
        "pmtiles show": lambda cmd: json.dumps(header if "--header-json" in cmd else meta),
        "pmtiles tile": lambda cmd: b"\x1f\x8b" if cmd[-2:] == ["2023", "1403"] else b"",
    })
    ctx = make_ctx(tmp_path, runner=runner)
    assert common.pmtiles_header(ctx, Path("/x/a.pmtiles"))["maxzoom"] == 15
    assert common.vector_layer_ids(common.pmtiles_metadata(ctx, Path("/x/a.pmtiles"))) == {"roads", "water"}
    assert common.tile_exists(ctx, Path("/x/a.pmtiles"), 12, 2023, 1403) is True
    assert common.tile_exists(ctx, Path("/x/a.pmtiles"), 12, 1, 1) is False
    common.pmtiles_verify(ctx, Path("/x/a.pmtiles"))
    assert runner.find("pmtiles", "verify") == [["pmtiles", "verify", "/x/a.pmtiles"]]


class DummyStep:
    def __init__(self, sid, outputs):
        self.id = sid
        self._outputs = outputs
        self.runs = 0

    def outputs(self, ctx):
        return self._outputs

    def run(self, ctx):
        self.runs += 1
        for name in self._outputs:
            p = ctx.stage(name)
            p.write_text("built")
            ctx.commit(name)


def test_run_steps_skips_up_to_date_and_force_rebuilds(tmp_path, monkeypatch):
    step = DummyStep("base", ["test.pmtiles"])
    monkeypatch.setattr(buildmaps, "all_steps", lambda: [step])
    ctx = make_ctx(tmp_path)
    buildmaps.run_steps(ctx, ["base"])
    buildmaps.run_steps(ctx, ["base"])
    assert step.runs == 1
    ctx.force = True
    buildmaps.run_steps(ctx, ["base"])
    assert step.runs == 2


def test_run_steps_fails_when_step_leaves_outputs_missing(tmp_path, monkeypatch):
    class Lazy(DummyStep):
        def run(self, ctx):
            self.runs += 1
    monkeypatch.setattr(buildmaps, "all_steps", lambda: [Lazy("base", ["test.pmtiles"])])
    with pytest.raises(BuildError, match="did not produce"):
        buildmaps.run_steps(make_ctx(tmp_path), ["base"])


def test_select_steps_keeps_registry_order_and_rejects_unknown(monkeypatch):
    a, b = DummyStep("base", []), DummyStep("verify", [])
    monkeypatch.setattr(buildmaps, "all_steps", lambda: [a, b])
    assert [s.id for s in buildmaps.select_steps(["verify", "base"])] == ["base", "verify"]
    assert [s.id for s in buildmaps.select_steps(None)] == ["base", "verify"]
    with pytest.raises(BuildError, match="hillshade"):
        buildmaps.select_steps(["hillshade"])


def test_run_resolves_defaults_and_runs_selected_steps(tmp_path, monkeypatch):
    monkeypatch.setattr(buildmaps, "check_tools", lambda: [])
    monkeypatch.setattr(buildmaps, "repo_root", lambda: tmp_path)
    (tmp_path / "install").mkdir()
    (tmp_path / "install" / "versions.env").write_text("PROTOMAPS_BUILD=20260902\n")
    monkeypatch.setenv("SOS_MAPS_SRC", str(tmp_path / "cache"))
    seen = {}
    def fake_run_steps(ctx, ids):
        seen["ctx"], seen["ids"] = ctx, ids
    monkeypatch.setattr(buildmaps, "run_steps", fake_run_steps)
    rc = buildmaps.main(["--fixture", "--steps", "base", "verify", "--build", "20260101"])
    assert rc == 0
    ctx = seen["ctx"]
    assert seen["ids"] == ["base", "verify"]
    assert ctx.fixture is True and ctx.build == "20260101"
    assert ctx.out == tmp_path / "api" / "tests" / "fixtures" / "maps"
    assert ctx.src == tmp_path / "cache"
    assert ctx.out.is_dir() and ctx.src.is_dir()


def test_run_returns_1_on_build_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(buildmaps, "check_tools", lambda: [])
    monkeypatch.setattr(buildmaps, "repo_root", lambda: tmp_path)
    (tmp_path / "install").mkdir()
    (tmp_path / "install" / "versions.env").write_text("PROTOMAPS_BUILD=20260902\n")
    def boom(ctx, ids):
        raise BuildError("no z12 tile covering Lerwick")
    monkeypatch.setattr(buildmaps, "run_steps", boom)
    assert buildmaps.main(["--out", str(tmp_path / "o"), "--steps", "base"]) == 1
    assert "Lerwick" in capsys.readouterr().err


def test_cli_exposes_build_maps(capsys):
    from sos import cli
    with pytest.raises(SystemExit) as exc:
        cli.main(["build-maps", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--out", "--steps", "--build", "--fixture", "--force"):
        assert flag in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_cli.py -q 2>&1 | tail -3`
Expected: `ERROR ... ModuleNotFoundError: No module named 'sos.mapbuild'` (collection error).

- [ ] **Step 3: Write `common.py`, `buildmaps.py`, the package marker, and the wiring**

`api/sos/mapbuild/__init__.py`:

```python
"""Stages of the PC-only `sos build-maps` pipeline (plan 04)."""
```

`api/sos/mapbuild/common.py`:

```python
"""Shared plumbing for `sos build-maps`: context, staging, downloads, tool checks, PMTiles helpers."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger("sos.buildmaps")

BBox = tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
SPEC_BBOX: BBox = (-11.0, 49.1, 2.2, 61.2)
# 0.1 degree box over Southampton Water and the New Forest edge; contains OS HQ (50.9379, -1.4708).
# Measured 4.9 MB at z15 on build 20260902 (the city-centre box is 6.8 MB and fails the 5 MiB rule).
FIXTURE_BBOX: BBox = (-1.56, 50.87, -1.46, 50.97)
FIXTURE_MAX_BYTES = 5 * 1024 * 1024
MICROMAMBA_HINT = (
    "activate the maps toolchain first:\n"
    '  export MAMBA_ROOT_PREFIX=$HOME/micromamba; eval "$(micromamba shell hook -s bash)"; '
    "micromamba activate sos-maps\n"
    "  export PATH=$HOME/.local/bin:$PATH   # pmtiles"
)
REQUIRED_TOOLS = (
    "pmtiles", "tippecanoe", "tile-join", "osmium", "ogr2ogr", "gdalwarp", "gdaldem", "gdal_translate",
    "gdaladdo", "gdalbuildvrt", "gdal_contour", "aria2c", "node", "pnpm", "tar",
)


class BuildError(RuntimeError):
    """A pipeline failure carrying a message meant for the terminal."""


def bbox_str(bbox: BBox) -> str:
    return ",".join(f"{v:g}" for v in bbox)


def bbox_args(bbox: BBox) -> list[str]:
    return [f"{v:g}" for v in bbox]


def bbox_intersects(a: BBox, b: BBox) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def bbox_polygon(bbox: BBox) -> dict:
    x0, y0, x1, y1 = bbox
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def lonlat_to_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def check_tools(which: Callable[[str], str | None] = shutil.which) -> list[str]:
    return [tool for tool in REQUIRED_TOOLS if which(tool) is None]


def read_versions(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def repo_root() -> Path:
    env = os.environ.get("SOS_REPO")
    root = Path(env).resolve() if env else Path(__file__).resolve().parents[3]
    if not (root / "install" / "versions.env").exists():
        raise BuildError(f"{root} is not the Operation SOS checkout (no install/versions.env); set SOS_REPO")
    return root


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def sidecar_path(final: Path) -> Path:
    """`uk-ie.pmtiles` -> `uk-ie.json`, `places.csv.gz` -> `places.json`, `styles/` -> `styles.json`."""
    return final.with_name(final.name.split(".", 1)[0] + ".json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def real_runner(cmd: list[str], *, cwd: Path | None = None, capture: bool = False,
                binary: bool = False) -> subprocess.CompletedProcess:
    log.info("$ %s", shlex.join(cmd))
    try:
        return subprocess.run(
            cmd, cwd=cwd, check=True, text=not binary,
            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)
    except subprocess.CalledProcessError as exc:
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
        raise BuildError(f"command failed (exit {exc.returncode}): {shlex.join(cmd)}\n{err[-2000:]}") from exc
    except FileNotFoundError as exc:
        raise BuildError(f"tool not found: {cmd[0]}\n{MICROMAMBA_HINT}") from exc


@dataclass
class Context:
    out: Path
    src: Path
    fixture: bool
    force: bool
    build: str
    versions: dict[str, str]
    repo: Path
    runner: Callable[..., subprocess.CompletedProcess] = real_runner

    @property
    def bbox(self) -> BBox:
        return FIXTURE_BBOX if self.fixture else SPEC_BBOX

    @property
    def base_name(self) -> str:
        return "test.pmtiles" if self.fixture else "uk-ie.pmtiles"

    @property
    def incoming(self) -> Path:
        return self.out / ".incoming"

    def version(self, key: str) -> str:
        value = self.versions.get(key, "")
        if not value:
            raise BuildError(f"install/versions.env has no value for {key}")
        return value

    def run(self, cmd: Iterable[object], *, cwd: Path | None = None, capture: bool = False,
            binary: bool = False) -> subprocess.CompletedProcess:
        return self.runner([str(c) for c in cmd], cwd=cwd, capture=capture, binary=binary)

    def output(self, name: str) -> Path:
        return self.out / name

    def stage(self, name: str) -> Path:
        path = self.incoming / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        return path

    def commit(self, name: str) -> Path:
        staged = self.incoming / name
        final = self.out / name
        if not staged.exists():
            raise BuildError(f"nothing staged at {staged}")
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.is_dir():
            shutil.rmtree(final)
        os.replace(staged, final)
        return final

    def write_sidecar(self, name: str, data: dict) -> Path:
        final = self.out / name
        side = sidecar_path(final)
        payload = {
            "output": name,
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "size_bytes": final.stat().st_size if final.is_file() else dir_size(final),
        }
        payload.update(data)
        side.write_text(json.dumps(payload, indent=2) + "\n")
        return side

    def sidecar(self, name: str) -> dict | None:
        side = sidecar_path(self.out / name)
        return json.loads(side.read_text()) if side.exists() else None

    def download(self, url: str, name: str, *, sha256: str | None = None, md5: str | None = None) -> Path:
        dest = self.src / name
        if dest.exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["aria2c", "-x", "8", "-s", "8", "-c", "--auto-file-renaming=false", "--allow-overwrite=true",
               "-d", str(dest.parent), "-o", dest.name]
        if sha256:
            cmd.append(f"--checksum=sha-256={sha256}")
        elif md5:
            cmd.append(f"--checksum=md5={md5}")
        cmd.append(url)
        self.run(cmd)
        if not dest.exists():
            raise BuildError(f"download of {url} did not produce {dest}")
        return dest


def fetch_github_tarball(ctx: Context, owner_repo: str, sha: str) -> Path:
    """Download and unpack https://github.com/<owner>/<repo>/archive/<sha>.tar.gz into the source cache."""
    repo = owner_repo.split("/")[1]
    target = ctx.src / f"{repo}-{sha}"
    if target.is_dir():
        return target
    tgz = ctx.download(f"https://github.com/{owner_repo}/archive/{sha}.tar.gz", f"{repo}-{sha}.tar.gz")
    ctx.run(["tar", "-xzf", str(tgz), "-C", str(ctx.src)])
    if not target.is_dir():
        raise BuildError(f"{tgz.name} did not unpack to {target}")
    return target


def pmtiles_header(ctx: Context, path: Path) -> dict:
    return json.loads(ctx.run(["pmtiles", "show", "--header-json", str(path)], capture=True).stdout)


def pmtiles_metadata(ctx: Context, path: Path) -> dict:
    return json.loads(ctx.run(["pmtiles", "show", "--metadata", str(path)], capture=True).stdout)


def vector_layer_ids(metadata: dict) -> set[str]:
    return {layer["id"] for layer in metadata.get("vector_layers", [])}


def tile_exists(ctx: Context, path: Path, z: int, x: int, y: int) -> bool:
    # `pmtiles tile` writes the tile bytes to stdout and nothing at all (exit 0) for an absent tile.
    proc = ctx.run(["pmtiles", "tile", str(path), str(z), str(x), str(y)], capture=True, binary=True)
    return bool(proc.stdout)


def pmtiles_verify(ctx: Context, path: Path) -> None:
    ctx.run(["pmtiles", "verify", str(path)])


def read_geojsonseq(path: Path) -> list[dict]:
    """osmium's geojsonseq lines start with an RS (0x1e) record separator."""
    features = []
    for line in path.read_text().splitlines():
        line = line.lstrip("\x1e").strip()
        if line:
            features.append(json.loads(line))
    return features


def validate_geojson(obj: object) -> list[str]:
    if not isinstance(obj, dict) or obj.get("type") != "FeatureCollection":
        return ["not a FeatureCollection"]
    problems = []
    features = obj.get("features")
    if not isinstance(features, list):
        return ["features is not a list"]
    for i, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            problems.append(f"feature {i} is not a Feature")
            continue
        geom = feature.get("geometry")
        if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
            problems.append(f"feature {i} has no geometry")
        if not isinstance(feature.get("properties"), dict):
            problems.append(f"feature {i} has no properties object")
    return problems
```

`api/sos/buildmaps.py`:

```python
"""`sos build-maps`: the PC-only map pipeline (spec section 9 and 13; plan 04)."""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from sos.mapbuild.common import (BuildError, Context, MICROMAMBA_HINT, check_tools, log, read_versions,
                                 repo_root)

STEP_IDS = ("base", "os", "contours", "hillshade", "overlays", "places", "packs", "styles", "verify")


def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    return []


def select_steps(ids: list[str] | None) -> list:
    registry = all_steps()
    wanted = list(ids) if ids else list(STEP_IDS)
    known = {step.id for step in registry}
    missing = [i for i in wanted if i not in known]
    if missing:
        raise BuildError(f"step(s) not available: {', '.join(missing)} (registered: {', '.join(sorted(known))})")
    return [step for step in registry if step.id in wanted]


def run_steps(ctx: Context, ids: list[str] | None) -> None:
    for step in select_steps(ids):
        outputs = [ctx.out / name for name in step.outputs(ctx)]
        if outputs and all(p.exists() for p in outputs) and not ctx.force:
            log.info("[%s] up to date, skipping (use --force to rebuild)", step.id)
            continue
        started = time.monotonic()
        log.info("[%s] start", step.id)
        step.run(ctx)
        missing = [str(p) for p in outputs if not p.exists()]
        if missing:
            raise BuildError(f"[{step.id}] did not produce: {', '.join(missing)}")
        log.info("[%s] done in %.0fs", step.id, time.monotonic() - started)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", type=Path, default=None,
                        help="output directory (default ~/sos-content/maps; with --fixture api/tests/fixtures/maps)")
    parser.add_argument("--steps", nargs="+", choices=STEP_IDS, default=None,
                        help="steps to run in registry order (default: all)")
    parser.add_argument("--build", default=None, help="Protomaps build YYYYMMDD (default PROTOMAPS_BUILD from install/versions.env)")
    parser.add_argument("--fixture", action="store_true", help="build the 0.1 degree Southampton fixture instead of the full extract")
    parser.add_argument("--force", action="store_true", help="rebuild steps whose outputs already exist")


def run(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    missing = check_tools()
    if missing:
        print(f"build-maps: missing tools: {', '.join(missing)}\n{MICROMAMBA_HINT}", file=sys.stderr)
        return 2
    try:
        repo = repo_root()
        versions = read_versions(repo / "install" / "versions.env")
        build = args.build or versions.get("PROTOMAPS_BUILD", "")
        if not build:
            raise BuildError("no Protomaps build: pass --build YYYYMMDD or set PROTOMAPS_BUILD in install/versions.env")
        default_out = repo / "api" / "tests" / "fixtures" / "maps" if args.fixture else Path.home() / "sos-content" / "maps"
        out = Path(args.out).resolve() if args.out else default_out
        src = Path(os.environ.get("SOS_MAPS_SRC") or Path.home() / "sos-content" / "maps-src")
        out.mkdir(parents=True, exist_ok=True)
        src.mkdir(parents=True, exist_ok=True)
        ctx = Context(out=out, src=src, fixture=args.fixture, force=args.force, build=build, versions=versions, repo=repo)
        log.info("build-maps out=%s src=%s fixture=%s build=%s", out, src, args.fixture, build)
        run_steps(ctx, args.steps)
    except BuildError as exc:
        print(f"build-maps: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sos build-maps")
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
```

Wire the CLI in `api/sos/cli.py`: find plan 01's `build-maps` subparser (it prints "not implemented") and replace it with:

```python
from sos import buildmaps

build_maps = subparsers.add_parser("build-maps", help="PC only: build map tiles, styles, overlays, places and phone packs")
buildmaps.add_arguments(build_maps)
build_maps.set_defaults(func=buildmaps.run)
```

(`cli.main` dispatches `args.func(args)` and exits with its return code; keep plan 01's dispatch convention if it differs, but the subcommand must accept exactly `--out --steps --build --fixture --force`.)

`api/pyproject.toml`: add the PC-only extra.

```toml
[project.optional-dependencies]
maps = ["pyproj>=3.6"]
```

`install/versions.env`: append this block (create the file with only this block if plan 01 has not landed yet; plan 01's block goes above it when it does).

```bash
# --- maps pipeline (plan 04) ---
PROTOMAPS_BUILD=20260902
PROTOMAPS_BUILDS_BASE=https://build.protomaps.com
PROTOMAPS_BASEMAPS_NPM=5.7.2
BASEMAPS_ASSETS_COMMIT=028c18f713baecad011301ff7a69acc39bcc2ae7
OS_ZOOMSTACK_STYLES_COMMIT=d23143b4a36435680eda99b4febb3187398f594f
OS_DOWNLOADS_API=https://api.os.uk/downloads/v1
GEOFABRIK_PBF_URL=https://download.geofabrik.de/europe/britain-and-ireland-latest.osm.pbf
GEOFABRIK_FIXTURE_PBF_URL=https://download.geofabrik.de/europe/united-kingdom/england/hampshire-latest.osm.pbf
COPERNICUS_DEM_BASE=https://copernicus-dem-30m.s3.amazonaws.com
# OSNI Open Data 50 m DTM (Irish Grid). Blank: Northern Ireland relief comes from Copernicus GLO-30 with a warning.
OSNI_DTM_URL=
ORGANICMAPS_TAG=2026.08.27-18-android
ORGANICMAPS_CDN=https://cdn.organicmaps.app/maps
ORGANICMAPS_APK_URL=https://github.com/organicmaps/organicmaps/releases/download/2026.08.27-18-android/OrganicMaps-26082718-web-release.apk
ORGANICMAPS_APK_SHA256=1f19229d95b731862349d504b150dad63eb405caa83e98c96bfe93b7acae3c7a
# Vector sources for ogr2ogr: a URL ending .zip (GPKG or GeoJSON inside), a GeoJSON/GPKG URL, or an ArcGIS
# FeatureServer layer URL (.../FeatureServer/<n>). Append |<layer> to name a layer. Blank: region skipped.
FLOOD_EN_URL=
FLOOD_WA_URL=
FLOOD_SC_URL=
FLOOD_NI_URL=
FLOOD_IE_URL=
ACCESS_EN_URL=https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/CRoW_Act_2000_Access_Layer/FeatureServer/0
ACCESS_WA_URL=
```

`.gitignore`: append.

```gitignore
# maps pipeline (plan 04): scratch, and exceptions so the committed fixture outputs survive the *.pmtiles / *.pbf rules
.incoming/
*.apk
*.fgb
*.vrt
*.asc
*.osm.pbf
!api/tests/fixtures/maps/*.pmtiles
!api/tests/fixtures/maps/overlays/*.pmtiles
!api/tests/fixtures/maps/fonts/**/*.pbf
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && pip install -e '.[maps]' >/dev/null && python -m pytest tests/test_buildmaps_cli.py -v 2>&1 | tail -25`
Expected: `18 passed` (every test in the file, including `test_cli_exposes_build_maps`).

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/buildmaps.py api/sos/mapbuild/__init__.py api/sos/mapbuild/common.py api/sos/cli.py api/pyproject.toml \
        api/tests/__init__.py api/tests/mapbuild_helpers.py api/tests/test_buildmaps_cli.py install/versions.env .gitignore
git commit -m "feat(maps): build-maps CLI skeleton with staging, tool check and step registry"
```

---

### Task 2: Step `base` — Protomaps extract with bbox, zoom and probe-tile verification

**Files:**
- Create: `api/sos/mapbuild/base.py`
- Create: `api/tests/test_buildmaps_base.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `Context`, `bbox_str`, `lonlat_to_tile`, `pmtiles_header`, `tile_exists`, `BuildError` (Task 1).
- Produces: `sos.mapbuild.base.BaseStep` (`id == "base"`, outputs `[ctx.base_name]`), `build_url(ctx) -> str`, `extract_command(ctx, url, out_path) -> list[str]`, `check_base(header, bbox, probes, has_tile, *, maxzoom=15) -> list[str]`, `PROBES_FULL`, `PROBES_FIXTURE`, `PROBE_ZOOM = 12`. Sidecar `<base>.json` carries `step, source, build, bbox, header`. Task 10's verify step reuses `check_base` and the probe tables.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_buildmaps_base.py`:

```python
import json

import pytest

from sos.mapbuild import base
from sos.mapbuild.base import BaseStep, check_base, extract_command, PROBES_FULL, PROBES_FIXTURE
from sos.mapbuild.common import BuildError, SPEC_BBOX, FIXTURE_BBOX
from tests.mapbuild_helpers import FakeRunner, make_ctx

FULL_HEADER = {"tile_compression": "gzip", "tile_type": "mvt", "minzoom": 0, "maxzoom": 15,
               "bounds": [-11.0, 49.1, 2.2, 61.2], "center": [-4.4, 55.15, 0]}
FIXTURE_HEADER = {"tile_compression": "gzip", "tile_type": "mvt", "minzoom": 0, "maxzoom": 15,
                  "bounds": [-1.56, 50.87, -1.46, 50.97], "center": [-1.51, 50.92, 0]}


def test_check_base_passes_on_good_header():
    assert check_base(FULL_HEADER, SPEC_BBOX, PROBES_FULL, lambda z, x, y: True) == []


def test_check_base_reports_missing_probe_tile():
    missing_st_helier = lambda z, x, y: (z, x, y) != (12, 2023, 1403)
    problems = check_base(FULL_HEADER, SPEC_BBOX, PROBES_FULL, missing_st_helier)
    assert len(problems) == 1 and "St Helier" in problems[0] and "z12" in problems[0]


def test_check_base_reports_short_bbox_wrong_zoom_and_tile_type():
    header = dict(FULL_HEADER, bounds=[-11.0, 49.5, 2.2, 61.2], maxzoom=14, tile_type="png")
    problems = check_base(header, SPEC_BBOX, {}, lambda z, x, y: True)
    assert any("49.5" in p for p in problems)
    assert any("maxzoom 14" in p for p in problems)
    assert any("tile type" in p for p in problems)
    assert len(problems) == 3


def test_extract_command_is_the_spec_command(tmp_path):
    ctx = make_ctx(tmp_path, fixture=False)
    cmd = extract_command(ctx, base.build_url(ctx), tmp_path / "uk-ie.pmtiles")
    assert cmd == ["pmtiles", "extract", "https://build.protomaps.com/20260902.pmtiles", str(tmp_path / "uk-ie.pmtiles"),
                   "--bbox=-11,49.1,2.2,61.2", "--download-threads=8"]


def test_base_step_extracts_verifies_commits_and_writes_sidecar(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"},
                        files={"test.pmtiles": b"PMTiles"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    BaseStep().run(ctx)
    extract = runner.find("pmtiles", "extract")[0]
    assert extract[3] == str(ctx.incoming / "test.pmtiles")
    assert "--bbox=-1.56,50.87,-1.46,50.97" in extract
    assert (ctx.out / "test.pmtiles").read_bytes() == b"PMTiles"
    assert not (ctx.incoming / "test.pmtiles").exists()
    probes = runner.find("pmtiles", "tile")
    assert probes == [["pmtiles", "tile", str(ctx.incoming / "test.pmtiles"), "12", "2031", "1372"]]  # OS HQ at z12
    side = json.loads((ctx.out / "test.json").read_text())
    assert side["build"] == "20260902" and side["bbox"] == list(FIXTURE_BBOX) and side["header"]["maxzoom"] == 15
    assert side["source"] == "https://build.protomaps.com/20260902.pmtiles"


def test_base_step_fails_and_leaves_nothing_when_probe_missing(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b""},
                        files={"test.pmtiles": b"PMTiles"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    with pytest.raises(BuildError, match="OS HQ"):
        BaseStep().run(ctx)
    assert not (ctx.out / "test.pmtiles").exists()


def test_full_mode_probes_st_helier_and_lerwick(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FULL_HEADER), "pmtiles tile": b"\x1f\x8b"},
                        files={"uk-ie.pmtiles": b"PMTiles"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    BaseStep().run(ctx)
    probed = {tuple(c[-3:]) for c in runner.find("pmtiles", "tile")}
    assert probed == {("12", "2023", "1403"), ("12", "2034", "1186")}
    assert set(PROBES_FULL) == {"St Helier", "Lerwick"} and set(PROBES_FIXTURE) == {"OS HQ Southampton"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_base.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.base'`.

- [ ] **Step 3: Implement `base.py` and register the step**

`api/sos/mapbuild/base.py`:

```python
"""Step `base`: extract the pinned Protomaps build over the UK and Ireland bbox and verify it."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .common import BBox, BuildError, Context, bbox_str, lonlat_to_tile, pmtiles_header, tile_exists

PROBES_FULL: dict[str, tuple[float, float]] = {"St Helier": (49.19, -2.11), "Lerwick": (60.15, -1.15)}
PROBES_FIXTURE: dict[str, tuple[float, float]] = {"OS HQ Southampton": (50.9379, -1.4708)}
PROBE_ZOOM = 12
BASE_MAXZOOM = 15


def build_url(ctx: Context) -> str:
    return f"{ctx.version('PROTOMAPS_BUILDS_BASE')}/{ctx.build}.pmtiles"


def extract_command(ctx: Context, url: str, out_path: Path) -> list[str]:
    return ["pmtiles", "extract", url, str(out_path), f"--bbox={bbox_str(ctx.bbox)}", "--download-threads=8"]


def check_base(header: dict, bbox: BBox, probes: dict[str, tuple[float, float]],
               has_tile: Callable[[int, int, int], bool], *, maxzoom: int = BASE_MAXZOOM) -> list[str]:
    problems: list[str] = []
    bounds = header.get("bounds") or []
    eps = 1e-6
    covers = (len(bounds) == 4 and bounds[0] <= bbox[0] + eps and bounds[1] <= bbox[1] + eps
              and bounds[2] >= bbox[2] - eps and bounds[3] >= bbox[3] - eps)
    if not covers:
        problems.append(f"bounds {bounds} do not cover {list(bbox)}")
    if header.get("maxzoom") != maxzoom:
        problems.append(f"maxzoom {header.get('maxzoom')} is not {maxzoom}")
    if header.get("tile_type") != "mvt":
        problems.append(f"tile type {header.get('tile_type')!r} is not mvt")
    for name, (lat, lon) in probes.items():
        x, y = lonlat_to_tile(lat, lon, PROBE_ZOOM)
        if not has_tile(PROBE_ZOOM, x, y):
            problems.append(f"no z{PROBE_ZOOM} tile covering {name} ({lat}, {lon}) at {x}/{y}")
    return problems


class BaseStep:
    id = "base"

    def outputs(self, ctx: Context) -> list[str]:
        return [ctx.base_name]

    def run(self, ctx: Context) -> None:
        staged = ctx.stage(ctx.base_name)
        url = build_url(ctx)
        ctx.run(extract_command(ctx, url, staged))
        header = pmtiles_header(ctx, staged)
        probes = PROBES_FIXTURE if ctx.fixture else PROBES_FULL
        problems = check_base(header, ctx.bbox, probes, lambda z, x, y: tile_exists(ctx, staged, z, x, y))
        if problems:
            raise BuildError("base map failed verification:\n  " + "\n  ".join(problems))
        ctx.commit(ctx.base_name)
        ctx.write_sidecar(ctx.base_name, {"step": self.id, "source": url, "build": ctx.build,
                                          "bbox": list(ctx.bbox), "header": header})
```

`api/sos/buildmaps.py` — replace `all_steps`:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    return [BaseStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_base.py tests/test_buildmaps_cli.py -q 2>&1 | tail -3`
Expected: `25 passed`.

- [ ] **Step 5: Smoke the real command against the fixture bbox (network, about 15 seconds)**

Run:

```bash
export PATH=$HOME/.local/bin:$PATH
export MAMBA_ROOT_PREFIX=$HOME/micromamba; eval "$(micromamba shell hook -s bash)"; micromamba activate sos-maps
cd /home/dan/OperationSOS/api && SOS_MAPS_SRC=/tmp/sos-maps-src sos build-maps --fixture --steps base --out /tmp/sos-maps-smoke
ls -la /tmp/sos-maps-smoke && python -c "import json; print(json.load(open('/tmp/sos-maps-smoke/test.json'))['header'])"
```

Expected: log lines `[base] start`, `$ pmtiles extract https://build.protomaps.com/20260902.pmtiles ... --bbox=-1.56,50.87,-1.46,50.97 --download-threads=8`, `[base] done in ...s`; `test.pmtiles` about 4.9 MB and `test.json`; the printed header has `'maxzoom': 15` and `'bounds': [-1.56, 50.87, -1.46, 50.97]`.

- [ ] **Step 6: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/base.py api/sos/buildmaps.py api/tests/test_buildmaps_base.py
git commit -m "feat(maps): base step extracts the pinned Protomaps build and verifies bbox, zoom and probe tiles"
```

---

### Task 3: Step `styles` — Protomaps styles via Node, OS styles rewritten, sprites and glyphs vendored

**Files:**
- Create: `tools/map-styles/package.json`
- Create: `tools/map-styles/pnpm-lock.yaml` (generated by `pnpm install`, committed)
- Create: `tools/map-styles/build-styles.mjs`
- Create: `tools/map-styles/build-styles.test.mjs`
- Create: `tools/map-styles/layers/contours.json`, `hillshade.json`, `footpaths.json`, `flood-zones.json`, `overlays.json`
- Create: `api/sos/mapbuild/styles.py`
- Create: `api/tests/test_buildmaps_styles.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)
- Modify: `Makefile` (`test` target runs `node --test` in `tools/map-styles`)

**Interfaces:**
- Consumes: `Context`, `fetch_github_tarball`, `pmtiles_metadata`, `vector_layer_ids` (Task 1); `os-zoomstack.pmtiles` (Task 4, must exist before this step runs); `contours.json` sidecar `height_field` (Task 5, optional); `overlays/index.json` (Task 7, optional).
- Produces: `sos.mapbuild.styles.StylesStep` (`id == "styles"`), `rewrite_os_style(style, *, tiles_url=..., sprite=..., glyphs=...) -> dict`, `missing_source_layers(style, present) -> set[str]`, `style_fonts(style) -> set[str]`, `vendor_glyphs(src_fonts, dest, faces, ranges=None) -> int`, `vendor_sprites(src, dest, names) -> int`, `style_index(base_name) -> dict`, `render_layer_fragment(text, *, height_field) -> str`, `prune_overlay_fragment(fragment, kinds) -> dict`, constants `NOTO_FACES`, `OS_FACES`, `FIXTURE_GLYPH_RANGES`, `GLYPHS_URL`, `OS_TILES_URL`, `OS_SPRITE`, `FRAGMENTS`. Node: `buildAll(tilesUrl) -> [[file, style], ...]`, `buildStyle(spec, tilesUrl)`, `VAULT`, `STYLES`, `GLYPHS`.
- Output contract for the frontend (plan 02) and the map router (plan 01): `styles/index.json` is `{"osm": {"vault", "field", "blackout", "tiles"}, "os": {...}, "layers": {"contours", "hillshade", "footpaths", "flood-zones", "overlays"}}` with `/maps/...` URLs; every layer fragment is `{"sources": {...}, "layers": [...]}`.

- [ ] **Step 1: Write the failing Node test and the Python tests**

`tools/map-styles/build-styles.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import { buildAll, GLYPHS, VAULT, STYLES } from "./build-styles.mjs";

const NOTO = new Set(["Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic"]);

test("three styles are generated in the expected order", () => {
  assert.deepEqual(buildAll("pmtiles:///maps/uk-ie.pmtiles").map(([file]) => file),
    ["osm-light.json", "osm-dark.json", "osm-vault.json"]);
});

test("every generated style is a valid MapLibre style that only references local assets", () => {
  for (const [file, style] of buildAll("pmtiles:///maps/test.pmtiles")) {
    const errors = validateStyleMin(style);
    assert.deepEqual(errors, [], `${file}: ${errors.map((e) => e.message).join("; ")}`);
    assert.equal(style.version, 8);
    assert.deepEqual(Object.keys(style.sources), ["protomaps"]);
    assert.equal(style.sources.protomaps.url, "pmtiles:///maps/test.pmtiles");
    assert.equal(style.glyphs, GLYPHS);
    assert.match(style.sprite, /^\/maps\/sprites\/v4\/(light|dark)$/);
    assert.ok(style.layers.length > 50, `${file} has only ${style.layers.length} layers`);
    for (const layer of style.layers) {
      if (layer.type !== "background") assert.equal(layer.source, "protomaps", `${file}/${layer.id}`);
      const font = layer.layout?.["text-font"];
      if (font) for (const face of font) assert.ok(NOTO.has(face), `${file}/${layer.id} uses ${face}`);
    }
    assert.doesNotMatch(JSON.stringify(style), /https?:\/\//, `${file} contains an external URL`);
  }
});

test("vault flavour is dark-based with the phosphor palette and Noto fonts", () => {
  assert.equal(VAULT.background, "#05090a");
  assert.equal(VAULT.regular, "Noto Sans Regular");
  const vault = STYLES.find((s) => s.file === "osm-vault.json");
  assert.equal(vault.sprite, "/maps/sprites/v4/dark");
});
```

`api/tests/test_buildmaps_styles.py`:

```python
import json
from pathlib import Path

import pytest

from sos.mapbuild import styles
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx, REPO

OS_LAYERS = ["airports", "boundaries", "buildings", "contours", "etl", "foreshore", "greenspaces", "names",
             "national_parks", "rail", "railwaystations", "roads", "sea", "sites", "surfacewater", "urban_areas",
             "waterlines", "woodland"]

OS_STYLE = {
    "version": 8, "name": "OS Open Zoomstack - Outdoor", "id": "cjqzn7wul164r2ro6u6awxepx", "owner": "ordnancesurvey",
    "created": "2019-01-16T20:32:55.069Z", "modified": "2019-02-04T10:17:59.178Z", "visibility": "public", "draft": False,
    "sources": {"composite": {"url": "mapbox://ADD-SOURCE-URL-HERE", "type": "vector"}},
    "sprite": "mapbox://sprites/ordnancesurvey/cjqzn7wul164r2ro6u6awxepx",
    "glyphs": "mapbox://fonts/ordnancesurvey/{fontstack}/{range}.pbf",
    "layers": [
        {"id": "background", "type": "background", "paint": {"background-color": "#f5f5f0"}},
        {"id": "sea", "type": "fill", "source": "composite", "source-layer": "sea", "paint": {"fill-color": "#cde"}},
        {"id": "road numbers", "type": "symbol", "source": "composite", "source-layer": "roads",
         "layout": {"text-field": ["get", "number"], "text-font": ["Source Sans Pro Regular", "Arial Unicode MS Regular"]}},
        {"id": "names", "type": "symbol", "source": "composite", "source-layer": "names",
         "layout": {"text-field": ["get", "name"], "text-font": ["Source Sans Pro Bold", "Arial Unicode MS Regular"]}},
    ],
}


def test_rewrite_os_style_applies_the_spec_transformation():
    before = json.dumps(OS_STYLE)
    new = styles.rewrite_os_style(OS_STYLE)
    assert json.dumps(OS_STYLE) == before, "input must not be mutated"
    assert new["sources"] == {"os": {"type": "vector", "url": "pmtiles:///maps/os-zoomstack.pmtiles",
                                     "attribution": styles.OS_ATTRIBUTION}}
    assert new["sprite"] == "/maps/sprites/os/sprites"
    assert new["glyphs"] == "/maps/fonts/{fontstack}/{range}.pbf"
    assert "source" not in new["layers"][0]
    assert all(layer["source"] == "os" for layer in new["layers"][1:])
    assert new["layers"][2]["layout"]["text-font"] == ["Source Sans Pro Regular"]
    assert new["layers"][3]["layout"]["text-font"] == ["Source Sans Pro Bold"]
    for key in ("created", "modified", "owner", "id", "visibility", "draft"):
        assert key not in new
    assert new["name"] == "OS Open Zoomstack - Outdoor" and new["version"] == 8


def test_missing_source_layers_and_style_fonts():
    assert styles.missing_source_layers(OS_STYLE, set(OS_LAYERS)) == set()
    assert styles.missing_source_layers(OS_STYLE, {"sea", "roads"}) == {"names"}
    assert styles.style_fonts(styles.rewrite_os_style(OS_STYLE)) == {"Source Sans Pro Regular", "Source Sans Pro Bold"}


def test_vendor_glyphs_copies_ranges_and_fails_on_missing_face(tmp_path):
    src = tmp_path / "fonts"
    for face in ("Noto Sans Regular", "Noto Sans Medium"):
        (src / face).mkdir(parents=True)
        for rng in ("0-255", "256-511", "512-767"):
            (src / face / f"{rng}.pbf").write_bytes(b"g")
    dest = tmp_path / "out"
    assert styles.vendor_glyphs(src, dest, ("Noto Sans Regular",), ("0-255", "256-511")) == 2
    assert sorted(p.name for p in (dest / "Noto Sans Regular").iterdir()) == ["0-255.pbf", "256-511.pbf"]
    assert styles.vendor_glyphs(src, dest, ("Noto Sans Medium",)) == 3
    with pytest.raises(BuildError, match="Noto Sans Italic"):
        styles.vendor_glyphs(src, dest, ("Noto Sans Italic",))


def test_vendor_sprites_copies_only_named_sets(tmp_path):
    src = tmp_path / "v4"
    src.mkdir()
    for name in ("light.json", "light.png", "light@2x.json", "light@2x.png", "dark.json", "dark.png", "white.json"):
        (src / name).write_bytes(b"s")
    dest = tmp_path / "sprites"
    assert styles.vendor_sprites(src, dest, ("light", "dark")) == 6
    assert not (dest / "white.json").exists()
    with pytest.raises(BuildError):
        styles.vendor_sprites(src, dest, ("grayscale",))


def test_style_index_and_fragment_rendering():
    index = styles.style_index("test.pmtiles")
    assert index["osm"] == {"vault": "/maps/styles/osm-vault.json", "field": "/maps/styles/osm-light.json",
                            "blackout": "/maps/styles/osm-dark.json", "tiles": "/maps/test.pmtiles"}
    assert index["os"]["field"] == "/maps/styles/os-outdoor.json" and index["os"]["blackout"] == "/maps/styles/os-night.json"
    assert index["os"]["tiles"] == "/maps/os-zoomstack.pmtiles"
    assert set(index["layers"]) == set(styles.FRAGMENTS)
    text = (REPO / "tools/map-styles/layers/contours.json").read_text()
    rendered = json.loads(styles.render_layer_fragment(text, height_field="PROP_VALUE"))
    assert "__HEIGHT__" not in json.dumps(rendered)
    assert json.dumps(["get", "PROP_VALUE"]) in json.dumps(rendered)


def test_every_fragment_is_a_sources_layers_object_with_local_urls():
    for name in styles.FRAGMENTS:
        frag = json.loads((REPO / "tools/map-styles/layers" / f"{name}.json").read_text())
        assert set(frag) == {"sources", "layers"}
        for source in frag["sources"].values():
            assert source["url"].startswith("pmtiles:///maps/")
        for layer in frag["layers"]:
            assert layer["source"] in frag["sources"]


def test_prune_overlay_fragment_keeps_only_pmtiles_overlays():
    frag = json.loads((REPO / "tools/map-styles/layers/overlays.json").read_text())
    pruned = styles.prune_overlay_fragment(frag, {"water": "pmtiles", "airports-military": "geojson", "access-land": "geojson"})
    assert set(pruned["sources"]) == {"water"}
    assert {layer["source"] for layer in pruned["layers"]} == {"water"}


def _fake_assets(ctx, sha_assets, sha_os):
    assets = ctx.src / f"basemaps-assets-{sha_assets}"
    for name in ("light.json", "light.png", "light@2x.json", "light@2x.png", "dark.json", "dark.png", "dark@2x.json", "dark@2x.png"):
        (assets / "sprites" / "v4").mkdir(parents=True, exist_ok=True)
        (assets / "sprites" / "v4" / name).write_bytes(b"s")
    for face in styles.NOTO_FACES:
        (assets / "fonts" / face).mkdir(parents=True)
        for rng in ("0-255", "256-511", "512-767"):
            (assets / "fonts" / face / f"{rng}.pbf").write_bytes(b"g")
    gl = ctx.src / f"OS-Open-Zoomstack-Stylesheets-{sha_os}" / "Vector Tiles" / "Mapbox GL Styles"
    (gl / "sprites").mkdir(parents=True)
    for name in ("sprites.json", "sprites.png", "sprites@2x.json", "sprites@2x.png"):
        (gl / "sprites" / name).write_bytes(b"s")
    for face in styles.OS_FACES:
        (gl / "fonts" / face).mkdir(parents=True)
        for rng in ("0-255", "256-511"):
            (gl / "fonts" / face / f"{rng}.pbf").write_bytes(b"g")
    (gl / "OS Open Zoomstack - Outdoor.json").write_text(json.dumps(OS_STYLE))
    (gl / "OS Open Zoomstack - Night.json").write_text(json.dumps(dict(OS_STYLE, name="OS Open Zoomstack - Night")))


def _fake_node(cmd):
    out = Path(cmd[cmd.index("--out") + 1])
    out.mkdir(parents=True, exist_ok=True)
    tiles = cmd[cmd.index("--tiles") + 1]
    for name in ("osm-light.json", "osm-dark.json", "osm-vault.json"):
        (out / name).write_text(json.dumps({"version": 8, "sources": {"protomaps": {"type": "vector", "url": tiles}},
                                            "sprite": "/maps/sprites/v4/light", "glyphs": styles.GLYPHS_URL,
                                            "layers": [{"id": "l", "type": "symbol", "source": "protomaps", "source-layer": "places",
                                                        "layout": {"text-font": ["Noto Sans Regular"]}}]}))
    return ""


def test_styles_step_generates_rewrites_vendors_and_indexes(tmp_path):
    runner = FakeRunner(outputs={"node build-styles.mjs": _fake_node,
                                 "pmtiles show": json.dumps({"vector_layers": [{"id": l, "fields": {}} for l in OS_LAYERS]})})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    sha_assets, sha_os = ctx.version("BASEMAPS_ASSETS_COMMIT"), ctx.version("OS_ZOOMSTACK_STYLES_COMMIT")
    _fake_assets(ctx, sha_assets, sha_os)
    (ctx.out / "os-zoomstack.pmtiles").write_bytes(b"pm")
    (ctx.out / "contours.json").write_text(json.dumps({"output": "contours.pmtiles", "height_field": "PROP_VALUE"}))
    (ctx.out / "overlays").mkdir()
    (ctx.out / "overlays" / "index.json").write_text(json.dumps({"water": {"kind": "pmtiles", "file": "overlays/water.pmtiles"},
                                                                 "airports-military": {"kind": "geojson", "file": "overlays/airports-military.geojson"}}))
    styles.StylesStep().run(ctx)
    tools = REPO / "tools" / "map-styles"
    assert runner.find("pnpm", "install")[0] == ["pnpm", "install", "--frozen-lockfile"]
    node = runner.find("node", "build-styles.mjs")[0]
    assert node[node.index("--tiles") + 1] == "pmtiles:///maps/test.pmtiles"
    assert node[node.index("--out") + 1] == str(ctx.incoming / "styles")
    assert not runner.find("aria2c"), "assets already in the cache must not be downloaded"
    out = ctx.out
    assert json.loads((out / "styles" / "index.json").read_text())["osm"]["tiles"] == "/maps/test.pmtiles"
    outdoor = json.loads((out / "styles" / "os-outdoor.json").read_text())
    assert outdoor["sources"]["os"]["url"] == "pmtiles:///maps/os-zoomstack.pmtiles"
    assert (out / "styles" / "os-night.json").exists() and (out / "styles" / "osm-vault.json").exists()
    contours = json.loads((out / "styles" / "layers" / "contours.json").read_text())
    assert "PROP_VALUE" in json.dumps(contours)
    overlays = json.loads((out / "styles" / "layers" / "overlays.json").read_text())
    assert set(overlays["sources"]) == {"water"}
    assert sorted(p.name for p in (out / "fonts" / "Noto Sans Regular").iterdir()) == ["0-255.pbf", "256-511.pbf"]
    assert (out / "fonts" / "Source Sans Pro SemiBold" / "0-255.pbf").exists()
    assert (out / "sprites" / "v4" / "dark@2x.png").exists() and (out / "sprites" / "os" / "sprites@2x.json").exists()
    assert not (ctx.incoming / "styles").exists()
    side = json.loads((out / "styles.json").read_text())
    assert side["glyph_faces"] == sorted(styles.NOTO_FACES + styles.OS_FACES) and side["fixture_ranges"] == list(styles.FIXTURE_GLYPH_RANGES)


def test_styles_step_fails_on_missing_source_layer(tmp_path):
    runner = FakeRunner(outputs={"node build-styles.mjs": _fake_node,
                                 "pmtiles show": json.dumps({"vector_layers": [{"id": "sea", "fields": {}}, {"id": "roads", "fields": {}}]})})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    _fake_assets(ctx, ctx.version("BASEMAPS_ASSETS_COMMIT"), ctx.version("OS_ZOOMSTACK_STYLES_COMMIT"))
    (ctx.out / "os-zoomstack.pmtiles").write_bytes(b"pm")
    with pytest.raises(BuildError, match="names"):
        styles.StylesStep().run(ctx)


def test_styles_step_requires_os_archive(tmp_path):
    ctx = make_ctx(tmp_path)
    with pytest.raises(BuildError, match="os-zoomstack.pmtiles"):
        styles.StylesStep().run(ctx)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_styles.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.styles'`.

Run: `cd /home/dan/OperationSOS/tools/map-styles 2>/dev/null && node --test; echo "exit=$?"`
Expected: the directory does not exist yet, so `exit=1` (or `Cannot find module` once the test file exists).

- [ ] **Step 3: Create the Node package, generator, fragments, and `styles.py`**

`tools/map-styles/package.json`:

```json
{
  "name": "sos-map-styles",
  "private": true,
  "type": "module",
  "description": "Operation SOS map styles: Protomaps flavours, MapLibre layer fragments, osmium export configs and site lists",
  "scripts": {
    "build": "node build-styles.mjs",
    "test": "node --test"
  },
  "dependencies": {
    "@protomaps/basemaps": "5.7.2"
  },
  "devDependencies": {
    "@maplibre/maplibre-gl-style-spec": "26.4.1"
  }
}
```

Run `cd /home/dan/OperationSOS/tools/map-styles && pnpm install` once to create `pnpm-lock.yaml` (committed) and `node_modules/` (ignored).

`tools/map-styles/build-styles.mjs`:

```js
// Generates the three Protomaps styles used by the "osm" base: light (Field theme), dark (Blackout) and
// the custom Vault flavour. Usage: node build-styles.mjs --out DIR [--tiles pmtiles:///maps/uk-ie.pmtiles]
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { layers, namedFlavor } from "@protomaps/basemaps";

export const GLYPHS = "/maps/fonts/{fontstack}/{range}.pbf";
export const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; Protomaps';
const FONTS = { regular: "Noto Sans Regular", bold: "Noto Sans Medium", italic: "Noto Sans Italic" };

// Vault: phosphor green on near-black with an amber highway accent (spec section 11 themes).
export const VAULT = {
  ...namedFlavor("dark"),
  background: "#05090a",
  earth: "#0c1410",
  water: "#062a2a",
  park_a: "#0f2416",
  park_b: "#123019",
  wood_a: "#0f2416",
  wood_b: "#123019",
  scrub_a: "#0e1f14",
  scrub_b: "#11261a",
  buildings: "#16221b",
  hospital: "#2a1d10",
  industrial: "#1a1f1d",
  school: "#1e2417",
  pedestrian: "#14201a",
  sand: "#1d2417",
  beach: "#1d2417",
  glacier: "#1a2a2a",
  aerodrome: "#161d19",
  runway: "#2a3a2f",
  military: "#241c1c",
  zoo: "#1a2617",
  pier: "#1c2a24",
  minor_service: "#20342a",
  minor_a: "#254131",
  minor_b: "#254131",
  link: "#2e4d3a",
  major: "#37603f",
  highway: "#c58a1a",
  other: "#1f2d26",
  minor_service_casing: "#0a120d",
  minor_casing: "#0a120d",
  link_casing: "#0a120d",
  major_casing_early: "#0a120d",
  major_casing_late: "#0a120d",
  highway_casing_early: "#3a2a08",
  highway_casing_late: "#3a2a08",
  railway: "#3a4d42",
  boundaries: "#5b7a63",
  roads_label_minor: "#8ee6a0",
  roads_label_minor_halo: "#05090a",
  roads_label_major: "#b8ffc4",
  roads_label_major_halo: "#05090a",
  ocean_label: "#4fb3a9",
  subplace_label: "#9be7a8",
  subplace_label_halo: "#05090a",
  city_label: "#d5ffd9",
  city_label_halo: "#05090a",
  state_label: "#7cc58a",
  state_label_halo: "#05090a",
  country_label: "#a6f0b0",
  address_label: "#8ee6a0",
  address_label_halo: "#05090a",
  ...FONTS,
};

export const STYLES = [
  { file: "osm-light.json", name: "SOS Field (Protomaps light)", flavor: { ...namedFlavor("light"), ...FONTS }, sprite: "/maps/sprites/v4/light" },
  { file: "osm-dark.json", name: "SOS Blackout (Protomaps dark)", flavor: { ...namedFlavor("dark"), ...FONTS }, sprite: "/maps/sprites/v4/dark" },
  { file: "osm-vault.json", name: "SOS Vault (Protomaps custom)", flavor: VAULT, sprite: "/maps/sprites/v4/dark" },
];

export function buildStyle({ name, flavor, sprite }, tilesUrl) {
  return {
    version: 8,
    name,
    sources: { protomaps: { type: "vector", url: tilesUrl, attribution: ATTRIBUTION } },
    sprite,
    glyphs: GLYPHS,
    layers: layers("protomaps", flavor, { lang: "en" }),
  };
}

export function buildAll(tilesUrl) {
  return STYLES.map((spec) => [spec.file, buildStyle(spec, tilesUrl)]);
}

function parseArgs(argv) {
  const args = { out: null, tiles: "pmtiles:///maps/uk-ie.pmtiles" };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--out") args.out = argv[++i];
    else if (argv[i] === "--tiles") args.tiles = argv[++i];
    else throw new Error(`unknown argument ${argv[i]}`);
  }
  if (!args.out) throw new Error("--out DIR is required");
  return args;
}

export function main(argv) {
  const args = parseArgs(argv);
  mkdirSync(args.out, { recursive: true });
  for (const [file, style] of buildAll(args.tiles)) {
    writeFileSync(join(args.out, file), `${JSON.stringify(style, null, 1)}\n`);
    console.log(`wrote ${file} (${style.layers.length} layers)`);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main(process.argv.slice(2));
```

`tools/map-styles/layers/contours.json` (`__HEIGHT__` is replaced by the height attribute found in the OS tiles):

```json
{
  "sources": {"contours": {"type": "vector", "url": "pmtiles:///maps/contours.pmtiles"}},
  "layers": [
    {"id": "contours-line", "type": "line", "source": "contours", "source-layer": "contour_line", "minzoom": 11,
     "paint": {"line-color": "#b5651d", "line-opacity": 0.55,
               "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.4, 15, 0.9]}},
    {"id": "contours-index", "type": "line", "source": "contours", "source-layer": "contour_line", "minzoom": 11,
     "filter": ["==", ["%", ["to-number", ["get", "__HEIGHT__"]], 50], 0],
     "paint": {"line-color": "#b5651d", "line-opacity": 0.85,
               "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.8, 15, 1.6]}},
    {"id": "contours-label", "type": "symbol", "source": "contours", "source-layer": "contour_line", "minzoom": 13,
     "filter": ["==", ["%", ["to-number", ["get", "__HEIGHT__"]], 50], 0],
     "layout": {"symbol-placement": "line", "text-field": ["to-string", ["get", "__HEIGHT__"]],
                "text-font": ["Noto Sans Regular"], "text-size": 10, "text-max-angle": 30},
     "paint": {"text-color": "#8a4a12", "text-halo-color": "#ffffff", "text-halo-width": 1}}
  ]
}
```

`tools/map-styles/layers/hillshade.json`:

```json
{
  "sources": {"hillshade": {"type": "raster", "url": "pmtiles:///maps/hillshade.pmtiles", "tileSize": 256}},
  "layers": [
    {"id": "hillshade", "type": "raster", "source": "hillshade",
     "paint": {"raster-opacity": 0.35, "raster-resampling": "linear"}}
  ]
}
```

`tools/map-styles/layers/footpaths.json` (designated rights of way from z10, everything else from z13; colour by `designation`):

```json
{
  "sources": {"footpaths": {"type": "vector", "url": "pmtiles:///maps/overlays/footpaths.pmtiles"}},
  "layers": [
    {"id": "footpaths-other", "type": "line", "source": "footpaths", "source-layer": "footpaths", "minzoom": 13,
     "filter": ["!", ["has", "designation"]],
     "paint": {"line-color": "#7a7a7a", "line-dasharray": [1, 2],
               "line-width": ["interpolate", ["linear"], ["zoom"], 13, 0.8, 16, 1.6]}},
    {"id": "footpaths-row-footpath", "type": "line", "source": "footpaths", "source-layer": "footpaths", "minzoom": 10,
     "filter": ["in", ["get", "designation"], ["literal", ["public_footpath", "core_path"]]],
     "paint": {"line-color": "#e6007e", "line-dasharray": [3, 2],
               "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.8, 14, 1.8, 16, 2.6]}},
    {"id": "footpaths-row-bridleway", "type": "line", "source": "footpaths", "source-layer": "footpaths", "minzoom": 10,
     "filter": ["==", ["get", "designation"], "public_bridleway"],
     "paint": {"line-color": "#00a651", "line-dasharray": [4, 2],
               "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.8, 14, 1.8, 16, 2.6]}},
    {"id": "footpaths-row-byway", "type": "line", "source": "footpaths", "source-layer": "footpaths", "minzoom": 10,
     "filter": ["in", ["get", "designation"], ["literal", ["restricted_byway", "byway_open_to_all_traffic"]]],
     "paint": {"line-color": ["match", ["get", "designation"], "restricted_byway", "#6a3d9a", "#c8102e"],
               "line-dasharray": [6, 2],
               "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.8, 14, 1.8, 16, 2.6]}},
    {"id": "footpaths-name", "type": "symbol", "source": "footpaths", "source-layer": "footpaths", "minzoom": 14,
     "filter": ["has", "name"],
     "layout": {"symbol-placement": "line", "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 11},
     "paint": {"text-color": "#333333", "text-halo-color": "#ffffff", "text-halo-width": 1.2}}
  ]
}
```

`tools/map-styles/layers/flood-zones.json` (one fill layer per region source-layer; a region absent from the archive renders nothing):

```json
{
  "sources": {"flood-zones": {"type": "vector", "url": "pmtiles:///maps/overlays/flood-zones.pmtiles"}},
  "layers": [
    {"id": "flood-zones-england", "type": "fill", "source": "flood-zones", "source-layer": "flood_england",
     "paint": {"fill-color": "#1e90ff", "fill-opacity": 0.35, "fill-outline-color": "#0b5cad"}},
    {"id": "flood-zones-wales", "type": "fill", "source": "flood-zones", "source-layer": "flood_wales",
     "paint": {"fill-color": "#1e90ff", "fill-opacity": 0.35, "fill-outline-color": "#0b5cad"}},
    {"id": "flood-zones-scotland", "type": "fill", "source": "flood-zones", "source-layer": "flood_scotland",
     "paint": {"fill-color": "#1e90ff", "fill-opacity": 0.35, "fill-outline-color": "#0b5cad"}},
    {"id": "flood-zones-ni", "type": "fill", "source": "flood-zones", "source-layer": "flood_ni",
     "paint": {"fill-color": "#1e90ff", "fill-opacity": 0.35, "fill-outline-color": "#0b5cad"}},
    {"id": "flood-zones-roi", "type": "fill", "source": "flood-zones", "source-layer": "flood_roi",
     "paint": {"fill-color": "#1e90ff", "fill-opacity": 0.35, "fill-outline-color": "#0b5cad"}}
  ]
}
```

`tools/map-styles/layers/overlays.json` (sources for the overlays that may be tiled by the 5 MB rule; the styles step keeps only those actually built as `pmtiles`):

```json
{
  "sources": {
    "water": {"type": "vector", "url": "pmtiles:///maps/overlays/water.pmtiles"},
    "airports-military": {"type": "vector", "url": "pmtiles:///maps/overlays/airports-military.pmtiles"},
    "access-land": {"type": "vector", "url": "pmtiles:///maps/overlays/access-land.pmtiles"}
  },
  "layers": [
    {"id": "water-fill", "type": "fill", "source": "water", "source-layer": "water",
     "paint": {"fill-color": "#1ca3c9", "fill-opacity": 0.45, "fill-outline-color": "#0e6f8a"}},
    {"id": "water-label", "type": "symbol", "source": "water", "source-layer": "water", "minzoom": 11,
     "filter": ["has", "name"],
     "layout": {"text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 11},
     "paint": {"text-color": "#0e6f8a", "text-halo-color": "#ffffff", "text-halo-width": 1}},
    {"id": "airports-military-fill", "type": "fill", "source": "airports-military", "source-layer": "airports-military",
     "paint": {"fill-color": ["case", ["has", "military"], "#8b0000", "#555555"], "fill-opacity": 0.35}},
    {"id": "airports-military-label", "type": "symbol", "source": "airports-military", "source-layer": "airports-military",
     "minzoom": 9, "filter": ["has", "name"],
     "layout": {"text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 11},
     "paint": {"text-color": "#3a0000", "text-halo-color": "#ffffff", "text-halo-width": 1}},
    {"id": "access-land-fill", "type": "fill", "source": "access-land", "source-layer": "access-land",
     "paint": {"fill-color": "#f2b705", "fill-opacity": 0.3, "fill-outline-color": "#a07800"}}
  ]
}
```

`api/sos/mapbuild/styles.py`:

```python
"""Step `styles`: Protomaps styles from Node, OS Open Zoomstack styles rewritten, sprites and glyphs vendored."""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Iterable

from .common import BuildError, Context, fetch_github_tarball, log, pmtiles_metadata, vector_layer_ids

NOTO_FACES = ("Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic")
OS_FACES = ("Source Sans Pro Regular", "Source Sans Pro Bold", "Source Sans Pro Italic",
            "Source Sans Pro SemiBold", "Open Sans Regular")
FIXTURE_GLYPH_RANGES = ("0-255", "256-511")
OS_STYLES = (("OS Open Zoomstack - Outdoor.json", "os-outdoor.json"),
             ("OS Open Zoomstack - Night.json", "os-night.json"))
OS_GL_DIR = Path("Vector Tiles") / "Mapbox GL Styles"
OS_TILES_URL = "pmtiles:///maps/os-zoomstack.pmtiles"
OS_SPRITE = "/maps/sprites/os/sprites"
GLYPHS_URL = "/maps/fonts/{fontstack}/{range}.pbf"
OS_ATTRIBUTION = "Contains OS data &copy; Crown copyright and database right 2026"
MAPBOX_ONLY_KEYS = ("created", "modified", "owner", "id", "visibility", "draft")
FRAGMENTS = ("contours", "hillshade", "footpaths", "flood-zones", "overlays")
SPRITE_SUFFIXES = (".json", ".png", "@2x.json", "@2x.png", "@3x.json", "@3x.png")


def rewrite_os_style(style: dict, *, tiles_url: str = OS_TILES_URL, sprite: str = OS_SPRITE,
                     glyphs: str = GLYPHS_URL) -> dict:
    """The spec's jq rewrite: local source, sprite and glyphs, every layer on source "os",
    Arial Unicode MS dropped from every text-font stack, Mapbox account keys removed."""
    new = copy.deepcopy(style)
    new["sources"] = {"os": {"type": "vector", "url": tiles_url, "attribution": OS_ATTRIBUTION}}
    new["sprite"] = sprite
    new["glyphs"] = glyphs
    for layer in new.get("layers", []):
        if "source" in layer:
            layer["source"] = "os"
        fonts = layer.get("layout", {}).get("text-font")
        if isinstance(fonts, list):
            layer["layout"]["text-font"] = [f for f in fonts if not (isinstance(f, str) and f.startswith("Arial Unicode MS"))]
    for key in MAPBOX_ONLY_KEYS:
        new.pop(key, None)
    return new


def missing_source_layers(style: dict, present: set[str]) -> set[str]:
    used = {layer["source-layer"] for layer in style.get("layers", []) if "source-layer" in layer}
    return used - present


def style_fonts(style: dict) -> set[str]:
    faces: set[str] = set()
    for layer in style.get("layers", []):
        fonts = layer.get("layout", {}).get("text-font")
        if isinstance(fonts, list):
            faces.update(f for f in fonts if isinstance(f, str))
    return faces


def vendor_glyphs(src_fonts: Path, dest: Path, faces: Iterable[str], ranges: Iterable[str] | None = None) -> int:
    copied = 0
    for face in faces:
        face_dir = src_fonts / face
        if not face_dir.is_dir():
            raise BuildError(f"glyph face missing under {src_fonts}: {face}")
        wanted = [face_dir / f"{rng}.pbf" for rng in ranges] if ranges else sorted(face_dir.glob("*.pbf"))
        (dest / face).mkdir(parents=True, exist_ok=True)
        for pbf in wanted:
            if not pbf.exists():
                raise BuildError(f"glyph range missing: {pbf}")
            shutil.copyfile(pbf, dest / face / pbf.name)
            copied += 1
    return copied


def vendor_sprites(src: Path, dest: Path, names: Iterable[str]) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    wanted = {f"{name}{suffix}" for name in names for suffix in SPRITE_SUFFIXES}
    copied = 0
    for entry in sorted(src.iterdir()):
        if entry.is_file() and entry.name in wanted:
            shutil.copyfile(entry, dest / entry.name)
            copied += 1
    if copied == 0:
        raise BuildError(f"no sprite files named {sorted(names)} under {src}")
    return copied


def style_index(base_name: str) -> dict:
    return {
        "osm": {"vault": "/maps/styles/osm-vault.json", "field": "/maps/styles/osm-light.json",
                "blackout": "/maps/styles/osm-dark.json", "tiles": f"/maps/{base_name}"},
        "os": {"vault": "/maps/styles/os-night.json", "field": "/maps/styles/os-outdoor.json",
               "blackout": "/maps/styles/os-night.json", "tiles": "/maps/os-zoomstack.pmtiles"},
        "layers": {name: f"/maps/styles/layers/{name}.json" for name in FRAGMENTS},
    }


def render_layer_fragment(text: str, *, height_field: str) -> str:
    return text.replace("__HEIGHT__", height_field)


def prune_overlay_fragment(fragment: dict, kinds: dict[str, str]) -> dict:
    keep = {sid for sid in fragment["sources"] if kinds.get(sid) == "pmtiles"}
    return {"sources": {k: v for k, v in fragment["sources"].items() if k in keep},
            "layers": [layer for layer in fragment["layers"] if layer.get("source") in keep]}


class StylesStep:
    id = "styles"

    def outputs(self, ctx: Context) -> list[str]:
        return ["styles/index.json", "styles/osm-vault.json", "styles/os-outdoor.json", "styles/os-night.json",
                "sprites/v4/light.json", "sprites/os/sprites.json",
                "fonts/Noto Sans Regular/0-255.pbf", "fonts/Source Sans Pro Regular/0-255.pbf"]

    def run(self, ctx: Context) -> None:
        os_archive = ctx.output("os-zoomstack.pmtiles")
        if not os_archive.exists():
            raise BuildError("styles needs os-zoomstack.pmtiles: run the 'os' step first")
        tools = ctx.repo / "tools" / "map-styles"
        styles_dir = ctx.stage("styles")
        ctx.run(["pnpm", "install", "--frozen-lockfile"], cwd=tools)
        ctx.run(["node", "build-styles.mjs", "--out", str(styles_dir), "--tiles", f"pmtiles:///maps/{ctx.base_name}"], cwd=tools)

        assets = fetch_github_tarball(ctx, "protomaps/basemaps-assets", ctx.version("BASEMAPS_ASSETS_COMMIT"))
        os_repo = fetch_github_tarball(ctx, "OrdnanceSurvey/OS-Open-Zoomstack-Stylesheets", ctx.version("OS_ZOOMSTACK_STYLES_COMMIT"))
        os_gl = os_repo / OS_GL_DIR
        sprites_dir = ctx.stage("sprites")
        vendor_sprites(assets / "sprites" / "v4", sprites_dir / "v4", ("light", "dark"))
        vendor_sprites(os_gl / "sprites", sprites_dir / "os", ("sprites",))
        fonts_dir = ctx.stage("fonts")
        ranges = FIXTURE_GLYPH_RANGES if ctx.fixture else None
        glyphs = vendor_glyphs(assets / "fonts", fonts_dir, NOTO_FACES, ranges)
        glyphs += vendor_glyphs(os_gl / "fonts", fonts_dir, OS_FACES, ranges)

        present = vector_layer_ids(pmtiles_metadata(ctx, os_archive))
        for src_name, out_name in OS_STYLES:
            style = json.loads((os_gl / src_name).read_text())
            new = rewrite_os_style(style)
            missing = missing_source_layers(new, present)
            if missing:
                raise BuildError(f"{src_name} uses source-layers absent from os-zoomstack.pmtiles: {sorted(missing)}")
            unknown_fonts = style_fonts(new) - set(OS_FACES)
            if unknown_fonts:
                raise BuildError(f"{src_name} uses fonts that are not vendored: {sorted(unknown_fonts)}")
            (styles_dir / out_name).write_text(json.dumps(new, indent=1) + "\n")

        side = ctx.sidecar("contours.pmtiles") or {}
        height_field = side.get("height_field", "height")
        index_path = ctx.output("overlays/index.json")
        kinds = {k: v.get("kind", "") for k, v in json.loads(index_path.read_text()).items()} if index_path.exists() else {}
        layers_dir = styles_dir / "layers"
        layers_dir.mkdir()
        for name in FRAGMENTS:
            text = render_layer_fragment((tools / "layers" / f"{name}.json").read_text(), height_field=height_field)
            fragment = json.loads(text)
            if name == "overlays":
                fragment = prune_overlay_fragment(fragment, kinds)
            (layers_dir / f"{name}.json").write_text(json.dumps(fragment, indent=1) + "\n")
        (styles_dir / "index.json").write_text(json.dumps(style_index(ctx.base_name), indent=2) + "\n")

        for name in ("styles", "sprites", "fonts"):
            ctx.commit(name)
        log.info("[styles] %d glyph files, height field %r, overlay kinds %s", glyphs, height_field, kinds)
        ctx.write_sidecar("styles", {"step": self.id, "base": ctx.base_name, "height_field": height_field,
                                     "glyph_faces": sorted(NOTO_FACES + OS_FACES), "glyph_files": glyphs,
                                     "fixture_ranges": list(FIXTURE_GLYPH_RANGES) if ctx.fixture else [],
                                     "basemaps_assets": ctx.version("BASEMAPS_ASSETS_COMMIT"),
                                     "os_stylesheets": ctx.version("OS_ZOOMSTACK_STYLES_COMMIT")})
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), StylesStep()]
```

`Makefile`: add to the `test` target (after the pytest and vitest lines) `cd tools/map-styles && pnpm install --frozen-lockfile --silent && node --test`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/tools/map-styles && pnpm install && node --test 2>&1 | tail -6`
Expected: `# pass 3`, `# fail 0`.

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_styles.py -q 2>&1 | tail -3`
Expected: `10 passed`.

Run: `cd /home/dan/OperationSOS/tools/map-styles && node build-styles.mjs --out /tmp/sos-styles --tiles pmtiles:///maps/test.pmtiles && python3 -c "import json; s=json.load(open('/tmp/sos-styles/osm-vault.json')); print(len(s['layers']), s['sources'])"`
Expected: `wrote osm-light.json (N layers)` three times and a printed layer count above 50 with `{'protomaps': {'type': 'vector', 'url': 'pmtiles:///maps/test.pmtiles', 'attribution': ...}}`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add tools/map-styles/package.json tools/map-styles/pnpm-lock.yaml tools/map-styles/build-styles.mjs \
        tools/map-styles/build-styles.test.mjs tools/map-styles/layers api/sos/mapbuild/styles.py \
        api/sos/buildmaps.py api/tests/test_buildmaps_styles.py Makefile
git commit -m "feat(maps): styles step generates Protomaps flavours, rewrites OS Zoomstack styles and vendors assets"
```

---

### Task 4: Step `os` — OS Downloads API client and OS Open Zoomstack → `os-zoomstack.pmtiles`

**Files:**
- Create: `api/sos/mapbuild/osdata.py`
- Create: `api/tests/test_buildmaps_os.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `Context.download`, `bbox_str`, `pmtiles_header`, `pmtiles_metadata`, `vector_layer_ids` (Task 1); `httpx`.
- Produces: `os_downloads(ctx, product) -> list[dict]` (the API's JSON list of `{md5, size, url, format, subformat?, area, fileName}`), `pick_download(entries, file_name) -> dict`, `os_fetch(ctx, product, file_name) -> Path` (downloads into the source cache with the API's md5), `unzip_single(zip_path, pattern, dest_dir) -> Path`, `OsZoomstackStep` (`id == "os"`, output `os-zoomstack.pmtiles`, sidecar with `header` and `layers`). Tasks 5, 6 and 8 reuse `os_fetch` and `unzip_single` for Terrain 50 and Open Names.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_buildmaps_os.py`:

```python
import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import osdata
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx

API = "https://api.os.uk/downloads/v1/products/OpenZoomstack/downloads"
ENTRIES = [
    {"md5": "19c18967b2d83e7eff4bfc0a61f4fc28", "size": 4301453983,
     "url": "https://api.os.uk/downloads/v1/products/OpenZoomstack/downloads?area=GB&format=GeoPackage&redirect",
     "format": "GeoPackage", "area": "GB", "fileName": "OS_Open_Zoomstack.zip"},
    {"md5": "04c5ebcfa98447fab9925803dcbf7497", "size": 2852712448,
     "url": "https://api.os.uk/downloads/v1/products/OpenZoomstack/downloads?area=GB&format=Vector+Tiles&subformat=%28MBTiles%29&redirect",
     "format": "Vector Tiles", "subformat": "(MBTiles)", "area": "GB", "fileName": "OS_Open_Zoomstack.mbtiles"},
]
OS_LAYERS = ["airports", "boundaries", "buildings", "contours", "etl", "foreshore", "greenspaces", "names",
             "national_parks", "rail", "railwaystations", "roads", "sea", "sites", "surfacewater", "urban_areas",
             "waterlines", "woodland"]
HEADER = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 14, "bounds": [-9.0, 49.75, 2.0, 61.0]}


def _show(cmd):
    return json.dumps(HEADER if "--header-json" in cmd else {"vector_layers": [{"id": l, "fields": {}} for l in OS_LAYERS]})


@respx.mock
def test_os_fetch_picks_the_named_file_and_downloads_with_md5(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    path = osdata.os_fetch(ctx, "OpenZoomstack", "OS_Open_Zoomstack.mbtiles")
    assert path == ctx.src / "OS_Open_Zoomstack.mbtiles" and path.exists()
    cmd = runner.calls[0]
    assert cmd[0] == "aria2c" and cmd[-1] == ENTRIES[1]["url"]
    assert "--checksum=md5=04c5ebcfa98447fab9925803dcbf7497" in cmd


def test_pick_download_error_lists_available_names():
    with pytest.raises(BuildError, match="terr50_mbtiles_gb.zip.*OS_Open_Zoomstack.mbtiles"):
        osdata.pick_download(ENTRIES, "terr50_mbtiles_gb.zip")


@respx.mock
def test_os_downloads_non_200_is_a_build_error(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(503))
    with pytest.raises(BuildError, match="503"):
        osdata.os_downloads(make_ctx(tmp_path), "OpenZoomstack")


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_unzip_single_extracts_once_and_finds_one_match(tmp_path):
    z = tmp_path / "terr50_mbtiles_gb.zip"
    z.write_bytes(_zip_bytes({"data/terr50_gb.mbtiles": b"sqlite", "doc/readme.txt": b"hi"}))
    dest = tmp_path / "terr50_mbtiles"
    found = osdata.unzip_single(z, "*.mbtiles", dest)
    assert found == dest / "data" / "terr50_gb.mbtiles" and found.read_bytes() == b"sqlite"
    (dest / "data" / "terr50_gb.mbtiles").write_bytes(b"touched")
    assert osdata.unzip_single(z, "*.mbtiles", dest).read_bytes() == b"touched", "must not re-extract"
    with pytest.raises(BuildError, match="found 0"):
        osdata.unzip_single(z, "*.gpkg", dest)


@respx.mock
def test_os_step_full_mode_converts_straight_into_staging(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner(outputs={"pmtiles show": _show}, files={"os-zoomstack.pmtiles": b"pm"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    osdata.OsZoomstackStep().run(ctx)
    convert = runner.find("pmtiles", "convert")
    assert convert == [["pmtiles", "convert", str(ctx.src / "OS_Open_Zoomstack.mbtiles"), str(ctx.incoming / "os-zoomstack.pmtiles")]]
    assert not runner.find("pmtiles", "extract")
    assert (ctx.out / "os-zoomstack.pmtiles").read_bytes() == b"pm"
    side = json.loads((ctx.out / "os-zoomstack.json").read_text())
    assert side["layers"] == OS_LAYERS and side["header"]["maxzoom"] == 14


@respx.mock
def test_os_step_fixture_mode_converts_once_then_extracts_bbox(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner(outputs={"pmtiles show": _show},
                        files={"os-zoomstack-full.pmtiles": b"full", "os-zoomstack.pmtiles": b"pm"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner, force=True)
    osdata.OsZoomstackStep().run(ctx)
    osdata.OsZoomstackStep().run(ctx)
    assert len(runner.find("pmtiles", "convert")) == 1, "the full conversion is cached in the source dir"
    extract = runner.find("pmtiles", "extract")[0]
    assert extract == ["pmtiles", "extract", str(ctx.src / "os-zoomstack-full.pmtiles"),
                       str(ctx.incoming / "os-zoomstack.pmtiles"), "--bbox=-1.56,50.87,-1.46,50.97"]


@respx.mock
def test_os_step_fails_when_roads_layer_is_missing(tmp_path):
    respx.get(API).mock(return_value=httpx.Response(200, json=ENTRIES))
    runner = FakeRunner(outputs={"pmtiles show": lambda cmd: json.dumps(HEADER if "--header-json" in cmd else {"vector_layers": [{"id": "sea", "fields": {}}]})},
                        files={"os-zoomstack.pmtiles": b"pm"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    with pytest.raises(BuildError, match="roads"):
        osdata.OsZoomstackStep().run(ctx)
    assert not (ctx.out / "os-zoomstack.pmtiles").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_os.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.osdata'`.

- [ ] **Step 3: Implement `osdata.py` and register the step**

`api/sos/mapbuild/osdata.py`:

```python
"""OS Data Hub downloads API client and step `os` (OS Open Zoomstack MBTiles -> os-zoomstack.pmtiles)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

from .common import BuildError, Context, bbox_str, pmtiles_header, pmtiles_metadata, vector_layer_ids

REQUIRED_OS_LAYERS = ("roads", "names", "sea")


def os_downloads(ctx: Context, product: str) -> list[dict]:
    url = f"{ctx.version('OS_DOWNLOADS_API')}/products/{product}/downloads"
    response = httpx.get(url, timeout=60, follow_redirects=True)
    if response.status_code != 200:
        raise BuildError(f"OS downloads API {url} returned {response.status_code}")
    return response.json()


def pick_download(entries: list[dict], file_name: str) -> dict:
    for entry in entries:
        if entry.get("fileName") == file_name:
            return entry
    names = ", ".join(str(e.get("fileName")) for e in entries)
    raise BuildError(f"OS downloads API has no {file_name}; available: {names}")


def os_fetch(ctx: Context, product: str, file_name: str) -> Path:
    entry = pick_download(os_downloads(ctx, product), file_name)
    return ctx.download(entry["url"], file_name, md5=entry.get("md5"))


def unzip_single(zip_path: Path, pattern: str, dest_dir: Path) -> Path:
    """Extract zip_path into dest_dir once (marker file) and return the single member matching the glob."""
    marker = dest_dir / ".extracted"
    if not marker.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
        marker.touch()
    matches = sorted(p for p in dest_dir.rglob(pattern) if p.is_file())
    if len(matches) != 1:
        raise BuildError(f"expected exactly one {pattern} inside {zip_path.name}, found {len(matches)}")
    return matches[0]


class OsZoomstackStep:
    id = "os"

    def outputs(self, ctx: Context) -> list[str]:
        return ["os-zoomstack.pmtiles"]

    def run(self, ctx: Context) -> None:
        mbtiles = os_fetch(ctx, "OpenZoomstack", "OS_Open_Zoomstack.mbtiles")
        staged = ctx.stage("os-zoomstack.pmtiles")
        if ctx.fixture:
            full = ctx.src / "os-zoomstack-full.pmtiles"
            if not full.exists():
                ctx.run(["pmtiles", "convert", str(mbtiles), str(full)])
            ctx.run(["pmtiles", "extract", str(full), str(staged), f"--bbox={bbox_str(ctx.bbox)}"])
        else:
            ctx.run(["pmtiles", "convert", str(mbtiles), str(staged)])
        header = pmtiles_header(ctx, staged)
        layers = sorted(vector_layer_ids(pmtiles_metadata(ctx, staged)))
        missing = [name for name in REQUIRED_OS_LAYERS if name not in layers]
        if missing:
            raise BuildError(f"os-zoomstack.pmtiles lacks expected source-layers {missing}; found {layers}")
        ctx.commit("os-zoomstack.pmtiles")
        ctx.write_sidecar("os-zoomstack.pmtiles", {"step": self.id, "source": "OS Open Zoomstack (OS Downloads API, MBTiles)",
                                                   "input": mbtiles.name, "header": header, "layers": layers})
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), StylesStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_os.py -q 2>&1 | tail -3`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/osdata.py api/sos/buildmaps.py api/tests/test_buildmaps_os.py
git commit -m "feat(maps): os step downloads OS Open Zoomstack via the OS API and converts it to PMTiles"
```

---

### Task 5: Step `contours` — OS Terrain 50 tiles for GB, `gdal_contour` for NI/RoI/IoM/CI, `tile-join` merge (plus the OSM input and DEM source modules)

**Files:**
- Create: `api/sos/mapbuild/osm.py`
- Create: `api/sos/mapbuild/dem.py`
- Create: `api/sos/mapbuild/contours.py`
- Create: `tools/map-styles/export/regions.json`
- Create: `api/tests/test_buildmaps_contours.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `os_fetch`, `unzip_single` (Task 4); `Context`, `bbox_*`, `read_geojsonseq`, PMTiles helpers (Task 1).
- Produces:
  - `osm.osm_input(ctx) -> Path` (full: Geofabrik britain-and-ireland PBF; fixture: `osmium extract -b <bbox>` of the Hampshire PBF), `osm.export_config(ctx, name) -> Path`, `osm.REGIONS`, `osm.NON_GB`, `osm.REGION_LABELS`, `osm.select_region_features(features) -> dict[str, dict]`, `osm.region_polygons(ctx, pbf) -> dict[str, Path]` (GeoJSON per region id `roi, iom, jersey, guernsey, ni`), `osm.nongb_cutline(ctx, pbf | None) -> Path`.
  - `dem.copernicus_name(lat, lon)`, `dem.copernicus_names(bbox, *, max_lat=57)`, `dem.fetch_copernicus(ctx, bbox) -> list[Path]`, `dem.terr50_asc_dir(ctx) -> Path`, `dem.osni_dtm(ctx) -> Path | None`, `dem.dem_vrts(ctx, work) -> list[Path]` (order `glo30.vrt, [osni.vrt], t50.vrt`), `dem.nongb_dtm_vrt(ctx, work) -> Path`, constants `NI_BBOX`, `OSNI_SRS`, `T50_SRS`.
  - `contours.contour_height_field(metadata) -> str`, `contours.ContoursStep` (`id == "contours"`, output `contours.pmtiles`, sidecar `height_field`, `layers`).

- [ ] **Step 1: Write the failing tests**

`api/tests/test_buildmaps_contours.py`:

```python
import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import contours, dem, osm
from sos.mapbuild.common import BuildError, SPEC_BBOX, FIXTURE_BBOX
from tests.mapbuild_helpers import FakeRunner, make_ctx

T50_API = "https://api.os.uk/downloads/v1/products/Terrain50/downloads"
T50_ENTRIES = [
    {"md5": "feba9008db55cdcb5c5e5b7896e3428b", "size": 161706566, "fileName": "terr50_gagg_gb.zip",
     "url": "https://api.os.uk/downloads/v1/products/Terrain50/downloads?area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect",
     "format": "ASCII Grid and GML (Grid)", "area": "GB"},
    {"md5": "fa3fed543cfa2073863b4170194e13b7", "size": 1070803333, "fileName": "terr50_mbtiles_gb.zip",
     "url": "https://api.os.uk/downloads/v1/products/Terrain50/downloads?area=GB&format=Vector+Tiles&subformat=%28MBTiles%29&redirect",
     "format": "Vector Tiles", "subformat": "(MBTiles)", "area": "GB"},
]
T50_META = {"vector_layers": [{"id": "contour_line", "fields": {"height": "Number", "id": "String"}, "minzoom": 9, "maxzoom": 14},
                              {"id": "spot_height", "fields": {"height": "Number"}}, {"id": "land_water_boundary", "fields": {}}]}
HEADER = {"tile_type": "mvt", "minzoom": 9, "maxzoom": 14, "bounds": [-9, 49.7, 2, 61]}
TILE_LIST = b"Copernicus_DSM_COG_10_N50_00_W002_00_DEM\nCopernicus_DSM_COG_10_N50_00_W001_00_DEM\nCopernicus_DSM_COG_10_N53_00_W006_00_DEM\n"


def _zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_copernicus_names_cover_the_spec_rows_and_columns():
    names = dem.copernicus_names(SPEC_BBOX)
    assert len(names) == 8 * 14
    assert names[0] == "Copernicus_DSM_COG_10_N49_00_W011_00_DEM"
    assert names[-1] == "Copernicus_DSM_COG_10_N56_00_E002_00_DEM"
    assert dem.copernicus_names(FIXTURE_BBOX) == ["Copernicus_DSM_COG_10_N50_00_W002_00_DEM"]


def test_fetch_copernicus_downloads_only_squares_present_in_the_bucket(tmp_path):
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    paths = dem.fetch_copernicus(ctx, ctx.bbox)
    assert paths == [ctx.src / "copernicus" / "Copernicus_DSM_COG_10_N50_00_W002_00_DEM.tif"]
    urls = [c[-1] for c in runner.find("aria2c")]
    assert urls == ["https://example.test/dem/tileList.txt",
                    "https://example.test/dem/Copernicus_DSM_COG_10_N50_00_W002_00_DEM/Copernicus_DSM_COG_10_N50_00_W002_00_DEM.tif"]
    ctx2 = make_ctx(tmp_path / "b", fixture=False, runner=FakeRunner(files={"copernicus-tileList.txt": b"nothing\n"}))
    with pytest.raises(BuildError, match="no Copernicus"):
        dem.fetch_copernicus(ctx2, ctx2.bbox)


@respx.mock
def test_terr50_asc_dir_unpacks_nested_zips_once(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    inner_hp = _zip({"HP40.asc": b"ncols 200\n", "HP40.gml": b"<gml/>"})
    inner_su = _zip({"SU41.asc": b"ncols 200\n"})
    outer = _zip({"data/hp/hp40_OST50GRID_20230601.zip": inner_hp, "data/su/su41_OST50GRID_20230601.zip": inner_su, "doc/licence.txt": b"OGL"})
    runner = FakeRunner(files={"terr50_gagg_gb.zip": outer})
    ctx = make_ctx(tmp_path, runner=runner)
    root = dem.terr50_asc_dir(ctx)
    assert sorted(p.name for p in root.glob("*.asc")) == ["HP40.asc", "SU41.asc"]
    (root / "HP40.asc").write_bytes(b"kept")
    assert dem.terr50_asc_dir(ctx) == root and (root / "HP40.asc").read_bytes() == b"kept"


def test_osni_dtm_blank_url_returns_none_with_warning(tmp_path, caplog):
    ctx = make_ctx(tmp_path, versions={"OSNI_DTM_URL": ""})
    assert dem.osni_dtm(ctx) is None
    assert "OSNI_DTM_URL is blank" in caplog.text
    ctx2 = make_ctx(tmp_path / "b", versions={"OSNI_DTM_URL": "https://example.test/osni_dtm50.tif"})
    assert dem.osni_dtm(ctx2) == ctx2.src / "osni-dtm50.tif"


@respx.mock
def test_dem_vrts_are_built_in_later_wins_order(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    outer = _zip({"data/su/su41.zip": _zip({"SU41.asc": b"ncols 1\n"}), "data/su/su42.zip": _zip({"SU42.asc": b"ncols 1\n"})})
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST, "terr50_gagg_gb.zip": outer})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner, versions={"OSNI_DTM_URL": "https://example.test/osni.tif"})
    work = tmp_path / "work"
    vrts = dem.dem_vrts(ctx, work)
    assert [v.name for v in vrts] == ["glo30.vrt", "t50.vrt"], "OSNI is skipped when the bbox misses Northern Ireland"
    calls = runner.find("gdalbuildvrt")
    assert calls[0][:4] == ["gdalbuildvrt", "-overwrite", "-input_file_list", str(work / "glo30.txt")]
    assert calls[1][:6] == ["gdalbuildvrt", "-overwrite", "-a_srs", "EPSG:27700", "-input_file_list", str(work / "t50.txt")]
    assert (work / "t50.txt").read_text().splitlines() == [str(ctx.src / "terr50_asc" / "SU41.asc"), str(ctx.src / "terr50_asc" / "SU42.asc")]


@respx.mock
def test_dem_vrts_include_osni_for_full_bbox(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner, versions={"OSNI_DTM_URL": "https://example.test/osni.tif"})
    (ctx.src / "terr50_asc").mkdir()
    (ctx.src / "terr50_asc" / ".done").touch()
    (ctx.src / "terr50_asc" / "SU41.asc").write_bytes(b"x")
    vrts = dem.dem_vrts(ctx, tmp_path / "work")
    assert [v.name for v in vrts] == ["glo30.vrt", "osni.vrt", "t50.vrt"]
    osni = runner.find("gdalbuildvrt")[1]
    assert osni[2:4] == ["-a_srs", "EPSG:29902"] and osni[-1] == str(ctx.src / "osni-dtm50.tif")


def test_nongb_dtm_vrt_warps_osni_to_4326_and_puts_it_last(tmp_path):
    runner = FakeRunner(files={"copernicus-tileList.txt": TILE_LIST})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner, versions={"OSNI_DTM_URL": "https://example.test/osni.tif"})
    work = tmp_path / "work"
    vrt = dem.nongb_dtm_vrt(ctx, work)
    assert vrt == work / "nongb-4326.vrt"
    warp = runner.find("gdalwarp")[0]
    assert "-s_srs" in warp and warp[warp.index("-s_srs") + 1] == "EPSG:29902" and warp[warp.index("-t_srs") + 1] == "EPSG:4326"
    build = runner.find("gdalbuildvrt")[0]
    assert build[-1] == str(work / "osni-4326.tif") and build[-2].endswith("Copernicus_DSM_COG_10_N53_00_W006_00_DEM.tif")
    assert "-resolution" in build and build[build.index("-resolution") + 1] == "highest"


def test_contour_height_field_prefers_known_names_then_numeric():
    assert contours.contour_height_field(T50_META) == "height"
    assert contours.contour_height_field({"vector_layers": [{"id": "contour_line", "fields": {"PROP_VALUE": "Number"}}]}) == "PROP_VALUE"
    assert contours.contour_height_field({"vector_layers": [{"id": "contour_line", "fields": {"name": "String", "elev_m": "Number"}}]}) == "elev_m"
    with pytest.raises(BuildError, match="no numeric"):
        contours.contour_height_field({"vector_layers": [{"id": "contour_line", "fields": {"name": "String"}}]})
    with pytest.raises(BuildError, match="contour_line"):
        contours.contour_height_field({"vector_layers": []})


def test_select_region_features_matches_iso_codes_and_northern_ireland():
    features = [
        {"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "2", "ISO3166-1": "IE", "name": "Ireland"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "4", "name": "Northern Ireland"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"type": "Feature", "properties": {"boundary": "historic", "ISO3166-1": "IM", "name": "Isle of Man"}, "geometry": {"type": "Polygon", "coordinates": []}},
        {"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "4", "name": "Wales"}, "geometry": {"type": "Polygon", "coordinates": []}},
    ]
    found = osm.select_region_features(features)
    assert set(found) == {"roi", "ni"}
    assert found["roi"]["properties"]["name"] == "Ireland"


def test_region_polygons_runs_osmium_and_writes_one_file_per_region(tmp_path):
    seq = "\x1e" + json.dumps({"type": "Feature", "properties": {"boundary": "administrative", "ISO3166-1": "JE", "name": "Jersey"},
                               "geometry": {"type": "Polygon", "coordinates": [[[-2.2, 49.1], [-2.0, 49.1], [-2.0, 49.3], [-2.2, 49.1]]]}}) + "\n"
    runner = FakeRunner(files={"admin.geojsonseq": seq.encode()})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    paths = osm.region_polygons(ctx, ctx.src / "bi.osm.pbf")
    assert set(paths) == {"roi", "iom", "jersey", "guernsey", "ni"}
    assert json.loads(paths["jersey"].read_text())["features"][0]["properties"]["name"] == "Jersey"
    assert json.loads(paths["roi"].read_text())["features"] == []
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "r/admin_level=2,4" and tags[-2] == str(ctx.src / "bi.osm.pbf")
    export = runner.find("osmium", "export")[0]
    assert "--geometry-types=polygon" in export and export[export.index("-c") + 1].endswith("tools/map-styles/export/regions.json")


def test_nongb_cutline_fixture_is_the_bbox_polygon(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    path = osm.nongb_cutline(ctx, None)
    ring = json.loads(path.read_text())["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == [-1.56, 50.87] and ring[2] == [-1.46, 50.97]


def test_osm_input_fixture_extracts_bbox_from_hampshire(tmp_path):
    runner = FakeRunner(files={"fixture.osm.pbf": b"pbf"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    assert osm.osm_input(ctx) == ctx.src / "fixture.osm.pbf"
    assert runner.find("aria2c")[0][-1] == "https://example.test/hampshire-latest.osm.pbf"
    extract = runner.find("osmium", "extract")[0]
    assert extract[extract.index("-b") + 1] == "-1.56,50.87,-1.46,50.97" and extract[-1] == str(ctx.src / "hampshire-latest.osm.pbf")
    full = make_ctx(tmp_path / "f", fixture=False, runner=FakeRunner())
    assert osm.osm_input(full) == full.src / "britain-and-ireland-latest.osm.pbf"


@respx.mock
def test_contours_step_assembles_the_pipeline_in_fixture_mode(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    runner = FakeRunner(
        outputs={"pmtiles show": lambda cmd: json.dumps(HEADER if "--header-json" in cmd else T50_META)},
        files={"terr50_mbtiles_gb.zip": _zip({"data/terr50_gb.mbtiles": b"sqlite"}), "copernicus-tileList.txt": TILE_LIST,
               "contours-gb-full.pmtiles": b"gb", "contours-gb.pmtiles": b"gbx", "contours-nongb.pmtiles": b"ng", "contours.pmtiles": b"merged"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    contours.ContoursStep().run(ctx)
    tools = [c[0] for c in runner.calls if c[0] not in ("aria2c", "pmtiles")]
    assert tools == ["gdalbuildvrt", "gdalwarp", "gdal_contour", "tippecanoe", "tile-join"]
    work = ctx.src / "contours-work"
    assert runner.find("pmtiles", "convert")[0][2] == str(ctx.src / "terr50_mbtiles" / "data" / "terr50_gb.mbtiles")
    assert runner.find("pmtiles", "extract")[0][-1] == "--bbox=-1.56,50.87,-1.46,50.97"
    warp = runner.find("gdalwarp")[0]
    assert warp[warp.index("-cutline") + 1] == str(ctx.src / "regions" / "nongb-cutline.geojson") and "-crop_to_cutline" in warp
    contour = runner.find("gdal_contour")[0]
    assert contour[1:9] == ["-i", "10", "-a", "height", "-snodata", "-9999", "-f", "FlatGeobuf"]
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:9] == ["-o", str(work / "contours-nongb.pmtiles"), "-l", "contour_line", "-Z11", "-z14", "-P", "--drop-densest-as-needed"]
    join = runner.find("tile-join")[0]
    assert join == ["tile-join", "-o", str(ctx.incoming / "contours.pmtiles"), "-pk", "--force",
                    str(work / "contours-gb.pmtiles"), str(work / "contours-nongb.pmtiles")]
    assert (ctx.out / "contours.pmtiles").read_bytes() == b"merged"
    side = json.loads((ctx.out / "contours.json").read_text())
    assert side["height_field"] == "height" and side["layers"] == ["contour_line", "land_water_boundary", "spot_height"]
```

`tools/map-styles/export/regions.json`:

```json
{
  "attributes": {"type": false, "id": false, "version": false, "changeset": false, "timestamp": false, "uid": false, "user": false, "way_nodes": false},
  "format_options": {},
  "linear_tags": false,
  "area_tags": true,
  "exclude_tags": [],
  "include_tags": ["boundary", "admin_level", "name", "ISO3166-1"]
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_contours.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.contours'`.

- [ ] **Step 3: Implement `osm.py`, `dem.py`, `contours.py`, register the step**

`api/sos/mapbuild/osm.py`:

```python
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
```

`api/sos/mapbuild/dem.py`:

```python
"""Digital terrain sources: Copernicus GLO-30 COGs, OS Terrain 50 ASCII grids and the OSNI 50 m DTM."""
from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path
from typing import Iterable

from .common import BBox, BuildError, Context, bbox_intersects, log
from .osdata import os_fetch, unzip_single

COPERNICUS_MAX_LAT = 57  # rows N49..N56 cover RoI, NI, IoM and CI; north of 57 N is Great Britain (OS Terrain 50)
NI_BBOX: BBox = (-8.2, 54.0, -5.4, 55.4)
OSNI_SRS = "EPSG:29902"  # TM65 / Irish Grid
T50_SRS = "EPSG:27700"


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
    ctx.run(["gdalbuildvrt", "-overwrite", "-input_file_list", str(_input_list(work, "glo30.txt", fetch_copernicus(ctx, ctx.bbox))), str(glo)])
    vrts.append(glo)
    osni = osni_dtm(ctx)
    if osni is not None and bbox_intersects(ctx.bbox, NI_BBOX):
        osni_vrt = work / "osni.vrt"
        ctx.run(["gdalbuildvrt", "-overwrite", "-a_srs", OSNI_SRS, str(osni_vrt), str(osni)])
        vrts.append(osni_vrt)
    grids = sorted(terr50_asc_dir(ctx).glob("*.asc"))
    if not grids:
        raise BuildError("no OS Terrain 50 .asc grids found")
    t50 = work / "t50.vrt"
    ctx.run(["gdalbuildvrt", "-overwrite", "-a_srs", T50_SRS, "-input_file_list", str(_input_list(work, "t50.txt", grids)), str(t50)])
    vrts.append(t50)
    return vrts


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
```

`api/sos/mapbuild/contours.py`:

```python
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
        ctx.commit("contours.pmtiles")
        ctx.write_sidecar("contours.pmtiles", {
            "step": self.id, "height_field": height, "layers": layers, "interval_m": 10,
            "gb_source": "OS Terrain 50 vector tiles (terr50_mbtiles_gb.zip)",
            "non_gb_source": "gdal_contour over Copernicus GLO-30 (OSNI on top where configured)",
            "header": pmtiles_header(ctx, staged)})
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), StylesStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_contours.py -q 2>&1 | tail -3`
Expected: `13 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/osm.py api/sos/mapbuild/dem.py api/sos/mapbuild/contours.py tools/map-styles/export/regions.json \
        api/sos/buildmaps.py api/tests/test_buildmaps_contours.py
git commit -m "feat(maps): contours step merges OS Terrain 50 tiles with gdal_contour output for NI, RoI, IoM and CI"
```

---

### Task 6: Step `hillshade` — one-CRS DTM mosaic → `gdaldem hillshade` → MBTiles PNG8 → overviews → PMTiles

**Files:**
- Create: `api/sos/mapbuild/hillshade.py`
- Create: `api/tests/test_buildmaps_hillshade.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `dem.dem_vrts(ctx, work)` (Task 5), `bbox_args`, `pmtiles_header` (Task 1).
- Produces: `HillshadeStep` (`id == "hillshade"`, output `hillshade.pmtiles`, sidecar `sources`, `header`, `pipeline`). The archive is raster PNG; MapLibre overzooms it above its native maximum (about z12 at 30 m).

- [ ] **Step 1: Write the failing tests**

`api/tests/test_buildmaps_hillshade.py`:

```python
import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import hillshade
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx
from tests.test_buildmaps_contours import T50_API, T50_ENTRIES, TILE_LIST, _zip

PNG_HEADER = {"tile_type": "png", "minzoom": 5, "maxzoom": 12, "bounds": [-1.56, 50.87, -1.46, 50.97]}


def _fixture_ctx(tmp_path, header=PNG_HEADER):
    outer = _zip({"data/su/su41.zip": _zip({"SU41.asc": b"ncols 1\n"})})
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(header)},
                        files={"copernicus-tileList.txt": TILE_LIST, "terr50_gagg_gb.zip": outer, "hillshade.pmtiles": b"png-archive"})
    return make_ctx(tmp_path, fixture=True, runner=runner), runner


@respx.mock
def test_hillshade_step_runs_the_spec_pipeline_in_order(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    ctx, runner = _fixture_ctx(tmp_path)
    hillshade.HillshadeStep().run(ctx)
    work = ctx.src / "hillshade-work"
    tools = [c[0] if c[0] != "pmtiles" else " ".join(c[:2]) for c in runner.calls if c[0] != "aria2c"]
    assert tools == ["gdalbuildvrt", "gdalbuildvrt", "gdalwarp", "gdaldem", "gdal_translate", "gdaladdo",
                     "pmtiles convert", "pmtiles show"]
    warp = runner.find("gdalwarp")[0]
    assert warp[1:12] == ["-overwrite", "-t_srs", "EPSG:3857", "-tr", "30", "30", "-r", "bilinear", "-dstnodata", "-9999", "-te"]
    assert warp[12:18] == ["-1.56", "50.87", "-1.46", "50.97", "-te_srs", "EPSG:4326"]
    assert warp[-3:] == [str(work / "glo30.vrt"), str(work / "t50.vrt"), str(work / "dtm3857.tif")], "later inputs win: OS last"
    shade = runner.find("gdaldem")[0]
    assert shade[1:12] == ["hillshade", "-compute_edges", "-z", "1", "-s", "1", "-az", "315", "-alt", "45", "-co"]
    assert shade[-2:] == [str(work / "dtm3857.tif"), str(work / "hillshade.tif")]
    translate = runner.find("gdal_translate")[0]
    assert translate == ["gdal_translate", "-of", "MBTILES", "-co", "TILE_FORMAT=PNG8", "-co", "ZOOM_LEVEL_STRATEGY=LOWER",
                         str(work / "hillshade.tif"), str(work / "hillshade.mbtiles")]
    assert runner.find("gdaladdo")[0] == ["gdaladdo", "-r", "average", str(work / "hillshade.mbtiles"), "2", "4", "8", "16", "32", "64", "128"]
    assert runner.find("pmtiles", "convert")[0] == ["pmtiles", "convert", str(work / "hillshade.mbtiles"), str(ctx.incoming / "hillshade.pmtiles")]
    assert (ctx.out / "hillshade.pmtiles").read_bytes() == b"png-archive"
    side = json.loads((ctx.out / "hillshade.json").read_text())
    assert side["sources"] == ["glo30.vrt", "t50.vrt"] and side["header"]["tile_type"] == "png"


@respx.mock
def test_hillshade_step_rejects_non_png_archive(tmp_path):
    respx.get(T50_API).mock(return_value=httpx.Response(200, json=T50_ENTRIES))
    ctx, _ = _fixture_ctx(tmp_path, header=dict(PNG_HEADER, tile_type="mvt"))
    with pytest.raises(BuildError, match="png"):
        hillshade.HillshadeStep().run(ctx)
    assert not (ctx.out / "hillshade.pmtiles").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_hillshade.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.hillshade'`.

- [ ] **Step 3: Implement `hillshade.py` and register the step**

`api/sos/mapbuild/hillshade.py`:

```python
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
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.hillshade import HillshadeStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), HillshadeStep(), StylesStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_hillshade.py -q 2>&1 | tail -3`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/hillshade.py api/sos/buildmaps.py api/tests/test_buildmaps_hillshade.py
git commit -m "feat(maps): hillshade step mosaics OS, OSNI and Copernicus DTMs into a PNG8 PMTiles archive"
```

---

### Task 7: Step `overlays` — footpaths, OSM point overlays, flood zones, access land, nuclear and chemical sites

**Files:**
- Create: `api/sos/mapbuild/overlays.py`
- Create: `tools/map-styles/export/paths.json`, `tools/map-styles/export/pois.json`
- Create: `tools/map-styles/data/nuclear-sites.geojson` (only if plan 03 has not created it; if it exists, keep plan 03's file and skip this one)
- Create: `tools/map-styles/data/chemical-sites.geojson`
- Create: `api/tests/fixtures/maps/src/flood-england-sample.geojson`, `api/tests/fixtures/maps/src/access-england-sample.geojson`
- Create: `api/tests/test_buildmaps_overlays.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `osm.osm_input`, `osm.export_config` (Task 5); `Context`, `bbox_args`, `validate_geojson` (Task 1).
- Produces: `OverlaysStep` (`id == "overlays"`, outputs `overlays/index.json`, `overlays/footpaths.pmtiles`, `overlays/flood-zones.pmtiles`, `overlays/nuclear-sites.geojson`), `OSM_OVERLAYS`, `SIZE_RULE_BYTES`, `VectorSource`, `vector_source(ctx, spec, name)`, `ogr_to(ctx, fmt, dest, src, *, spat=None)`, `region_sources(ctx, regions, *, fixture_sample)`, `build_footpaths`, `build_osm_overlay`, `finalise(ctx, ov_id, geojson, staged_dir) -> (kind, file_name)`, `build_flood_zones`, `build_access_land`, `nuclear_sites(ctx) -> dict`, `merge_feature_collections`, `load_geojson`.
- Output contract: `overlays/index.json` is `{"<overlay id>": {"kind": "geojson" | "pmtiles", "file": "overlays/<name>", "size_bytes": n, "features"?: n, "layers"?: [...], "coverage"?: [...]}}`. Plan 03's `manifest/overlays.json` takes its `kind` per overlay from this file after the first full build; Task 3's styles step reads it to prune the overlay layer fragment.

- [ ] **Step 1: Write the failing tests and the committed data files**

`api/tests/fixtures/maps/src/flood-england-sample.geojson` (two polygons over the Test estuary inside the fixture bbox):

```json
{"type": "FeatureCollection", "features": [
 {"type": "Feature", "properties": {"zone": "3", "source": "fixture sample"},
  "geometry": {"type": "Polygon", "coordinates": [[[-1.49, 50.90], [-1.47, 50.90], [-1.47, 50.93], [-1.49, 50.93], [-1.49, 50.90]]]}},
 {"type": "Feature", "properties": {"zone": "2", "source": "fixture sample"},
  "geometry": {"type": "Polygon", "coordinates": [[[-1.50, 50.895], [-1.465, 50.895], [-1.465, 50.935], [-1.50, 50.935], [-1.50, 50.895]]]}}
]}
```

`api/tests/fixtures/maps/src/access-england-sample.geojson` (one polygon on the New Forest edge west of Totton):

```json
{"type": "FeatureCollection", "features": [
 {"type": "Feature", "properties": {"Descrip": "Open Country", "source": "fixture sample"},
  "geometry": {"type": "Polygon", "coordinates": [[[-1.55, 50.90], [-1.52, 50.90], [-1.52, 50.93], [-1.55, 50.93], [-1.55, 50.90]]]}}
]}
```

`tools/map-styles/export/paths.json`:

```json
{
  "attributes": {"type": false, "id": false, "version": false, "changeset": false, "timestamp": false, "uid": false, "user": false, "way_nodes": false},
  "format_options": {},
  "linear_tags": true,
  "area_tags": false,
  "exclude_tags": [],
  "include_tags": ["highway", "designation", "name", "prow_ref", "sac_scale", "trail_visibility", "foot", "access", "surface"]
}
```

`tools/map-styles/export/pois.json`:

```json
{
  "attributes": {"type": false, "id": false, "version": false, "changeset": false, "timestamp": false, "uid": false, "user": false, "way_nodes": false},
  "format_options": {},
  "linear_tags": true,
  "area_tags": true,
  "exclude_tags": [],
  "include_tags": ["name", "amenity", "phone", "opening_hours", "operator", "railway", "network", "industrial",
                   "aeroway", "military", "landuse", "water", "man_made", "natural"]
}
```

`tools/map-styles/data/nuclear-sites.geojson` (create only if absent; every site the spec lists, WGS84 `[lon, lat]`, positions to about 1 km):

```json
{"type": "FeatureCollection", "name": "nuclear-sites", "features": [
 {"type": "Feature", "properties": {"name": "Sizewell", "kind": "power-station", "note": "Sizewell B operating; Sizewell A decommissioning; Sizewell C under construction"}, "geometry": {"type": "Point", "coordinates": [1.620, 52.213]}},
 {"type": "Feature", "properties": {"name": "Hinkley Point", "kind": "power-station", "note": "Hinkley Point B defuelling; Hinkley Point C under construction"}, "geometry": {"type": "Point", "coordinates": [-3.133, 51.209]}},
 {"type": "Feature", "properties": {"name": "Heysham", "kind": "power-station", "note": "Heysham 1 and 2 operating"}, "geometry": {"type": "Point", "coordinates": [-2.916, 54.029]}},
 {"type": "Feature", "properties": {"name": "Hartlepool", "kind": "power-station", "note": "operating"}, "geometry": {"type": "Point", "coordinates": [-1.181, 54.635]}},
 {"type": "Feature", "properties": {"name": "Torness", "kind": "power-station", "note": "operating"}, "geometry": {"type": "Point", "coordinates": [-2.409, 55.968]}},
 {"type": "Feature", "properties": {"name": "Hunterston", "kind": "power-station", "note": "A and B decommissioning"}, "geometry": {"type": "Point", "coordinates": [-4.890, 55.722]}},
 {"type": "Feature", "properties": {"name": "Dungeness", "kind": "power-station", "note": "A and B decommissioning"}, "geometry": {"type": "Point", "coordinates": [0.964, 50.914]}},
 {"type": "Feature", "properties": {"name": "Wylfa", "kind": "power-station", "note": "decommissioning; new build site"}, "geometry": {"type": "Point", "coordinates": [-4.483, 53.416]}},
 {"type": "Feature", "properties": {"name": "Trawsfynydd", "kind": "power-station", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-3.949, 52.925]}},
 {"type": "Feature", "properties": {"name": "Oldbury", "kind": "power-station", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-2.571, 51.649]}},
 {"type": "Feature", "properties": {"name": "Berkeley", "kind": "power-station", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-2.493, 51.693]}},
 {"type": "Feature", "properties": {"name": "Bradwell", "kind": "power-station", "note": "decommissioning; new build site"}, "geometry": {"type": "Point", "coordinates": [0.897, 51.742]}},
 {"type": "Feature", "properties": {"name": "Chapelcross", "kind": "power-station", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-3.224, 55.016]}},
 {"type": "Feature", "properties": {"name": "Sellafield", "kind": "fuel-cycle", "note": "reprocessing and waste stores; Calder Hall"}, "geometry": {"type": "Point", "coordinates": [-3.500, 54.420]}},
 {"type": "Feature", "properties": {"name": "Dounreay", "kind": "research", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-3.744, 58.577]}},
 {"type": "Feature", "properties": {"name": "AWE Aldermaston", "kind": "defence", "note": "warhead research and manufacture"}, "geometry": {"type": "Point", "coordinates": [-1.140, 51.373]}},
 {"type": "Feature", "properties": {"name": "AWE Burghfield", "kind": "defence", "note": "warhead assembly"}, "geometry": {"type": "Point", "coordinates": [-1.030, 51.410]}},
 {"type": "Feature", "properties": {"name": "HMNB Clyde (Faslane)", "kind": "defence", "note": "submarine base"}, "geometry": {"type": "Point", "coordinates": [-4.817, 56.067]}},
 {"type": "Feature", "properties": {"name": "RNAD Coulport", "kind": "defence", "note": "warhead store"}, "geometry": {"type": "Point", "coordinates": [-4.880, 56.050]}},
 {"type": "Feature", "properties": {"name": "HMNB Devonport", "kind": "defence", "note": "submarine refit and laid-up submarines"}, "geometry": {"type": "Point", "coordinates": [-4.183, 50.383]}},
 {"type": "Feature", "properties": {"name": "Barrow-in-Furness", "kind": "defence", "note": "submarine construction"}, "geometry": {"type": "Point", "coordinates": [-3.230, 54.108]}},
 {"type": "Feature", "properties": {"name": "Rosyth", "kind": "defence", "note": "laid-up submarines"}, "geometry": {"type": "Point", "coordinates": [-3.440, 56.020]}},
 {"type": "Feature", "properties": {"name": "Harwell", "kind": "research", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-1.310, 51.575]}},
 {"type": "Feature", "properties": {"name": "Winfrith", "kind": "research", "note": "decommissioning"}, "geometry": {"type": "Point", "coordinates": [-2.270, 50.680]}},
 {"type": "Feature", "properties": {"name": "Springfields", "kind": "fuel-cycle", "note": "fuel manufacture"}, "geometry": {"type": "Point", "coordinates": [-2.780, 53.780]}},
 {"type": "Feature", "properties": {"name": "Capenhurst", "kind": "fuel-cycle", "note": "uranium enrichment"}, "geometry": {"type": "Point", "coordinates": [-2.950, 53.260]}}
]}
```

`tools/map-styles/data/chemical-sites.geojson` (hand-authored major chemical and fuel sites merged with the OSM `industrial=` results):

```json
{"type": "FeatureCollection", "name": "chemical-sites", "features": [
 {"type": "Feature", "properties": {"name": "Fawley refinery and petrochemicals", "industrial": "refinery", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-1.345, 50.830]}},
 {"type": "Feature", "properties": {"name": "Stanlow refinery", "industrial": "refinery", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-2.850, 53.280]}},
 {"type": "Feature", "properties": {"name": "Grangemouth refinery and chemicals", "industrial": "refinery", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-3.700, 56.020]}},
 {"type": "Feature", "properties": {"name": "Pembroke refinery", "industrial": "refinery", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-5.020, 51.685]}},
 {"type": "Feature", "properties": {"name": "Humber refineries (Immingham)", "industrial": "refinery", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-0.250, 53.640]}},
 {"type": "Feature", "properties": {"name": "Runcorn chlor-alkali works", "industrial": "chemical", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-2.700, 53.335]}},
 {"type": "Feature", "properties": {"name": "Billingham chemical works", "industrial": "chemical", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-1.280, 54.600]}},
 {"type": "Feature", "properties": {"name": "Wilton International (Teesside)", "industrial": "chemical", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-1.130, 54.580]}},
 {"type": "Feature", "properties": {"name": "Mossmorran NGL and ethylene plants", "industrial": "chemical", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-3.280, 56.100]}},
 {"type": "Feature", "properties": {"name": "Avonmouth chemical and fuel terminals", "industrial": "chemical", "source": "hand-authored"}, "geometry": {"type": "Point", "coordinates": [-2.700, 51.510]}}
]}
```

`api/tests/test_buildmaps_overlays.py`:

```python
import json
from pathlib import Path

import pytest

from sos.mapbuild import overlays
from sos.mapbuild.common import BuildError, FIXTURE_BBOX, validate_geojson
from tests.mapbuild_helpers import FakeRunner, make_ctx, REPO

DATA = REPO / "tools" / "map-styles" / "data"
SAMPLES = REPO / "api" / "tests" / "fixtures" / "maps" / "src"
POINT_FC = json.dumps({"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"name": "Sample", "amenity": "hospital"}, "geometry": {"type": "Point", "coordinates": [-1.5, 50.9]}}]}).encode()


def _inside(bbox, lon, lat):
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def test_nuclear_sites_file_is_valid_with_at_least_20_uk_points():
    obj = json.loads((DATA / "nuclear-sites.geojson").read_text())
    assert validate_geojson(obj) == []
    assert len(obj["features"]) >= 20
    names = [f["properties"]["name"] for f in obj["features"]]
    for required in ("Sellafield", "AWE Aldermaston", "AWE Burghfield", "HMNB Clyde (Faslane)", "RNAD Coulport", "HMNB Devonport",
                     "Barrow-in-Furness", "Rosyth", "Dounreay", "Harwell", "Winfrith", "Springfields", "Capenhurst"):
        assert required in names, required
    for f in obj["features"]:
        assert f["geometry"]["type"] == "Point"
        lon, lat = f["geometry"]["coordinates"]
        assert -11 <= lon <= 2.2 and 49.1 <= lat <= 61.2, f["properties"]["name"]


def test_chemical_sites_and_fixture_samples_are_valid_geojson():
    chem = json.loads((DATA / "chemical-sites.geojson").read_text())
    assert validate_geojson(chem) == [] and len(chem["features"]) >= 8
    for name in ("flood-england-sample.geojson", "access-england-sample.geojson"):
        obj = json.loads((SAMPLES / name).read_text())
        assert validate_geojson(obj) == []
        for f in obj["features"]:
            for lon, lat in f["geometry"]["coordinates"][0]:
                assert _inside(FIXTURE_BBOX, lon, lat), f"{name} vertex {lon},{lat} outside the fixture bbox"


def test_vector_source_forms(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    z = overlays.vector_source(ctx, "https://example.test/fz.zip|Flood_Zone_3", "flood_en_url")
    assert z.source == f"/vsizip/{ctx.src / 'flood_en_url.zip'}" and z.layer == "Flood_Zone_3" and z.open_options == ()
    fs = overlays.vector_source(ctx, "https://services.arcgis.com/x/arcgis/rest/services/CRoW/FeatureServer/0", "access_en_url")
    assert fs.source == "https://services.arcgis.com/x/arcgis/rest/services/CRoW/FeatureServer/0/query?where=1%3D1&outFields=*&f=json"
    assert fs.open_options == ("-oo", "FEATURE_SERVER_PAGING=YES") and fs.layer is None
    plain = overlays.vector_source(ctx, "https://example.test/zones.geojson", "x")
    assert plain.source == "https://example.test/zones.geojson"
    assert len(runner.find("aria2c")) == 1


def test_ogr_to_assembles_reprojection_with_optional_spat(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    src = overlays.VectorSource("/vsizip//tmp/a.zip", ("-oo", "X=Y"), "layer1")
    overlays.ogr_to(ctx, "FlatGeobuf", tmp_path / "out.fgb", src, spat=FIXTURE_BBOX)
    assert runner.calls[0] == ["ogr2ogr", "-f", "FlatGeobuf", "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI",
                               "-spat", "-1.56", "50.87", "-1.46", "50.97", "-oo", "X=Y", str(tmp_path / "out.fgb"), "/vsizip//tmp/a.zip", "layer1"]
    overlays.ogr_to(ctx, "GeoJSON", tmp_path / "out.geojson", overlays.VectorSource("in.geojson"))
    assert runner.calls[1] == ["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI", str(tmp_path / "out.geojson"), "in.geojson"]


def test_finalise_applies_the_5mb_rule(tmp_path):
    runner = FakeRunner(files={"water.pmtiles": b"tiles"})
    ctx = make_ctx(tmp_path, runner=runner)
    staged = tmp_path / "staged"
    staged.mkdir()
    small = tmp_path / "health.geojson"
    small.write_bytes(POINT_FC)
    assert overlays.finalise(ctx, "health", small, staged) == ("geojson", "health.geojson")
    assert (staged / "health.geojson").read_bytes() == POINT_FC
    big = tmp_path / "water.geojson"
    big.write_bytes(b"{" + b" " * overlays.SIZE_RULE_BYTES + b"}")
    assert overlays.finalise(ctx, "water", big, staged) == ("pmtiles", "water.pmtiles")
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:5] == ["-o", str(staged / "water.pmtiles"), "-l", "water"]
    assert "-zg" in tippe and "--coalesce-densest-as-needed" in tippe and "--detect-shared-borders" in tippe and tippe[-1] == str(big)


def test_build_footpaths_uses_designation_first_zoom_rule(tmp_path):
    runner = FakeRunner(files={"footpaths.pmtiles": b"fp"})
    ctx = make_ctx(tmp_path, runner=runner)
    work, staged = tmp_path / "work", tmp_path / "staged"
    work.mkdir(); staged.mkdir()
    out = overlays.build_footpaths(ctx, ctx.src / "fixture.osm.pbf", work, staged)
    assert out == staged / "footpaths.pmtiles" and out.exists()
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "w/highway=path,footway,bridleway,track,cycleway,steps" and tags[-2] == str(ctx.src / "fixture.osm.pbf")
    export = runner.find("osmium", "export")[0]
    assert "--geometry-types=linestring" in export and export[export.index("-c") + 1].endswith("export/paths.json") and "-f" in export and export[export.index("-f") + 1] == "geojsonseq"
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:8] == ["-o", str(staged / "footpaths.pmtiles"), "-l", "footpaths", "-Z10", "-z15", "-P"]
    assert "--drop-densest-as-needed" in tippe and "--extend-zooms-if-still-dropping" in tippe
    assert tippe[tippe.index("-j") + 1] == '{"footpaths":["any",[">=","$zoom",13],["has","designation"]]}'
    assert tippe[-1] == str(work / "paths.geojsonseq")


def test_build_osm_overlay_points_use_point_on_surface_and_polygons_do_not(tmp_path):
    runner = FakeRunner(files={"_raw.geojson": POINT_FC, "health.geojson": POINT_FC})
    ctx = make_ctx(tmp_path, runner=runner)
    work = tmp_path / "work"
    work.mkdir()
    health = next(o for o in overlays.OSM_OVERLAYS if o.id == "health")
    out = overlays.build_osm_overlay(ctx, health, ctx.src / "in.pbf", work)
    assert out == work / "health.geojson"
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "nwr/amenity=hospital,pharmacy,doctors"
    export = runner.find("osmium", "export")[0]
    assert "--add-unique-id=type_id" in export and export[export.index("-c") + 1].endswith("export/pois.json")
    ogr = runner.find("ogr2ogr")[0]
    assert ogr[-1] == "SELECT ST_PointOnSurface(geometry) AS geometry, * FROM health_raw" and ogr[ogr.index("-dialect") + 1] == "sqlite"
    water = next(o for o in overlays.OSM_OVERLAYS if o.id == "water")
    out = overlays.build_osm_overlay(ctx, water, ctx.src / "in.pbf", work)
    assert out == work / "water_raw.geojson"
    tags = runner.find("osmium", "tags-filter")[1]
    assert tags[-3:] == ["nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works"]
    assert len(runner.find("ogr2ogr")) == 1


def test_osm_overlay_table_matches_the_spec():
    table = {o.id: (o.filters, o.points) for o in overlays.OSM_OVERLAYS}
    assert set(table) == {"health", "fuel", "water", "rail", "chemical-sites", "airports-military"}
    assert table["fuel"] == (("nwr/amenity=fuel",), True)
    assert table["rail"] == (("nwr/railway=station",), True)
    assert table["chemical-sites"] == (("nwr/industrial=chemical,refinery,oil",), True)
    assert table["airports-military"] == (("nwr/aeroway=aerodrome", "nwr/military=*"), False)


def test_flood_zones_fixture_uses_the_committed_sample_with_spat_and_named_layer(tmp_path):
    runner = FakeRunner(files={"flood-zones.pmtiles": b"fz"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    work, staged = tmp_path / "work", tmp_path / "staged"
    work.mkdir(); staged.mkdir()
    out, layers = overlays.build_flood_zones(ctx, work, staged)
    assert out == staged / "flood-zones.pmtiles" and layers == ["flood_england"]
    ogr = runner.find("ogr2ogr")[0]
    assert ogr[-1] == str(SAMPLES / "flood-england-sample.geojson") and "-spat" in ogr
    tippe = runner.find("tippecanoe")[0]
    assert tippe[1:9] == ["-o", str(staged / "flood-zones.pmtiles"), "-Z8", "-z14", "-P", "--detect-shared-borders", "--coalesce-densest-as-needed", "--simplification=6"]
    assert tippe[-2:] == ["-L", f"flood_england:{work / 'flood_england.fgb'}"]


def test_flood_zones_full_mode_skips_blank_regions_and_needs_at_least_one(tmp_path, caplog):
    runner = FakeRunner(files={"flood-zones.pmtiles": b"fz"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner,
                   versions={"FLOOD_EN_URL": "https://example.test/ea.zip|Flood_Zones_3", "FLOOD_SC_URL": "https://example.test/sepa/FeatureServer/2"})
    work, staged = tmp_path / "work", tmp_path / "staged"
    work.mkdir(); staged.mkdir()
    _, layers = overlays.build_flood_zones(ctx, work, staged)
    assert layers == ["flood_england", "flood_scotland"]
    assert "FLOOD_WA_URL is blank" in caplog.text and "FLOOD_NI_URL is blank" in caplog.text
    tippe = runner.find("tippecanoe")[0]
    assert [a for a in tippe if a.startswith("flood_")] == [f"flood_england:{work / 'flood_england.fgb'}", f"flood_scotland:{work / 'flood_scotland.fgb'}"]
    empty = make_ctx(tmp_path / "e", fixture=False, runner=FakeRunner())
    with pytest.raises(BuildError, match="FLOOD_"):
        overlays.build_flood_zones(empty, tmp_path / "e" / "w", tmp_path / "e" / "s")


def test_nuclear_sites_rejects_short_or_non_point_lists(tmp_path, monkeypatch):
    ctx = make_ctx(tmp_path)
    bad_repo = tmp_path / "repo"
    (bad_repo / "tools" / "map-styles" / "data").mkdir(parents=True)
    (bad_repo / "tools" / "map-styles" / "data" / "nuclear-sites.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"name": "x"}, "geometry": {"type": "Point", "coordinates": [-1, 51]}}]}))
    ctx.repo = bad_repo
    with pytest.raises(BuildError, match="20"):
        overlays.nuclear_sites(ctx)
    ctx.repo = REPO
    assert len(overlays.nuclear_sites(ctx)["features"]) >= 20


def test_overlays_step_end_to_end_fixture(tmp_path):
    runner = FakeRunner(files={"fixture.osm.pbf": b"pbf", "_raw.geojson": POINT_FC, "health.geojson": POINT_FC, "fuel.geojson": POINT_FC,
                               "rail.geojson": POINT_FC, "chemical-sites.geojson": POINT_FC, "access_england.geojson": POINT_FC,
                               "footpaths.pmtiles": b"fp", "flood-zones.pmtiles": b"fz"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    overlays.OverlaysStep().run(ctx)
    out = ctx.out / "overlays"
    index = json.loads((out / "index.json").read_text())
    assert set(index) == {"footpaths", "health", "fuel", "water", "rail", "chemical-sites", "airports-military", "flood-zones", "access-land", "nuclear-sites"}
    assert index["footpaths"] == {"kind": "pmtiles", "file": "overlays/footpaths.pmtiles", "layers": ["footpaths"], "size_bytes": 2}
    assert index["flood-zones"]["layers"] == ["flood_england"] and index["flood-zones"]["coverage"] == ["england"]
    assert index["health"]["kind"] == "geojson" and index["health"]["features"] == 1
    assert index["chemical-sites"]["features"] == 1 + 10, "OSM points plus the hand-authored list"
    assert index["access-land"] == {"kind": "geojson", "file": "overlays/access-land.geojson", "coverage": ["england"], "size_bytes": (out / "access-land.geojson").stat().st_size}
    assert index["nuclear-sites"]["features"] >= 20
    for info in index.values():
        assert (ctx.out / info["file"]).exists(), info
    assert json.loads((out / "access-land.geojson").read_text())["features"][0]["properties"]["region"] == "england"
    assert not (ctx.incoming / "overlays").exists()
    assert json.loads((ctx.out / "overlays.json").read_text())["osm_input"] == "fixture.osm.pbf"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_overlays.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.overlays'`.

- [ ] **Step 3: Implement `overlays.py` and register the step**

`api/sos/mapbuild/overlays.py`:

```python
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


OSM_OVERLAYS: tuple[OsmOverlay, ...] = (
    OsmOverlay("health", ("nwr/amenity=hospital,pharmacy,doctors",), True),
    OsmOverlay("fuel", ("nwr/amenity=fuel",), True),
    OsmOverlay("water", ("nwr/landuse=reservoir", "nwr/water=reservoir", "nwr/man_made=water_works"), False),
    OsmOverlay("rail", ("nwr/railway=station",), True),
    OsmOverlay("chemical-sites", ("nwr/industrial=chemical,refinery,oil",), True),
    OsmOverlay("airports-military", ("nwr/aeroway=aerodrome", "nwr/military=*"), False),
)
HAND_AUTHORED = {"chemical-sites": "chemical-sites.geojson"}
FLOOD_REGIONS = (("england", "FLOOD_EN_URL"), ("wales", "FLOOD_WA_URL"), ("scotland", "FLOOD_SC_URL"),
                 ("ni", "FLOOD_NI_URL"), ("roi", "FLOOD_IE_URL"))
ACCESS_REGIONS = (("england", "ACCESS_EN_URL"), ("wales", "ACCESS_WA_URL"))


@dataclass(frozen=True)
class VectorSource:
    source: str
    open_options: tuple[str, ...] = ()
    layer: str | None = None


def vector_source(ctx: Context, spec: str, name: str) -> VectorSource:
    """Turn a versions.env value into what ogr2ogr reads: /vsizip/ of a cached zip, a paged FeatureServer query, or the URL."""
    url, _, layer = spec.partition("|")
    layer = layer.strip() or None
    url = url.strip()
    if url.lower().endswith(".zip"):
        path = ctx.download(url, f"{name}.zip")
        return VectorSource(f"/vsizip/{path}", (), layer)
    if "/FeatureServer/" in url or "/MapServer/" in url:
        return VectorSource(f"{url.rstrip('/')}/query?where=1%3D1&outFields=*&f=json", ("-oo", "FEATURE_SERVER_PAGING=YES"), layer)
    return VectorSource(url, (), layer)


def ogr_to(ctx: Context, fmt: str, dest: Path, src: VectorSource, *, spat: BBox | None = None) -> None:
    cmd = ["ogr2ogr", "-f", fmt, "-t_srs", "EPSG:4326", "-nlt", "PROMOTE_TO_MULTI"]
    if spat:
        cmd += ["-spat", *bbox_args(spat)]
    cmd += [*src.open_options, str(dest), src.source]
    if src.layer:
        cmd.append(src.layer)
    dest.unlink(missing_ok=True)
    ctx.run(cmd)


def region_sources(ctx: Context, regions: tuple[tuple[str, str], ...], *, fixture_sample: str) -> list[tuple[str, VectorSource]]:
    if ctx.fixture:
        sample = ctx.repo / "api" / "tests" / "fixtures" / "maps" / "src" / fixture_sample
        return [("england", VectorSource(str(sample)))]
    found = []
    for region, key in regions:
        spec = ctx.versions.get(key, "")
        if not spec:
            log.warning("[overlays] %s is blank; %s skipped", key, region)
            continue
        found.append((region, vector_source(ctx, spec, key.lower())))
    return found


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


def build_osm_overlay(ctx: Context, overlay: OsmOverlay, pbf: Path, work: Path) -> Path:
    filtered = work / f"{overlay.id}.osm.pbf"
    ctx.run(["osmium", "tags-filter", "--overwrite", "-o", str(filtered), str(pbf), *overlay.filters])
    raw = work / f"{overlay.id}_raw.geojson"
    ctx.run(["osmium", "export", "--overwrite", "-f", "geojson", "--add-unique-id=type_id",
             "-c", str(export_config(ctx, "pois")), "-o", str(raw), str(filtered)])
    if not overlay.points:
        return raw
    out = work / f"{overlay.id}.geojson"
    out.unlink(missing_ok=True)
    ctx.run(["ogr2ogr", "-f", "GeoJSON", str(out), str(raw), "-dialect", "sqlite",
             "-sql", f"SELECT ST_PointOnSurface(geometry) AS geometry, * FROM {raw.stem}"])
    return out


def finalise(ctx: Context, overlay_id: str, geojson: Path, staged_dir: Path) -> tuple[str, str]:
    """Copy as GeoJSON, or tile with tippecanoe when the file exceeds 5 MB (spec section 9)."""
    if geojson.stat().st_size <= SIZE_RULE_BYTES:
        shutil.copyfile(geojson, staged_dir / f"{overlay_id}.geojson")
        return "geojson", f"{overlay_id}.geojson"
    out = staged_dir / f"{overlay_id}.pmtiles"
    ctx.run(["tippecanoe", "-o", str(out), "-l", overlay_id, "-zg", "--coalesce-densest-as-needed", "--detect-shared-borders",
             "--extend-zooms-if-still-dropping", "--force", str(geojson)])
    return "pmtiles", f"{overlay_id}.pmtiles"


def build_flood_zones(ctx: Context, work: Path, staged_dir: Path) -> tuple[Path, list[str]]:
    built: list[tuple[str, Path]] = []
    for region, src in region_sources(ctx, FLOOD_REGIONS, fixture_sample="flood-england-sample.geojson"):
        fgb = work / f"flood_{region}.fgb"
        ogr_to(ctx, "FlatGeobuf", fgb, src, spat=ctx.bbox if ctx.fixture else None)
        built.append((region, fgb))
    if not built:
        raise BuildError("no flood-zone sources configured: set FLOOD_EN_URL, FLOOD_WA_URL, FLOOD_SC_URL, FLOOD_NI_URL or FLOOD_IE_URL")
    out = staged_dir / "flood-zones.pmtiles"
    cmd = ["tippecanoe", "-o", str(out), "-Z8", "-z14", "-P", "--detect-shared-borders", "--coalesce-densest-as-needed",
           "--simplification=6", "--force"]
    for region, fgb in built:
        cmd += ["-L", f"flood_{region}:{fgb}"]
    ctx.run(cmd)
    return out, [f"flood_{region}" for region, _ in built]


def build_access_land(ctx: Context, work: Path, staged_dir: Path) -> tuple[str, str, list[str]]:
    collections: list[dict] = []
    regions: list[str] = []
    for region, src in region_sources(ctx, ACCESS_REGIONS, fixture_sample="access-england-sample.geojson"):
        geojson = work / f"access_{region}.geojson"
        ogr_to(ctx, "GeoJSON", geojson, src, spat=ctx.bbox if ctx.fixture else None)
        obj = load_geojson(geojson)
        for feature in obj["features"]:
            feature.setdefault("properties", {})["region"] = region
        collections.append(obj)
        regions.append(region)
    if not collections:
        raise BuildError("no access-land sources configured: set ACCESS_EN_URL or ACCESS_WA_URL")
    combined = work / "access-land.geojson"
    combined.write_text(json.dumps(merge_feature_collections(collections)))
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
                                "coverage": [layer.removeprefix("flood_") for layer in layers]}
        kind, name, regions = build_access_land(ctx, work, staged_dir)
        index["access-land"] = {"kind": kind, "file": f"overlays/{name}", "coverage": regions}

        nuclear = nuclear_sites(ctx)
        (staged_dir / "nuclear-sites.geojson").write_text(json.dumps(nuclear))
        index["nuclear-sites"] = {"kind": "geojson", "file": "overlays/nuclear-sites.geojson", "features": len(nuclear["features"])}

        for entry in index.values():
            entry["size_bytes"] = (staged_dir / Path(entry["file"]).name).stat().st_size
        (staged_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
        ctx.commit("overlays")
        log.info("[overlays] %s", ", ".join(f"{k}={v['kind']}" for k, v in index.items()))
        ctx.write_sidecar("overlays", {"step": self.id, "osm_input": pbf.name, "overlays": sorted(index)})
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.hillshade import HillshadeStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.overlays import OverlaysStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), HillshadeStep(), OverlaysStep(), StylesStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_overlays.py -q 2>&1 | tail -3`
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/overlays.py tools/map-styles/export/paths.json tools/map-styles/export/pois.json \
        tools/map-styles/data/nuclear-sites.geojson tools/map-styles/data/chemical-sites.geojson \
        api/tests/fixtures/maps/src api/sos/buildmaps.py api/tests/test_buildmaps_overlays.py
git commit -m "feat(maps): overlays step builds footpaths, flood zones, access land, POI and site overlays with the 5 MB rule"
```

---

### Task 8: Step `places` — OS Open Names plus OSM place nodes → `places.csv.gz`

**Files:**
- Create: `api/sos/mapbuild/places.py`
- Create: `tools/map-styles/export/places.json`
- Create: `api/tests/test_buildmaps_places.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `os_fetch` (Task 4); `osm_input`, `region_polygons`, `export_config`, `NON_GB`, `REGION_LABELS` (Task 5); `read_geojsonseq` (Task 1); `pyproj` (the `maps` extra).
- Produces: `PlacesStep` (`id == "places"`, output `places.csv.gz`), `make_transformer(inverse=False)`, `read_header(zf)`, `os_names_rows(zf, header)`, `reduce_os_rows(rows, *, os_bbox=None)`, `transform_rows(rows, transformer, *, bbox=None)`, `os_bbox_for(bbox, inverse_transformer, margin_m=2000)`, `osm_place_rows(features, region_label)`, `osm_places(ctx, work)`, `write_places(path, rows) -> int`, `COLUMNS`, `LOCAL_TYPES`.
- Output contract (consumed by plan 01's `sos.places` import into `fts_places`): gzip CSV with a header row `name,kind,lat,lon,region,postcode`; `kind` is one of `city, town, village, hamlet, other-settlement, postcode, named-road` (OS) or `city, town, village, hamlet, suburb, locality` (OSM); `lat`/`lon` are WGS84 rounded to 5 decimals; `postcode` is the postcode for `postcode` rows, the postcode district otherwise, empty when unknown; roads are one row per (name, populated place) at the mean of their sections, with the populated place in `region`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_buildmaps_places.py`:

```python
import csv
import gzip
import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import places
from sos.mapbuild.common import BuildError, FIXTURE_BBOX
from tests.mapbuild_helpers import FakeRunner, make_ctx

NAMES_API = "https://api.os.uk/downloads/v1/products/OpenNames/downloads"
NAMES_ENTRIES = [{"md5": "4a7d2d0d24be0470771b9cc170ca2aee", "size": 103259564, "fileName": "opname_csv_gb.zip",
                  "url": "https://api.os.uk/downloads/v1/products/OpenNames/downloads?area=GB&format=CSV&redirect", "format": "CSV", "area": "GB"}]
HEADER = ["ID", "NAMES_URI", "NAME1", "NAME1_LANG", "TYPE", "LOCAL_TYPE", "GEOMETRY_X", "GEOMETRY_Y", "POSTCODE_DISTRICT",
          "POPULATED_PLACE", "DISTRICT_BOROUGH", "COUNTY_UNITARY", "REGION", "COUNTRY"]


def _row(name, local_type, x, y, *, district="SO40", place="", county="Hampshire", region="South East", country="England"):
    return {"ID": "1", "NAMES_URI": "", "NAME1": name, "NAME1_LANG": "", "TYPE": "", "LOCAL_TYPE": local_type, "GEOMETRY_X": str(x),
            "GEOMETRY_Y": str(y), "POSTCODE_DISTRICT": district, "POPULATED_PLACE": place, "DISTRICT_BOROUGH": "",
            "COUNTY_UNITARY": county, "REGION": region, "COUNTRY": country}


class FakeTransformer:
    """27700 -> 4326 stand-in: linear around (440000, 110000) = (-1.5, 50.9)."""

    def __init__(self, inverse=False):
        self.inverse = inverse

    def transform(self, xs, ys):
        if self.inverse:
            return ([440000 + (lon + 1.5) * 70000 for lon in xs], [110000 + (lat - 50.9) * 111000 for lat in ys])
        return ([-1.5 + (x - 440000) / 70000 for x in xs], [50.9 + (y - 110000) / 111000 for y in ys])


def _names_zip(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Doc/OS_Open_Names_Header.csv", ",".join(HEADER) + "\n")
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=HEADER)
        for row in rows:
            writer.writerow(row)
        zf.writestr("Data/SU41.csv", out.getvalue())
        zf.writestr("Data/readme.txt", "not a csv")
    return buf.getvalue()


SAMPLE_ROWS = [
    _row("Totton", "Town", 436000, 112500, district="SO40"),
    _row("Eling", "Village", 436800, 112200, district="SO40"),
    _row("SO40 3ZZ", "Postcode", 436100, 112600, district="SO40"),
    _row("High Street", "Section Of Named Road", 436000, 112000, place="Totton"),
    _row("High Street", "Section Of Named Road", 436200, 112400, place="Totton"),
    _row("High Street", "Named Road", 700000, 300000, place="Lowestoft", region="East of England"),
    _row("Solent", "Sea", 440000, 100000),
    _row("Somewhere", "Hamlet", 480000, 140000, region="", county="", country="Wales"),
    _row("", "Town", 436000, 112500),
]


def test_read_header_and_rows_come_from_the_zip():
    with zipfile.ZipFile(io.BytesIO(_names_zip(SAMPLE_ROWS))) as zf:
        header = places.read_header(zf)
        assert header == HEADER
        rows = list(places.os_names_rows(zf, header))
    assert len(rows) == len(SAMPLE_ROWS) and rows[0]["NAME1"] == "Totton" and rows[0]["LOCAL_TYPE"] == "Town"


def test_reduce_os_rows_filters_types_collapses_roads_and_sets_postcodes():
    reduced = places.reduce_os_rows(SAMPLE_ROWS)
    by_name = {(r[0], r[1]): r for r in reduced}
    assert set(by_name) == {("Totton", "town"), ("Eling", "village"), ("SO40 3ZZ", "postcode"), ("High Street", "named-road"), ("Somewhere", "hamlet")}
    assert [r for r in reduced if r[0] == "High Street"] == [("High Street", "named-road", 436100.0, 112200.0, "Totton", "SO40"),
                                                            ("High Street", "named-road", 700000.0, 300000.0, "Lowestoft", "SO40")]
    assert by_name[("SO40 3ZZ", "postcode")][5] == "SO40 3ZZ"
    assert by_name[("Totton", "town")][4] == "South East" and by_name[("Totton", "town")][5] == "SO40"
    assert by_name[("Somewhere", "hamlet")][4] == "Wales", "REGION then COUNTY_UNITARY then COUNTRY"
    assert not any(r[0] == "Solent" for r in reduced) and not any(r[0] == "" for r in reduced)


def test_reduce_os_rows_prefilters_on_the_os_bbox():
    reduced = places.reduce_os_rows(SAMPLE_ROWS, os_bbox=(430000, 110000, 450000, 120000))
    assert {r[0] for r in reduced} == {"Totton", "Eling", "SO40 3ZZ", "High Street"}


def test_transform_rows_rounds_and_filters_by_bbox():
    rows = [("Totton", "town", 440000.0, 110000.0, "South East", "SO40"), ("Far", "town", 600000.0, 110000.0, "", "")]
    out = places.transform_rows(rows, FakeTransformer(), bbox=FIXTURE_BBOX)
    assert out == [["Totton", "town", 50.9, -1.5, "South East", "SO40"]]
    assert len(places.transform_rows(rows, FakeTransformer())) == 2


def test_os_bbox_for_uses_the_inverse_transformer_with_a_margin():
    xmin, ymin, xmax, ymax = places.os_bbox_for(FIXTURE_BBOX, FakeTransformer(inverse=True), margin_m=1000)
    assert xmin == pytest.approx(440000 + (-1.56 + 1.5) * 70000 - 1000)
    assert xmax == pytest.approx(440000 + (-1.46 + 1.5) * 70000 + 1000)
    assert ymin == pytest.approx(110000 + (50.87 - 50.9) * 111000 - 1000)
    assert ymax == pytest.approx(110000 + (50.97 - 50.9) * 111000 + 1000)


def test_osm_place_rows_keeps_named_place_nodes_only():
    features = [
        {"type": "Feature", "properties": {"name": "Newry", "place": "city"}, "geometry": {"type": "Point", "coordinates": [-6.34, 54.1753]}},
        {"type": "Feature", "properties": {"place": "village"}, "geometry": {"type": "Point", "coordinates": [-6.0, 54.0]}},
        {"type": "Feature", "properties": {"name": "Islet", "place": "island"}, "geometry": {"type": "Point", "coordinates": [-6.0, 54.0]}},
        {"type": "Feature", "properties": {"name": "Area", "place": "town"}, "geometry": {"type": "Polygon", "coordinates": []}},
    ]
    assert places.osm_place_rows(features, "Northern Ireland") == [["Newry", "city", 54.1753, -6.34, "Northern Ireland", ""]]


def test_write_places_writes_gzip_csv_with_header(tmp_path):
    path = tmp_path / "places.csv.gz"
    n = places.write_places(path, [["Totton", "town", 50.9, -1.5, "South East", "SO40"], ["Newry", "city", 54.1753, -6.34, "Northern Ireland", ""]])
    assert n == 2
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["name", "kind", "lat", "lon", "region", "postcode"]
    assert rows[1] == ["Totton", "town", "50.9", "-1.5", "South East", "SO40"] and rows[2][5] == ""


def test_osm_places_full_mode_clips_per_region(tmp_path):
    seq = json.dumps({"type": "Feature", "properties": {"name": "Newry", "place": "city"}, "geometry": {"type": "Point", "coordinates": [-6.34, 54.1753]}}) + "\n"
    runner = FakeRunner(files={"places_ni.geojsonseq": seq.encode(), "places_roi.geojsonseq": b""})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    regions = ctx.src / "regions"
    regions.mkdir()
    for region in ("roi", "iom", "jersey", "guernsey", "ni"):
        feats = [] if region in ("iom", "jersey", "guernsey") else [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[-8, 54], [-5, 54], [-5, 55.5], [-8, 54]]]}}]
        (regions / f"{region}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    work = tmp_path / "work"
    work.mkdir()
    rows = places.osm_places(ctx, work)
    assert rows == [["Newry", "city", 54.1753, -6.34, "Northern Ireland", ""]]
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "n/place=city,town,village,hamlet,suburb,locality"
    export = runner.find("osmium", "export")[0]
    assert "--geometry-types=point" in export and export[export.index("-c") + 1].endswith("export/places.json")
    clips = runner.find("ogr2ogr")
    assert [c[c.index("-clipsrc") + 1] for c in clips] == [str(regions / "roi.geojson"), str(regions / "ni.geojson")], "regions without a polygon are skipped"
    assert clips[0][1:3] == ["-f", "GeoJSONSeq"]


def test_osm_places_fixture_mode_runs_osmium_but_adds_no_rows(tmp_path):
    runner = FakeRunner(files={"fixture.osm.pbf": b"pbf"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    assert places.osm_places(ctx, tmp_path / "work") == []
    assert len(runner.find("osmium")) == 3 and not runner.find("ogr2ogr")  # extract, tags-filter, export


@respx.mock
def test_places_step_fixture_end_to_end(tmp_path, monkeypatch):
    respx.get(NAMES_API).mock(return_value=httpx.Response(200, json=NAMES_ENTRIES))
    monkeypatch.setattr(places, "make_transformer", lambda inverse=False: FakeTransformer(inverse))
    runner = FakeRunner(files={"opname_csv_gb.zip": _names_zip(SAMPLE_ROWS), "fixture.osm.pbf": b"pbf"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    places.PlacesStep().run(ctx)
    with gzip.open(ctx.out / "places.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    names = sorted((r["name"], r["kind"]) for r in rows)
    assert names == [("Eling", "village"), ("High Street", "named-road"), ("SO40 3ZZ", "postcode"), ("Totton", "town")], "rows outside the fixture bbox are dropped"
    totton = next(r for r in rows if r["name"] == "Totton")
    assert -1.56 <= float(totton["lon"]) <= -1.46 and 50.87 <= float(totton["lat"]) <= 50.97
    side = json.loads((ctx.out / "places.json").read_text())
    assert side["rows"] == 4 and side["gb_rows"] == 4 and side["osm_rows"] == 0 and side["columns"] == list(places.COLUMNS)
    assert runner.find("aria2c")[0][-1] == NAMES_ENTRIES[0]["url"]


def test_make_transformer_needs_pyproj(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def no_pyproj(name, *args, **kwargs):
        if name == "pyproj":
            raise ImportError("no pyproj")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pyproj)
    with pytest.raises(BuildError, match=r"api\[maps\]"):
        places.make_transformer()
```

`tools/map-styles/export/places.json`:

```json
{
  "attributes": {"type": false, "id": false, "version": false, "changeset": false, "timestamp": false, "uid": false, "user": false, "way_nodes": false},
  "format_options": {},
  "linear_tags": false,
  "area_tags": false,
  "exclude_tags": [],
  "include_tags": ["name", "place", "population"]
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_places.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.places'`.

- [ ] **Step 3: Implement `places.py` and register the step**

`api/sos/mapbuild/places.py`:

```python
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
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.hillshade import HillshadeStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.overlays import OverlaysStep
    from sos.mapbuild.places import PlacesStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), HillshadeStep(), OverlaysStep(), PlacesStep(), StylesStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_places.py -q 2>&1 | tail -3`
Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/places.py tools/map-styles/export/places.json api/sos/buildmaps.py api/tests/test_buildmaps_places.py
git commit -m "feat(maps): places step builds places.csv.gz from OS Open Names and OSM place nodes"
```

---

### Task 9: Step `packs` — Organic Maps `.mwm` files, the Android APK, `packs/index.html` and `packs/index.json`

**Files:**
- Create: `api/sos/mapbuild/packs.py`
- Create: `api/tests/test_buildmaps_packs.py`
- Modify: `api/sos/buildmaps.py` (`all_steps`)

**Interfaces:**
- Consumes: `Context.download`, `Context.version` (Task 1); `httpx`; `install/versions.env` `ORGANICMAPS_TAG`, `ORGANICMAPS_CDN`, `ORGANICMAPS_APK_URL`, `ORGANICMAPS_APK_SHA256`.
- Produces: `PacksStep` (`id == "packs"`, outputs `packs/index.html`, `packs/index.json`), `countries_url(ctx)`, `fetch_countries(ctx) -> dict`, `leaves(node)`, `pack_ids(countries) -> list[str]` (exactly 24), `pack_sizes(countries)`, `pack_title(pack_id)`, `data_version(countries) -> str`, `render_index_html(version, packs, apk) -> str`, `index_json(version, packs, apk) -> dict`, `FIXTURE_IDS = ("Jersey",)`.
- Output contract (consumed by plan 01's `GET /api/map/config` for `packs` and `packs_index_url`): `packs/index.json` is `{"version": "260826", "apk": {"file", "url", "size_bytes", "sha256", "tag"} | null, "packs": [{"id", "title", "file", "url", "size_bytes", "expected_size_bytes"}], "index_url": "/maps/packs/index.html"}`; `packs[].url` is `/maps/packs/<id URL-encoded>.mwm`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_buildmaps_packs.py`:

```python
import json

import httpx
import pytest
import respx

from sos.mapbuild import packs
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx

UK_IDS = ["UK_England_East Midlands", "UK_England_East of England_Essex", "UK_England_East of England_Norfolk", "UK_England_Greater London",
          "UK_England_North East England", "UK_England_North West England_Manchester", "UK_England_North West England_Lancaster",
          "UK_England_South East_Brighton", "UK_England_South East_Oxford", "UK_England_South West England_Bristol",
          "UK_England_South West England_Cornwall", "UK_England_West Midlands", "UK_England_Yorkshire and the Humber",
          "UK_Northern Ireland", "UK_Scotland_North", "UK_Scotland_South", "UK_Wales"]
IE_IDS = ["Ireland_Connacht", "Ireland_Leinster", "Ireland_Munster", "Ireland_Northern Counties"]
COUNTRIES_URL = "https://raw.githubusercontent.com/organicmaps/organicmaps/2026.08.27-18-android/data/countries.json"


def _countries(size=10, drop=None):
    def leaf(i):
        return {"id": i, "s": size, "h": "hash"}
    uk = [leaf(i) for i in UK_IDS if i != drop]
    return {"v": 260826, "id": "Countries", "g": [
        {"id": "United Kingdom", "g": [{"id": "England", "g": uk[:13]}, *uk[13:]]},
        {"id": "Ireland", "g": [leaf(i) for i in IE_IDS]},
        leaf("Isle of Man"), leaf("Jersey"), leaf("Guernsey"),
        {"id": "France", "g": [leaf("France_Paris")]}, leaf("World"),
    ]}


def test_pack_ids_finds_exactly_the_24_uk_and_ireland_ids():
    ids = packs.pack_ids(_countries())
    assert len(ids) == 24 and ids == sorted(UK_IDS + IE_IDS + ["Isle of Man", "Jersey", "Guernsey"])
    assert "World" not in ids and "France_Paris" not in ids
    with pytest.raises(BuildError, match="23"):
        packs.pack_ids(_countries(drop="UK_Wales"))
    assert packs.pack_sizes(_countries(size=7))["Jersey"] == 7
    assert packs.data_version(_countries()) == "260826"


def test_pack_titles_read_naturally():
    assert packs.pack_title("UK_England_South East_Brighton") == "England – South East – Brighton"
    assert packs.pack_title("UK_Northern Ireland") == "Northern Ireland"
    assert packs.pack_title("Ireland_Munster") == "Ireland – Munster"
    assert packs.pack_title("Isle of Man") == "Isle of Man"


def test_index_html_carries_the_spec_instructions_and_no_external_urls():
    pack = {"id": "Jersey", "title": "Jersey", "file": "Jersey.mwm", "url": "/maps/packs/Jersey.mwm", "size_bytes": 2590086, "expected_size_bytes": 2590086}
    apk = {"file": "OrganicMaps-26082718-web-release.apk", "url": "/maps/packs/OrganicMaps-26082718-web-release.apk", "size_bytes": 64193127, "sha256": "ab", "tag": "2026.08.27-18-android"}
    page = packs.render_index_html("260826", [pack], apk)
    for text in ("Install the app first", "Android/data/app.organicmaps/files/260826/", "Android 11 and later block the browser",
                 "direct laptop link", "iPhone and iPad are not supported", 'href="/maps/packs/Jersey.mwm"',
                 'href="/maps/packs/OrganicMaps-26082718-web-release.apk"', "Data version 260826"):
        assert text in page, text
    assert "http://" not in page and "https://" not in page
    without = packs.render_index_html("260826", [pack], None)
    assert "not included in this build" in without and ".apk" not in without


def test_index_json_shape():
    doc = packs.index_json("260826", [{"id": "Jersey"}], None)
    assert doc == {"version": "260826", "apk": None, "packs": [{"id": "Jersey"}], "index_url": "/maps/packs/index.html"}


@respx.mock
def test_packs_step_fixture_downloads_jersey_only_and_no_apk(tmp_path):
    respx.get(COUNTRIES_URL).mock(return_value=httpx.Response(200, json=_countries(size=3)))
    runner = FakeRunner(files={"Jersey.mwm": b"mwm"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    packs.PacksStep().run(ctx)
    downloads = [c[-1] for c in runner.find("aria2c")]
    assert downloads == ["https://example.test/maps/260826/Jersey.mwm"]
    index = json.loads((ctx.out / "packs" / "index.json").read_text())
    assert index["version"] == "260826" and index["apk"] is None
    assert index["packs"] == [{"id": "Jersey", "title": "Jersey", "file": "Jersey.mwm", "url": "/maps/packs/Jersey.mwm", "size_bytes": 3, "expected_size_bytes": 3}]
    assert (ctx.out / "packs" / "Jersey.mwm").read_bytes() == b"mwm"
    assert "Android/data/app.organicmaps/files/260826/" in (ctx.out / "packs" / "index.html").read_text()
    assert json.loads((ctx.out / "packs.json").read_text())["ids"] == ["Jersey"]


@respx.mock
def test_packs_step_full_downloads_24_packs_and_the_apk_with_sha256(tmp_path):
    respx.get(COUNTRIES_URL).mock(return_value=httpx.Response(200, json=_countries(size=10)))
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    packs.PacksStep().run(ctx)
    urls = [c[-1] for c in runner.find("aria2c")]
    assert len(urls) == 25
    assert "https://example.test/maps/260826/UK_England_South%20East_Brighton.mwm" in urls
    assert "https://example.test/maps/260826/Isle%20of%20Man.mwm" in urls
    apk_cmd = next(c for c in runner.find("aria2c") if c[-1].endswith(".apk"))
    assert "--checksum=sha-256=1f19229d95b731862349d504b150dad63eb405caa83e98c96bfe93b7acae3c7a" in apk_cmd
    index = json.loads((ctx.out / "packs" / "index.json").read_text())
    assert len(index["packs"]) == 24 and index["apk"]["file"] == "OrganicMaps-26082718-web-release.apk"
    assert index["packs"][0]["url"] == "/maps/packs/Guernsey.mwm"
    assert (ctx.out / "packs" / "OrganicMaps-26082718-web-release.apk").exists()


@respx.mock
def test_packs_step_rejects_size_mismatch(tmp_path):
    respx.get(COUNTRIES_URL).mock(return_value=httpx.Response(200, json=_countries(size=99)))
    ctx = make_ctx(tmp_path, fixture=True, runner=FakeRunner(files={"Jersey.mwm": b"short"}))
    with pytest.raises(BuildError, match="Jersey.*99"):
        packs.PacksStep().run(ctx)
    assert not (ctx.out / "packs").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_packs.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.packs'`.

- [ ] **Step 3: Implement `packs.py` and register the step**

`api/sos/mapbuild/packs.py`:

```python
"""Step `packs`: Organic Maps .mwm files for the 24 UK and Ireland ids, the Android APK and the packs index."""
from __future__ import annotations

import html
import json
import os
import shutil
from pathlib import Path
from urllib.parse import quote

import httpx

from .common import BuildError, Context, log

EXPECTED_PACKS = 24
SINGLE_IDS = ("Isle of Man", "Jersey", "Guernsey")
FIXTURE_IDS = ("Jersey",)
INDEX_URL = "/maps/packs/index.html"


def countries_url(ctx: Context) -> str:
    return f"https://raw.githubusercontent.com/organicmaps/organicmaps/{ctx.version('ORGANICMAPS_TAG')}/data/countries.json"


def fetch_countries(ctx: Context) -> dict:
    url = countries_url(ctx)
    response = httpx.get(url, timeout=60, follow_redirects=True)
    if response.status_code != 200:
        raise BuildError(f"{url} returned {response.status_code}")
    return response.json()


def leaves(node: dict) -> list[dict]:
    if "g" in node:
        return [leaf for child in node["g"] for leaf in leaves(child)]
    return [node]


def pack_ids(countries: dict) -> list[str]:
    ids = sorted(leaf["id"] for leaf in leaves(countries)
                 if leaf["id"].startswith("UK_") or leaf["id"].startswith("Ireland_") or leaf["id"] in SINGLE_IDS)
    if len(ids) != EXPECTED_PACKS:
        raise BuildError(f"expected {EXPECTED_PACKS} Organic Maps pack ids, found {len(ids)}: {ids}")
    return ids


def pack_sizes(countries: dict) -> dict[str, int]:
    return {leaf["id"]: int(leaf.get("s", 0)) for leaf in leaves(countries)}


def data_version(countries: dict) -> str:
    return str(countries["v"])


def pack_title(pack_id: str) -> str:
    if pack_id.startswith("UK_"):
        return pack_id[len("UK_"):].replace("_", " – ")
    if pack_id.startswith("Ireland_"):
        return "Ireland – " + pack_id[len("Ireland_"):].replace("_", " – ")
    return pack_id


def index_json(version: str, packs: list[dict], apk: dict | None) -> dict:
    return {"version": version, "apk": apk, "packs": packs, "index_url": INDEX_URL}


def render_index_html(version: str, packs: list[dict], apk: dict | None) -> str:
    rows = "\n".join(
        f'      <tr><td><a href="{html.escape(p["url"])}">{html.escape(p["file"])}</a></td>'
        f'<td>{html.escape(p["title"])}</td><td>{p["size_bytes"] / 1e6:.0f} MB</td></tr>' for p in packs)
    if apk:
        apk_line = (f'Download <a href="{html.escape(apk["url"])}">{html.escape(apk["file"])}</a> '
                    f'({apk["size_bytes"] / 1e6:.0f} MB) and open it on the phone to install it. '
                    "Allow installs from your browser if Android asks.")
    else:
        apk_line = "The Android app is not included in this build."
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOS phone map packs</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  code {{ background: #eee; padding: 0 .25rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ text-align: left; padding: .4rem .5rem; border-bottom: 1px solid #ccc; }}
  .warn {{ border-left: 4px solid #c8102e; padding-left: .75rem; }}
</style>
</head>
<body>
<h1>Phone map packs (Organic Maps)</h1>
<p>These files give an Android phone its own offline map of the UK, the Republic of Ireland, the Isle of Man and the Channel Islands, usable when the phone cannot reach this box.</p>
<ol>
  <li><strong>Install the app first.</strong> {apk_line}</li>
  <li><strong>Copy the map files from a PC over USB.</strong> Plug the phone into a computer, choose <em>File transfer</em> on the phone, then copy the <code>.mwm</code> files below into <code>Android/data/app.organicmaps/files/{version}/</code> on the phone (create the folder if it is missing). Android 11 and later block the browser from saving into that folder, so downloading a <code>.mwm</code> directly on the phone does not work.</li>
  <li><strong>Getting the files onto the PC:</strong> the intended route is the Ethernet <em>direct laptop link</em> from the System screen: plug a laptop into the box with an Ethernet cable and download the files from this page. <code>adb push</code> works too.</li>
  <li>Open Organic Maps. The maps appear under <em>Downloaded maps</em>.</li>
</ol>
<p class="warn"><strong>iPhone and iPad are not supported.</strong> iOS has no way to load map files from outside the App Store.</p>
<table>
  <thead><tr><th>File</th><th>Area</th><th>Size</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
<p>Map data &copy; OpenStreetMap contributors, &copy; Organic Maps. Data version {version}.</p>
</body>
</html>
"""


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.unlink(missing_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


class PacksStep:
    id = "packs"

    def outputs(self, ctx: Context) -> list[str]:
        return ["packs/index.html", "packs/index.json"]

    def run(self, ctx: Context) -> None:
        countries = fetch_countries(ctx)
        version = data_version(countries)
        ids = pack_ids(countries)
        sizes = pack_sizes(countries)
        wanted = [i for i in ids if i in FIXTURE_IDS] if ctx.fixture else ids
        cdn = ctx.version("ORGANICMAPS_CDN")
        staged = ctx.stage("packs")
        staged.mkdir()
        packs: list[dict] = []
        for pack_id in wanted:
            source = ctx.download(f"{cdn}/{version}/{quote(pack_id)}.mwm", f"packs/{version}/{pack_id}.mwm")
            size = source.stat().st_size
            if size != sizes.get(pack_id, size):
                raise BuildError(f"{pack_id}.mwm is {size} bytes; countries.json says {sizes[pack_id]}")
            target = staged / f"{pack_id}.mwm"
            _link_or_copy(source, target)
            packs.append({"id": pack_id, "title": pack_title(pack_id), "file": f"{pack_id}.mwm",
                          "url": f"/maps/packs/{quote(pack_id)}.mwm", "size_bytes": size,
                          "expected_size_bytes": sizes.get(pack_id, 0)})
        apk: dict | None = None
        if not ctx.fixture:
            apk_url = ctx.version("ORGANICMAPS_APK_URL")
            sha = ctx.version("ORGANICMAPS_APK_SHA256")
            name = apk_url.rsplit("/", 1)[-1]
            source = ctx.download(apk_url, name, sha256=sha)
            _link_or_copy(source, staged / name)
            apk = {"file": name, "url": f"/maps/packs/{name}", "size_bytes": (staged / name).stat().st_size,
                   "sha256": sha, "tag": ctx.version("ORGANICMAPS_TAG")}
        (staged / "index.html").write_text(render_index_html(version, packs, apk))
        (staged / "index.json").write_text(json.dumps(index_json(version, packs, apk), indent=2) + "\n")
        ctx.commit("packs")
        log.info("[packs] data version %s, %d packs%s", version, len(packs), ", APK" if apk else "")
        ctx.write_sidecar("packs", {"step": self.id, "data_version": version, "ids": wanted,
                                    "apk": apk["file"] if apk else None})
```

`api/sos/buildmaps.py` — `all_steps` becomes:

```python
def all_steps() -> list:
    """Registry in pipeline order. Later tasks append their step here."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.hillshade import HillshadeStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.overlays import OverlaysStep
    from sos.mapbuild.packs import PacksStep
    from sos.mapbuild.places import PlacesStep
    from sos.mapbuild.styles import StylesStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), HillshadeStep(), OverlaysStep(), PlacesStep(), PacksStep(), StylesStep()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_packs.py -q 2>&1 | tail -3`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/packs.py api/sos/buildmaps.py api/tests/test_buildmaps_packs.py
git commit -m "feat(maps): packs step fetches Organic Maps packs and the APK and writes the packs index"
```

---

### Task 10: Step `verify`, `manifest/maps.json`, `--fixture` outputs committed, fixture manifest

**Files:**
- Create: `api/sos/mapbuild/verify.py`
- Create: `manifest/maps.json`
- Create: `api/tests/test_buildmaps_verify.py`
- Create: `api/tests/test_buildmaps_fixture_outputs.py`
- Create (generated by `sos build-maps --fixture`, committed): `api/tests/fixtures/maps/**` and `api/tests/fixtures/manifest/maps.json`
- Modify: `api/sos/buildmaps.py` (`all_steps`)
- Modify: `Makefile` (`fixtures` target runs `sos build-maps --fixture`)

**Interfaces:**
- Consumes: `check_base`, `PROBES_FULL`, `PROBES_FIXTURE` (Task 2); `pmtiles_verify`, `pmtiles_header`, `tile_exists`, `dir_size`, `FIXTURE_MAX_BYTES` (Task 1); every earlier step's outputs.
- Produces: `VerifyStep` (`id == "verify"`, no outputs, always runs when selected), `archives(out) -> list[Path]`, `check_style_sources(out) -> list[str]`, `output_sizes(ctx) -> dict[str, int]`, `update_manifest_sizes(path, sizes) -> list[str]`, `write_fixture_manifest(source, dest, base_name)`, `MANIFEST_OUTPUTS`. Writes `<out>/build.json`.
- Manifest contract (plan 01 reads it; plan 02 reads `styles/index.json` and `overlays/index.json` through the API): the twelve items `uk-ie, os-zoomstack, contours, hillshade, footpaths, flood-zones, styles, sprites, glyphs, places, packs, apk`, all `tier: core`, `category: maps`, `source.type: build` with `tool: "sos build-maps"`; `footpaths` and `flood-zones` carry their `overlay` object here (plan 03's `overlays.json` must not repeat those two ids). The fixture manifest is the same list with `uk-ie.dest = maps/test.pmtiles` and no `apk` item.

- [ ] **Step 1: Write the failing tests and the manifest**

`manifest/maps.json`:

```json
{
  "items": [
    {"id": "uk-ie", "title": "UK and Ireland base map (OpenStreetMap)", "kind": "pmtiles", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "uk-ie.pmtiles"}, "dest": "maps/uk-ie.pmtiles",
     "size_bytes": 3400000000, "as_at": "2026-09-02", "licence": "ODbL 1.0 (OpenStreetMap contributors); Protomaps BSD-3", "priority": 50,
     "description": "Protomaps vector tiles to zoom 15 for the UK, Ireland, the Isle of Man and the Channel Islands."},
    {"id": "os-zoomstack", "title": "OS Open Zoomstack base map (Great Britain)", "kind": "pmtiles", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "os-zoomstack.pmtiles"}, "dest": "maps/os-zoomstack.pmtiles",
     "size_bytes": 2852712448, "as_at": "2026-06", "licence": "OGL v3 (Contains OS data © Crown copyright and database right 2026)", "priority": 51,
     "description": "Ordnance Survey vector base map of Great Britain, Outdoor and Night styles."},
    {"id": "contours", "title": "Contours", "kind": "pmtiles", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "contours.pmtiles"}, "dest": "maps/contours.pmtiles",
     "size_bytes": 1100000000, "as_at": "2026-07", "licence": "OGL v3 (OS Terrain 50); Copernicus DEM licence (ESA)", "priority": 52,
     "description": "10 m contours: OS Terrain 50 for Great Britain, Copernicus and OSNI derived elsewhere."},
    {"id": "hillshade", "title": "Hillshade", "kind": "pmtiles", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "hillshade.pmtiles"}, "dest": "maps/hillshade.pmtiles",
     "size_bytes": 1500000000, "as_at": "2026-07", "licence": "OGL v3 (OS Terrain 50, OSNI); Copernicus DEM licence (ESA)", "priority": 53,
     "description": "Relief shading at 30 m for the whole map."},
    {"id": "footpaths", "title": "Footpaths and rights of way", "kind": "pmtiles", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "overlays/footpaths.pmtiles"}, "dest": "maps/overlays/footpaths.pmtiles",
     "size_bytes": 800000000, "as_at": "2026-09", "licence": "ODbL 1.0 (OpenStreetMap contributors)", "priority": 54,
     "description": "Paths, tracks and bridleways with public right-of-way designations from OpenStreetMap.",
     "overlay": {"id": "footpaths", "kind": "pmtiles", "layer_id": null, "default_on": false,
                 "coverage": ["england", "wales", "scotland", "ni", "roi", "iom", "ci"], "color": "#e6007e", "icon": "footprints"}},
    {"id": "flood-zones", "title": "Flood zones", "kind": "pmtiles", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "overlays/flood-zones.pmtiles"}, "dest": "maps/overlays/flood-zones.pmtiles",
     "size_bytes": 300000000, "as_at": "2026-09", "licence": "OGL v3 (Environment Agency, Natural Resources Wales, SEPA, DfI Rivers)", "priority": 55,
     "description": "River and sea flood zones from the four national agencies.",
     "overlay": {"id": "flood-zones", "kind": "pmtiles", "layer_id": null, "default_on": false,
                 "coverage": ["england", "wales", "scotland", "ni"], "color": "#1e90ff", "icon": "waves"}},
    {"id": "styles", "title": "Map styles", "kind": "style", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "styles"}, "dest": "maps/styles",
     "size_bytes": 2000000, "as_at": "2026-09", "licence": "BSD-3 (Protomaps basemaps); OGL v3 (OS Open Zoomstack stylesheets)", "priority": 56,
     "description": "MapLibre styles for both base maps in the Vault, Field and Blackout themes, plus terrain and overlay layer fragments."},
    {"id": "sprites", "title": "Map sprites", "kind": "sprites", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "sprites"}, "dest": "maps/sprites",
     "size_bytes": 1000000, "as_at": "2026-09", "licence": "BSD-3 (Protomaps basemaps-assets); OGL v3 (Ordnance Survey)", "priority": 57,
     "description": "Icon sprite sheets for the Protomaps and OS styles."},
    {"id": "glyphs", "title": "Map fonts", "kind": "glyphs", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "fonts"}, "dest": "maps/fonts",
     "size_bytes": 40000000, "as_at": "2026-09", "licence": "OFL 1.1 (Noto Sans, Source Sans Pro, Open Sans)", "priority": 58,
     "description": "Signed-distance-field glyphs for map labels."},
    {"id": "places", "title": "Place names", "kind": "places", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "places.csv.gz"}, "dest": "maps/places.csv.gz",
     "size_bytes": 60000000, "as_at": "2026-09", "licence": "OGL v3 (OS Open Names); ODbL 1.0 (OpenStreetMap contributors)", "priority": 59,
     "description": "Settlements, postcodes and road names for place search."},
    {"id": "packs", "title": "Phone map packs (Organic Maps)", "kind": "mwm", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "packs"}, "dest": "maps/packs",
     "size_bytes": 2614260432, "as_at": "2026-08-26", "licence": "ODbL 1.0 (OpenStreetMap contributors); Apache-2.0 (Organic Maps)", "priority": 60,
     "description": "Offline map files for Android phones, copied over USB from a PC."},
    {"id": "apk", "title": "Organic Maps Android app", "kind": "apk", "tier": "core", "category": "maps", "scenarios": [],
     "source": {"type": "build", "tool": "sos build-maps", "artifact": "packs/OrganicMaps-26082718-web-release.apk"}, "dest": "maps/packs/OrganicMaps-26082718-web-release.apk",
     "size_bytes": 64193127, "as_at": "2026-08-27", "licence": "Apache-2.0", "priority": 61,
     "description": "The Android app that reads the phone map packs (release 2026.08.27-18)."}
  ]
}
```

`api/tests/test_buildmaps_verify.py`:

```python
import json
import shutil
from pathlib import Path

import pytest

from sos.mapbuild import verify
from sos.mapbuild.common import BuildError, FIXTURE_MAX_BYTES
from tests.mapbuild_helpers import FakeRunner, make_ctx, REPO

FIXTURE_HEADER = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 15, "bounds": [-1.56, 50.87, -1.46, 50.97]}
MANIFEST_IDS = ["uk-ie", "os-zoomstack", "contours", "hillshade", "footpaths", "flood-zones", "styles", "sprites", "glyphs", "places", "packs", "apk"]
ALLOWED_KINDS = {"zim", "pmtiles", "geojson", "pdf", "epub", "dir", "model", "mwm", "apk", "style", "glyphs", "sprites", "places"}


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data))


def _synthetic_out(out: Path, base="test.pmtiles") -> None:
    """A minimal but complete output tree that check_style_sources and output_sizes accept."""
    for name in (base, "os-zoomstack.pmtiles", "contours.pmtiles", "hillshade.pmtiles", "overlays/footpaths.pmtiles", "overlays/flood-zones.pmtiles"):
        _write(out / name, b"pm")
    _write(out / "overlays" / "index.json", {"footpaths": {"kind": "pmtiles", "file": "overlays/footpaths.pmtiles"},
                                              "water": {"kind": "pmtiles", "file": "overlays/water.pmtiles"}})
    _write(out / "overlays" / "water.pmtiles", b"pm")
    _write(out / "overlays" / "nuclear-sites.geojson", {"type": "FeatureCollection", "features": []})
    for face in ("Noto Sans Regular", "Source Sans Pro Regular"):
        _write(out / "fonts" / face / "0-255.pbf", b"g")
    for name in ("v4/light.json", "v4/light.png", "v4/dark.json", "v4/dark.png", "os/sprites.json", "os/sprites.png"):
        _write(out / "sprites" / name, b"s")
    style = lambda src, sprite, face: {"version": 8, "sources": {"s": {"type": "vector", "url": f"pmtiles:///maps/{src}"}}, "sprite": sprite,
                                      "glyphs": "/maps/fonts/{fontstack}/{range}.pbf",
                                      "layers": [{"id": "l", "type": "symbol", "source": "s", "source-layer": "x", "layout": {"text-font": [face]}}]}
    _write(out / "styles" / "osm-light.json", style(base, "/maps/sprites/v4/light", "Noto Sans Regular"))
    _write(out / "styles" / "osm-dark.json", style(base, "/maps/sprites/v4/dark", "Noto Sans Regular"))
    _write(out / "styles" / "osm-vault.json", style(base, "/maps/sprites/v4/dark", "Noto Sans Regular"))
    _write(out / "styles" / "os-outdoor.json", style("os-zoomstack.pmtiles", "/maps/sprites/os/sprites", "Source Sans Pro Regular"))
    _write(out / "styles" / "os-night.json", style("os-zoomstack.pmtiles", "/maps/sprites/os/sprites", "Source Sans Pro Regular"))
    _write(out / "styles" / "layers" / "contours.json", {"sources": {"contours": {"type": "vector", "url": "pmtiles:///maps/contours.pmtiles"}}, "layers": []})
    _write(out / "styles" / "layers" / "overlays.json", {"sources": {"water": {"type": "vector", "url": "pmtiles:///maps/overlays/water.pmtiles"}}, "layers": []})
    _write(out / "styles" / "index.json", {
        "osm": {"vault": "/maps/styles/osm-vault.json", "field": "/maps/styles/osm-light.json", "blackout": "/maps/styles/osm-dark.json", "tiles": f"/maps/{base}"},
        "os": {"vault": "/maps/styles/os-night.json", "field": "/maps/styles/os-outdoor.json", "blackout": "/maps/styles/os-night.json", "tiles": "/maps/os-zoomstack.pmtiles"},
        "layers": {"contours": "/maps/styles/layers/contours.json", "overlays": "/maps/styles/layers/overlays.json"}})
    _write(out / "places.csv.gz", b"\x1f\x8b")
    _write(out / "packs" / "index.html", b"<html></html>")
    _write(out / "packs" / "index.json", {"version": "260826", "apk": None, "packs": [], "index_url": "/maps/packs/index.html"})


def test_manifest_maps_json_has_the_twelve_items_with_valid_shapes():
    doc = json.loads((REPO / "manifest" / "maps.json").read_text())
    items = doc["items"]
    assert [i["id"] for i in items] == MANIFEST_IDS
    for item in items:
        assert item["kind"] in ALLOWED_KINDS and item["tier"] == "core" and item["category"] == "maps"
        assert item["source"]["type"] == "build" and item["source"]["tool"] == "sos build-maps" and item["source"]["artifact"]
        assert item["dest"].startswith("maps/") and item["size_bytes"] > 0 and item["as_at"] and item["licence"]
        assert isinstance(item["priority"], int) and item["description"]
    overlays = {i["id"]: i["overlay"] for i in items if i.get("overlay")}
    assert set(overlays) == {"footpaths", "flood-zones"}
    assert overlays["flood-zones"]["coverage"] == ["england", "wales", "scotland", "ni"] and overlays["footpaths"]["kind"] == "pmtiles"
    assert "NOMAD" not in json.dumps(doc)


def test_check_style_sources_accepts_a_complete_tree_and_reports_gaps(tmp_path):
    out = tmp_path / "out"
    _synthetic_out(out)
    assert verify.check_style_sources(out) == []
    (out / "contours.pmtiles").unlink()
    (out / "sprites" / "v4" / "dark.png").unlink()
    shutil.rmtree(out / "fonts" / "Source Sans Pro Regular")
    problems = verify.check_style_sources(out)
    assert any("contours.pmtiles" in p for p in problems)
    assert any("dark.png" in p or "sprites/v4/dark" in p for p in problems)
    assert any("Source Sans Pro Regular" in p for p in problems)
    (out / "styles" / "osm-light.json").write_text(json.dumps({"version": 8, "sources": {"s": {"type": "vector", "url": "https://example.test/tiles.json"}}, "layers": []}))
    assert any("not pmtiles:///maps/" in p for p in verify.check_style_sources(out))
    shutil.rmtree(out / "styles")
    assert verify.check_style_sources(out) == ["no styles under styles/"]


def test_output_sizes_and_manifest_update(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    _synthetic_out(ctx.out)
    (ctx.out / "packs" / "index.json").write_text(json.dumps({"version": "260826", "apk": {"file": "a.apk", "url": "/maps/packs/a.apk", "size_bytes": 64193127, "sha256": "x", "tag": "t"}, "packs": [], "index_url": "/maps/packs/index.html"}))
    sizes = verify.output_sizes(ctx)
    assert set(sizes) == set(MANIFEST_IDS)
    assert sizes["uk-ie"] == 2 and sizes["apk"] == 64193127 and sizes["glyphs"] == 2 and sizes["sprites"] == 6
    manifest = tmp_path / "maps.json"
    shutil.copyfile(REPO / "manifest" / "maps.json", manifest)
    updated = verify.update_manifest_sizes(manifest, {"uk-ie": 3200000000, "unknown": 1})
    assert updated == ["uk-ie"]
    doc = json.loads(manifest.read_text())
    assert next(i for i in doc["items"] if i["id"] == "uk-ie")["size_bytes"] == 3200000000
    assert next(i for i in doc["items"] if i["id"] == "apk")["size_bytes"] == 64193127, "untouched items keep their values"


def test_write_fixture_manifest_rewrites_base_and_drops_apk(tmp_path):
    dest = tmp_path / "fixtures" / "manifest" / "maps.json"
    verify.write_fixture_manifest(REPO / "manifest" / "maps.json", dest, "test.pmtiles")
    doc = json.loads(dest.read_text())
    ids = [i["id"] for i in doc["items"]]
    assert ids == [i for i in MANIFEST_IDS if i != "apk"]
    base = doc["items"][0]
    assert base["dest"] == "maps/test.pmtiles" and base["source"]["artifact"] == "test.pmtiles"
    assert next(i for i in doc["items"] if i["id"] == "places")["dest"] == "maps/places.csv.gz"


def _repo_copy(tmp_path):
    repo = tmp_path / "repo"
    (repo / "manifest").mkdir(parents=True)
    shutil.copyfile(REPO / "manifest" / "maps.json", repo / "manifest" / "maps.json")
    (repo / "install").mkdir()
    (repo / "install" / "versions.env").write_text("PROTOMAPS_BUILD=20260902\n")
    return repo


def test_verify_step_fixture_verifies_every_archive_and_writes_sizes(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out)
    verify.VerifyStep().run(ctx)
    verified = sorted(c[2] for c in runner.find("pmtiles", "verify"))
    assert verified == sorted(str(p) for p in [ctx.out / "test.pmtiles", ctx.out / "os-zoomstack.pmtiles", ctx.out / "contours.pmtiles", ctx.out / "hillshade.pmtiles",
                                                ctx.out / "overlays" / "footpaths.pmtiles", ctx.out / "overlays" / "flood-zones.pmtiles", ctx.out / "overlays" / "water.pmtiles"])
    assert runner.find("pmtiles", "tile")[0][-3:] == ["12", "2031", "1372"]
    fixture_manifest = ctx.repo / "api" / "tests" / "fixtures" / "manifest" / "maps.json"
    doc = json.loads(fixture_manifest.read_text())
    assert next(i for i in doc["items"] if i["id"] == "uk-ie")["size_bytes"] == 2
    assert "apk" not in [i["id"] for i in doc["items"]]
    original = json.loads((ctx.repo / "manifest" / "maps.json").read_text())
    assert next(i for i in original["items"] if i["id"] == "uk-ie")["size_bytes"] == 3400000000, "fixture runs never touch manifest/maps.json"
    report = json.loads((ctx.out / "build.json").read_text())
    assert report["fixture"] is True and report["sizes"]["contours"] == 2 and len(report["verified_archives"]) == 7


def test_verify_step_full_mode_updates_the_real_manifest_copy(tmp_path):
    header = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 15, "bounds": [-11, 49.1, 2.2, 61.2]}
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(header), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out, base="uk-ie.pmtiles")
    verify.VerifyStep().run(ctx)
    probed = {tuple(c[-3:]) for c in runner.find("pmtiles", "tile")}
    assert probed == {("12", "2023", "1403"), ("12", "2034", "1186")}
    doc = json.loads((ctx.repo / "manifest" / "maps.json").read_text())
    assert next(i for i in doc["items"] if i["id"] == "uk-ie")["size_bytes"] == 2


def test_verify_step_fails_on_oversized_fixture_missing_output_or_bad_style(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    ctx.repo = _repo_copy(tmp_path)
    _synthetic_out(ctx.out)
    (ctx.out / "test.pmtiles").write_bytes(b"x" * FIXTURE_MAX_BYTES)
    with pytest.raises(BuildError, match="under"):
        verify.VerifyStep().run(ctx)
    (ctx.out / "test.pmtiles").write_bytes(b"pm")
    (ctx.out / "places.csv.gz").unlink()
    with pytest.raises(BuildError, match="places.csv.gz"):
        verify.VerifyStep().run(ctx)
    assert not (ctx.out / "build.json").exists()
```

`api/tests/test_buildmaps_fixture_outputs.py` (runs in CI against the committed fixture; skipped until the fixture has been built once):

```python
import csv
import gzip
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sos.mapbuild.common import FIXTURE_BBOX, FIXTURE_MAX_BYTES, validate_geojson
from sos.mapbuild.verify import archives, check_style_sources
from tests.mapbuild_helpers import REPO

FIXTURE = REPO / "api" / "tests" / "fixtures" / "maps"
pytestmark = pytest.mark.skipif(not (FIXTURE / "test.pmtiles").exists(), reason="run `sos build-maps --fixture` first")


def test_fixture_base_is_under_5_mib():
    assert (FIXTURE / "test.pmtiles").stat().st_size < FIXTURE_MAX_BYTES


def test_fixture_styles_resolve_to_fixture_files():
    assert check_style_sources(FIXTURE) == []
    index = json.loads((FIXTURE / "styles" / "index.json").read_text())
    assert index["osm"]["tiles"] == "/maps/test.pmtiles"


def test_fixture_overlays_index_matches_files():
    index = json.loads((FIXTURE / "overlays" / "index.json").read_text())
    for overlay_id in ("footpaths", "flood-zones", "nuclear-sites", "health", "fuel", "water", "rail", "chemical-sites", "airports-military", "access-land"):
        assert overlay_id in index
        assert (FIXTURE / index[overlay_id]["file"]).exists(), overlay_id
    nuclear = json.loads((FIXTURE / "overlays" / "nuclear-sites.geojson").read_text())
    assert validate_geojson(nuclear) == [] and len(nuclear["features"]) >= 20
    assert index["flood-zones"]["layers"] == ["flood_england"]


def test_fixture_places_are_inside_the_bbox():
    with gzip.open(FIXTURE / "places.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and list(rows[0]) == ["name", "kind", "lat", "lon", "region", "postcode"]
    assert len(rows) >= 100
    for row in rows:
        assert FIXTURE_BBOX[0] <= float(row["lon"]) <= FIXTURE_BBOX[2] and FIXTURE_BBOX[1] <= float(row["lat"]) <= FIXTURE_BBOX[3], row
    assert any(row["name"] == "Totton" and row["kind"] == "town" for row in rows)


def test_fixture_packs_index_and_manifest():
    packs = json.loads((FIXTURE / "packs" / "index.json").read_text())
    assert packs["apk"] is None and [p["id"] for p in packs["packs"]] == ["Jersey"] and packs["index_url"] == "/maps/packs/index.html"
    manifest = json.loads((REPO / "api" / "tests" / "fixtures" / "manifest" / "maps.json").read_text())
    base = next(i for i in manifest["items"] if i["id"] == "uk-ie")
    assert base["dest"] == "maps/test.pmtiles" and base["size_bytes"] == (FIXTURE / "test.pmtiles").stat().st_size


@pytest.mark.skipif(shutil.which("pmtiles") is None, reason="pmtiles binary not on PATH")
def test_fixture_archives_pass_pmtiles_verify_and_cover_the_bbox():
    found = archives(FIXTURE)
    assert len(found) >= 6
    for archive in found:
        subprocess.run(["pmtiles", "verify", str(archive)], check=True, capture_output=True)
    header = json.loads(subprocess.run(["pmtiles", "show", "--header-json", str(FIXTURE / "test.pmtiles")], check=True, capture_output=True, text=True).stdout)
    assert header["maxzoom"] == 15 and header["bounds"] == list(FIXTURE_BBOX)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_verify.py tests/test_buildmaps_fixture_outputs.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sos.mapbuild.verify'` (both modules import it).

- [ ] **Step 3: Implement `verify.py`, register the step, add the Makefile target**

`api/sos/mapbuild/verify.py`:

```python
"""Step `verify`: pmtiles verify on every archive, base map checks, style sources, sizes into the manifest."""
from __future__ import annotations

import json
from pathlib import Path

from .base import PROBES_FIXTURE, PROBES_FULL, check_base
from .common import BuildError, Context, FIXTURE_MAX_BYTES, dir_size, log, pmtiles_header, pmtiles_verify, tile_exists

MANIFEST_OUTPUTS = {  # manifest item id -> path under <out>; the base map is added per context
    "os-zoomstack": "os-zoomstack.pmtiles",
    "contours": "contours.pmtiles",
    "hillshade": "hillshade.pmtiles",
    "footpaths": "overlays/footpaths.pmtiles",
    "flood-zones": "overlays/flood-zones.pmtiles",
    "styles": "styles",
    "sprites": "sprites",
    "glyphs": "fonts",
    "places": "places.csv.gz",
    "packs": "packs",
}
LOCAL_TILES = "pmtiles:///maps/"
LOCAL_URL = "/maps/"
GLYPHS_URL = "/maps/fonts/{fontstack}/{range}.pbf"


def archives(out: Path) -> list[Path]:
    return sorted(out.glob("*.pmtiles")) + sorted((out / "overlays").glob("*.pmtiles"))


def _exists(out: Path, url: str, prefix: str) -> bool:
    return url.startswith(prefix) and (out / url[len(prefix):]).exists()


def check_style_sources(out: Path) -> list[str]:
    problems: list[str] = []
    styles_dir = out / "styles"
    files = sorted(p for p in styles_dir.glob("*.json") if p.name != "index.json") if styles_dir.is_dir() else []
    if not files:
        return ["no styles under styles/"]
    docs = [(p, json.loads(p.read_text())) for p in files]
    layers_dir = styles_dir / "layers"
    if layers_dir.is_dir():
        docs += [(p, json.loads(p.read_text())) for p in sorted(layers_dir.glob("*.json"))]
    for path, doc in docs:
        for source_id, source in doc.get("sources", {}).items():
            url = source.get("url", "")
            if not url.startswith(LOCAL_TILES):
                problems.append(f"{path.name}: source {source_id} url {url!r} is not pmtiles:///maps/...")
            elif not _exists(out, url, LOCAL_TILES):
                problems.append(f"{path.name}: source {source_id} -> {url} is missing")
        if "sprite" in doc:
            sprite = doc["sprite"]
            if not sprite.startswith(LOCAL_URL):
                problems.append(f"{path.name}: sprite {sprite!r} is not under /maps/")
            else:
                for ext in (".json", ".png"):
                    if not (out / (sprite[len(LOCAL_URL):] + ext)).exists():
                        problems.append(f"{path.name}: sprite file {sprite}{ext} is missing")
        if "glyphs" in doc and doc["glyphs"] != GLYPHS_URL:
            problems.append(f"{path.name}: glyphs {doc['glyphs']!r} is not {GLYPHS_URL}")
        for layer in doc.get("layers", []):
            fonts = layer.get("layout", {}).get("text-font")
            if isinstance(fonts, list):
                for face in fonts:
                    if isinstance(face, str) and not (out / "fonts" / face / "0-255.pbf").exists():
                        problems.append(f"{path.name}: glyphs for {face!r} are missing (layer {layer.get('id')})")
    index_path = styles_dir / "index.json"
    if not index_path.exists():
        problems.append("styles/index.json is missing")
    else:
        index = json.loads(index_path.read_text())
        for base in ("osm", "os"):
            for key in ("vault", "field", "blackout", "tiles"):
                url = index.get(base, {}).get(key, "")
                if not _exists(out, url, LOCAL_URL):
                    problems.append(f"styles/index.json {base}.{key} -> {url!r} is missing")
        for name, url in index.get("layers", {}).items():
            if not _exists(out, url, LOCAL_URL):
                problems.append(f"styles/index.json layers.{name} -> {url!r} is missing")
    return sorted(set(problems))


def output_sizes(ctx: Context) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for item_id, rel in {"uk-ie": ctx.base_name, **MANIFEST_OUTPUTS}.items():
        path = ctx.out / rel
        if path.is_file():
            sizes[item_id] = path.stat().st_size
        elif path.is_dir():
            sizes[item_id] = dir_size(path)
    packs_index = ctx.out / "packs" / "index.json"
    if packs_index.exists():
        apk = json.loads(packs_index.read_text()).get("apk")
        if apk:
            sizes["apk"] = int(apk["size_bytes"])
    return sizes


def update_manifest_sizes(path: Path, sizes: dict[str, int]) -> list[str]:
    doc = json.loads(path.read_text())
    updated = []
    for item in doc.get("items", []):
        if item.get("id") in sizes:
            item["size_bytes"] = sizes[item["id"]]
            updated.append(item["id"])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return updated


def write_fixture_manifest(source: Path, dest: Path, base_name: str) -> None:
    doc = json.loads(source.read_text())
    items = []
    for item in doc["items"]:
        if item["id"] == "apk":
            continue
        if item["id"] == "uk-ie":
            item["dest"] = f"maps/{base_name}"
            item["source"]["artifact"] = base_name
        items.append(item)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"items": items}, indent=2, ensure_ascii=False) + "\n")


class VerifyStep:
    id = "verify"

    def outputs(self, ctx: Context) -> list[str]:
        return []

    def run(self, ctx: Context) -> None:
        problems: list[str] = []
        found = archives(ctx.out)
        if not found:
            problems.append("no PMTiles archives under the output directory")
        for archive in found:
            pmtiles_verify(ctx, archive)
        base = ctx.output(ctx.base_name)
        if base.exists():
            header = pmtiles_header(ctx, base)
            probes = PROBES_FIXTURE if ctx.fixture else PROBES_FULL
            problems += check_base(header, ctx.bbox, probes, lambda z, x, y: tile_exists(ctx, base, z, x, y))
            size = base.stat().st_size
            if ctx.fixture and size >= FIXTURE_MAX_BYTES:
                problems.append(f"{ctx.base_name} is {size} bytes; the fixture must stay under {FIXTURE_MAX_BYTES} bytes")
        else:
            problems.append(f"{ctx.base_name} is missing")
        problems += check_style_sources(ctx.out)
        for rel in MANIFEST_OUTPUTS.values():
            if not (ctx.out / rel).exists():
                problems.append(f"missing output {rel}")
        if problems:
            raise BuildError("verification failed:\n  " + "\n  ".join(problems))

        sizes = output_sizes(ctx)
        manifest = ctx.repo / "manifest" / "maps.json"
        if ctx.fixture:
            target = ctx.repo / "api" / "tests" / "fixtures" / "manifest" / "maps.json"
            write_fixture_manifest(manifest, target, ctx.base_name)
        else:
            target = manifest
        updated = update_manifest_sizes(target, sizes)
        report = {"fixture": ctx.fixture, "build": ctx.build, "bbox": list(ctx.bbox),
                  "verified_archives": [str(a.relative_to(ctx.out)) for a in found],
                  "sizes": sizes, "manifest": str(target.relative_to(ctx.repo)), "updated": updated}
        (ctx.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        log.info("[verify] OK: %d archives verified; sizes written to %s", len(found), target.relative_to(ctx.repo))
```

`api/sos/buildmaps.py` — final `all_steps`:

```python
def all_steps() -> list:
    """Registry in pipeline order: base, os, contours, hillshade, overlays, places, packs, styles, verify."""
    from sos.mapbuild.base import BaseStep
    from sos.mapbuild.contours import ContoursStep
    from sos.mapbuild.hillshade import HillshadeStep
    from sos.mapbuild.osdata import OsZoomstackStep
    from sos.mapbuild.overlays import OverlaysStep
    from sos.mapbuild.packs import PacksStep
    from sos.mapbuild.places import PlacesStep
    from sos.mapbuild.styles import StylesStep
    from sos.mapbuild.verify import VerifyStep
    return [BaseStep(), OsZoomstackStep(), ContoursStep(), HillshadeStep(), OverlaysStep(), PlacesStep(), PacksStep(),
            StylesStep(), VerifyStep()]
```

`Makefile`: in the `fixtures` target add the line `cd api && sos build-maps --fixture` (after plan 01's fixture commands).

- [ ] **Step 4: Run the unit tests**

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_verify.py -q 2>&1 | tail -3`
Expected: `7 passed`.

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_fixture_outputs.py -q 2>&1 | tail -3`
Expected: `6 skipped` (the fixture has not been built yet).

- [ ] **Step 5: Build the fixture (network; the first run fills the source cache)**

Run:

```bash
export PATH=$HOME/.local/bin:$PATH
export MAMBA_ROOT_PREFIX=$HOME/micromamba; eval "$(micromamba shell hook -s bash)"; micromamba activate sos-maps
time sos build-maps --fixture --force 2>&1 | tee /tmp/build-maps-fixture.log | grep -E '^\S+ INFO \[|build-maps:'
```

Expected: one `[<step>] start` / `[<step>] done in Ns` pair for `base os contours hillshade overlays places packs styles`, then `[verify] OK: 6 archives verified; sizes written to api/tests/fixtures/manifest/maps.json` (7 or 8 if `water` or `airports-military` exceeded 5 MB in the fixture bbox), exit 0. The first run downloads about 4.5 GB into `~/sos-content/maps-src` (OS Open Zoomstack 2.85 GB, OS Terrain 50 tiles 1.07 GB and grids 162 MB, OS Open Names 103 MB, Hampshire PBF, one Copernicus tile, the two asset repositories, Jersey.mwm) and takes as long as the downloads take; rerun `time sos build-maps --fixture --force` with the warm cache and expect `real` under `5m0s`.

Run: `ls -la api/tests/fixtures/maps api/tests/fixtures/maps/overlays api/tests/fixtures/maps/styles && du -sh api/tests/fixtures/maps`
Expected: `test.pmtiles` under 5,242,880 bytes; `os-zoomstack.pmtiles`, `contours.pmtiles`, `hillshade.pmtiles`, sidecar `.json` files, `overlays/` with `index.json`, `footpaths.pmtiles`, `flood-zones.pmtiles`, `nuclear-sites.geojson`, `health.geojson`, `fuel.geojson`, `rail.geojson`, `chemical-sites.geojson`, `water.geojson` or `.pmtiles`, `airports-military.geojson` or `.pmtiles`, `access-land.geojson`; `styles/` with the five styles, `index.json` and `layers/`; `sprites/`, `fonts/`, `places.csv.gz`, `packs/index.html`, `packs/index.json`, `packs/Jersey.mwm`, `build.json`; total under 25 MB.

Run: `cd /home/dan/OperationSOS/api && python -m pytest tests/test_buildmaps_fixture_outputs.py -v 2>&1 | tail -8`
Expected: `6 passed`.

- [ ] **Step 6: Commit the code, the manifest and the fixture outputs**

```bash
cd /home/dan/OperationSOS
git add api/sos/mapbuild/verify.py api/sos/buildmaps.py manifest/maps.json Makefile \
        api/tests/test_buildmaps_verify.py api/tests/test_buildmaps_fixture_outputs.py \
        api/tests/fixtures/maps api/tests/fixtures/manifest/maps.json
git status --short | grep -E 'mwm|\.incoming' && echo "STOP: ignored files staged" || true
git commit -m "feat(maps): verify step, manifest/maps.json and the committed --fixture outputs"
```

(`*.mwm` and `.incoming/` are ignored, so `packs/Jersey.mwm` stays out of git; the fixture `packs/index.json` still lists it, which is what `GET /api/map/config` reports.)

---

### Task 11: Acceptance

**Files:** none new. Runs the whole plan's exit criteria (spec section 13 `sos build-maps`, section 14 Build pipelines row, section 15 milestone 3 CI part).

- [ ] **Step 1: Unit suites, style tests and content checks**

Run:

```bash
cd /home/dan/OperationSOS && make test 2>&1 | tail -15
```

Expected: pytest reports every `test_buildmaps_*` module passing (`test_buildmaps_cli.py` 18, `base` 6, `styles` 10, `os` 7, `contours` 13, `hillshade` 2, `overlays` 12, `places` 11, `packs` 7, `verify` 7, `fixture_outputs` 6 — 99 tests in this plan), `node --test` in `tools/map-styles` reports `# pass 3`, and the rest of `make test` (vitest, validate-playbooks, manifest schema check) still passes.

- [ ] **Step 2: Fixture build under five minutes with every verification passing**

Run:

```bash
export PATH=$HOME/.local/bin:$PATH
export MAMBA_ROOT_PREFIX=$HOME/micromamba; eval "$(micromamba shell hook -s bash)"; micromamba activate sos-maps
cd /home/dan/OperationSOS && time sos build-maps --fixture --force 2>&1 | grep -E '\[(base|os|contours|hillshade|overlays|places|packs|styles|verify)\] (done|OK)'
echo "exit=${PIPESTATUS[0]}"
python3 - <<'EOF'
import json, os
r = json.load(open("api/tests/fixtures/maps/build.json"))
print("archives:", len(r["verified_archives"]), "base bytes:", os.path.getsize("api/tests/fixtures/maps/test.pmtiles"))
print("updated manifest ids:", r["updated"])
EOF
git status --short api/tests/fixtures manifest
```

Expected: eight `[step] done in Ns` lines, `[verify] OK: 6 archives verified; sizes written to api/tests/fixtures/manifest/maps.json`, `exit=0`, `real` below `5m0.000s` (warm cache), `archives: 6` (or 7 or 8, see Task 10) with `base bytes` below 5242880, `updated manifest ids: ['uk-ie', 'os-zoomstack', 'contours', 'hillshade', 'footpaths', 'flood-zones', 'styles', 'sprites', 'glyphs', 'places', 'packs']`, and `git status` showing only sidecar `built_at` timestamps changed (rebuilding the same inputs reproduces the same archives; commit the refreshed sidecars if you want the timestamps in git, otherwise `git checkout api/tests/fixtures`).

- [ ] **Step 3: Tool-check message without the toolchain**

Run: `cd /home/dan/OperationSOS && env -i HOME=$HOME PATH=/usr/bin:/bin $(cd api && .venv/bin/python -c 'import sys; print(sys.executable)' 2>/dev/null || which python3) -m sos.buildmaps --fixture --steps base; echo "exit=$?"`
Expected: `build-maps: missing tools: pmtiles, tippecanoe, tile-join, osmium, ogr2ogr, ...` followed by the two-line micromamba hint, `exit=2`.

- [ ] **Step 4: `GET /api/map/config` lists the fixture layers**

Run (plan 01's API with `SOS_CORE` pointed at the fixture tree so `/maps/*` resolves to `api/tests/fixtures/maps`):

```bash
cd /home/dan/OperationSOS
mkdir -p /tmp/sos-accept/state /tmp/sos-accept/ext
export SOS_DEV=1 SOS_CORE=$PWD/api/tests/fixtures SOS_EXT=/tmp/sos-accept/ext SOS_STATE=/tmp/sos-accept/state \
       SOS_MANIFEST_DIR=$PWD/api/tests/fixtures/manifest SOS_PLAYBOOKS_DIR=$PWD/playbooks SOS_WEB=$PWD/web/dist SOS_PORT=8000
cd api && sos index && (uvicorn sos.main:app --port 8000 >/tmp/sos-accept/api.log 2>&1 & echo $! > /tmp/sos-accept/api.pid); sleep 2
curl -s http://127.0.0.1:8000/api/map/config | python3 -c "
import json, sys
c = json.load(sys.stdin)
print('bases:', [(b['id'], b['available'], b['styles']['vault']) for b in c['bases']])
print('terrain:', c['terrain'])
print('overlays:', sorted((o['id'], o['kind'], o['available']) for o in c['overlays'] if o['id'] in ('footpaths', 'flood-zones')))
print('packs:', c['packs'], c['packs_index_url'])
"
kill $(cat /tmp/sos-accept/api.pid)
```

(If plan 01 exposes the app through a factory, start it the way `dev/run-dev.sh` does instead of `uvicorn sos.main:app`.)

Expected:

```
bases: [('osm', True, '/maps/styles/osm-vault.json'), ('os', True, '/maps/styles/os-night.json')]
terrain: {'contours': '/maps/contours.pmtiles', 'hillshade': '/maps/hillshade.pmtiles'}
overlays: [('flood-zones', 'pmtiles', True), ('footpaths', 'pmtiles', True)]
packs: [{'title': 'Jersey', 'url': '/maps/packs/Jersey.mwm', 'size_bytes': 2590086}] /maps/packs/index.html
```

`available` is true for both bases and both overlays because every `dest` in the fixture manifest exists under `SOS_CORE/maps`; the style URLs come from `styles/index.json`, the terrain URLs from the `contours` and `hillshade` items, and the packs list from `packs/index.json`.

- [ ] **Step 5: Record the milestone**

Append to `docs/hardware-checklist.md` (plan 01's file; create the "Maps" heading if absent) one line: `Maps CI (plan 04): sos build-maps --fixture passed with pmtiles verify on every output on <date>, commit <sha>, fixture base <bytes> bytes`. Commit:

```bash
cd /home/dan/OperationSOS
git add docs/hardware-checklist.md api/tests/fixtures
git commit -m "chore(maps): record the fixture build acceptance for milestone 3"
```

---

## Notes for the full build on the PC (not part of CI)

- `sos build-maps` with no flags builds everything into `~/sos-content/maps` from `~/sos-content/maps-src`; expect roughly 4 GB of downloads (Protomaps extract 3.2 to 3.5 GB, OS products 4.2 GB, Geofabrik 2.4 GB, Copernicus 112 squares at most, Organic Maps 2.6 GB, APK 64 MB) plus several hours of tippecanoe and GDAL time; rerunning skips finished steps, `--force` rebuilds, `--steps overlays verify` rebuilds one layer and re-verifies.
- Fill `FLOOD_EN_URL`, `FLOOD_WA_URL`, `FLOOD_SC_URL`, `FLOOD_NI_URL`, optionally `FLOOD_IE_URL`, `ACCESS_WA_URL` and `OSNI_DTM_URL` in `install/versions.env` before the first full run; a blank value skips that region with a warning and `overlays/index.json` records the regions actually built, and `build.json` records everything else. Copy the resulting sizes from `manifest/maps.json` (written by `verify`) into spec section 16.
- Copy `~/sos-content/maps/` to the box as `/srv/sos/core/maps/` (rsync into `/srv/sos/core/maps/.incoming/` then `mv` each file into place, matching the `rename(2)` rule) and run `sos index` there so `places.csv.gz` is imported.
