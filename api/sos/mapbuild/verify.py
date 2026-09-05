"""Step `verify`: pmtiles verify on every archive, base map checks, style sources, overlay coverage,
and measured sizes written back into the manifest.

manifest/maps.json carries the non-overlay map outputs (base maps, terrain, styles, sprites, glyphs,
places, packs, the apk). footpaths and flood-zones live only in manifest/overlays.json (Ruling R6) —
duplicating their ids/dests into maps.json would trip the id/dest uniqueness rules that
`sos.manifest.validate_manifests` enforces across the whole `manifest/` tree. So this step measures and
writes sizes into both manifest files: `output_sizes` for the ids that live in maps.json, `overlay_sizes`
for whichever overlay ids the `overlays` step actually built (named in `overlays/index.json`)."""
from __future__ import annotations

import json
from pathlib import Path

from .base import PROBES_FIXTURE, PROBES_FULL, check_base
from .common import BuildError, Context, FIXTURE_MAX_BYTES, dir_size, log, pmtiles_header, pmtiles_verify, tile_exists

MANIFEST_OUTPUTS = {  # manifest/maps.json item id -> path under <out>; uk-ie is added per context (ctx.base_name)
    "os-zoomstack": "os-zoomstack.pmtiles",
    "contours": "contours.pmtiles",
    "hillshade": "hillshade.pmtiles",
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


def _collect_font_faces(expr, out: set[str], top: bool = True) -> None:
    """Walk a `text-font` value, which is either a flat list of face-name strings or a nested
    case/match expression (protomaps-basemaps emits the latter for internationalised labels, e.g.
    `["case", ["==", ["get", "script"], "Devanagari"], ["literal", [...]], ["literal", [...]]]`).
    Only a top-level flat array of strings, or a `["literal", [...]]` branch, names real faces --
    everything else (conditions, operators, get expressions) is walked but never treated as a face."""
    if not isinstance(expr, list):
        return
    if top and expr and all(isinstance(f, str) for f in expr):
        out.update(expr)
        return
    if expr and expr[0] == "literal" and isinstance(expr[1], list) and all(isinstance(f, str) for f in expr[1]):
        out.update(expr[1])
        return
    for item in expr:
        if isinstance(item, list):
            _collect_font_faces(item, out, top=False)


def _find_text_font_faces(node, out: set[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _find_text_font_faces(item, out)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "text-font":
                _collect_font_faces(value, out)
            else:
                _find_text_font_faces(value, out)


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
            faces: set[str] = set()
            _find_text_font_faces(layer.get("layout", {}), faces)
            for face in sorted(faces):
                if not (out / "fonts" / face / "0-255.pbf").exists():
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


def check_overlays(out: Path, overlays_manifest: Path, fixture: bool = False) -> list[str]:
    """Ruling R5: `overlays/index.json` must exist and name only files that exist under `<out>`, and
    every overlay item in `manifest/overlays.json` that this build actually produced (named in the
    index) must resolve to a real file at its `source.artifact`. An overlay id absent from the index is
    skipped rather than failed: a deliberately partial `--steps` run that never reaches the `overlays`
    step (or a manifest item added ahead of the code that builds it) should not fail verification for
    ids this run was never asked to build.

    Ruling R15: the second check (the `source.artifact` cross-check) is skipped entirely in fixture
    mode. `manifest/overlays.json` declares access-land/airports-military/water at their real
    production-scale kind (pmtiles, since full UK-wide data crosses the 5MB tippecanoe threshold), but
    at fixture scale every overlay's tiny sample input legitimately finalises as geojson under the
    uniform 5MB rule (Task 7's `finalise()`) -- so the manifest's hardcoded production-scale artifact
    path can never match a fixture build's real output for those overlays. This mirrors
    `overlays.verify_manifest_kinds`, which is likewise gated to `not ctx.fixture`. The first loop
    (every file `overlays/index.json` names actually exists under `<out>`) stays unconditional: it is
    meaningful regardless of fixture scale."""
    index_path = out / "overlays" / "index.json"
    if not index_path.exists():
        return ["overlays/index.json is missing"]
    problems: list[str] = []
    index = json.loads(index_path.read_text())
    for overlay_id, entry in index.items():
        if not (out / entry["file"]).exists():
            problems.append(f"overlays/index.json: {overlay_id} -> {entry['file']} is missing")
    if not fixture and overlays_manifest.exists():
        for item in json.loads(overlays_manifest.read_text()).get("items", []):
            overlay_id = item.get("id")
            if overlay_id not in index:
                continue
            artifact = item.get("source", {}).get("artifact", "")
            if artifact and not (out / artifact).exists():
                problems.append(f"manifest/overlays.json: {overlay_id} artifact {artifact!r} is missing from the output")
    return sorted(set(problems))


def output_sizes(ctx: Context) -> dict[str, int]:
    """Measured sizes for the ids that live in manifest/maps.json."""
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


def overlay_sizes(ctx: Context) -> dict[str, int]:
    """Measured sizes for every overlay id this build produced (named in `overlays/index.json`), for
    manifest/overlays.json -- footpaths and flood-zones included, since their ids live there, not in
    manifest/maps.json (Ruling R6)."""
    index_path = ctx.out / "overlays" / "index.json"
    if not index_path.exists():
        return {}
    index = json.loads(index_path.read_text())
    sizes: dict[str, int] = {}
    for overlay_id, entry in index.items():
        path = ctx.out / entry["file"]
        if path.is_file():
            sizes[overlay_id] = path.stat().st_size
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


def write_fixture_overlays_manifest(source: Path, dest: Path, index: dict) -> None:
    """Fixture counterpart of write_fixture_manifest, for manifest/overlays.json. At fixture scale every
    overlay's tiny sample input legitimately finalises under Task 7's uniform 5MB rule (`finalise()`), so
    an id this run actually built (named in `index`, the loaded `overlays/index.json`) may have produced
    a different `kind` than the real, production-scale manifest declares -- this mirrors the reasoning
    already established in `check_overlays`'s R15 fixture gate and `overlays.verify_manifest_kinds`. When
    that happens, rewrite the item's kind/source.artifact/dest/overlay.kind to the real produced values;
    an id absent from `index`, or one whose kind already matches, is copied verbatim."""
    doc = json.loads(source.read_text())
    items = []
    for item in doc["items"]:
        entry = index.get(item["id"])
        if entry is not None and entry["kind"] != item["kind"]:
            item["kind"] = entry["kind"]
            item["source"]["artifact"] = entry["file"]
            item["dest"] = f"maps/{entry['file']}"
            item["overlay"]["kind"] = entry["kind"]
        items.append(item)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"items": items}, indent=2, ensure_ascii=False) + "\n")


class VerifyStep:
    id = "verify"

    def outputs(self, ctx: Context) -> list[str]:
        # No declared outputs: run_steps's "already up to date, skip" branch only fires when a step
        # declares outputs and every one of them already exists, so an empty list means verify always
        # runs (and always logs its own "[verify] done in Ns" line) when it is selected.
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
        problems += check_overlays(ctx.out, ctx.repo / "manifest" / "overlays.json", fixture=ctx.fixture)
        for rel in MANIFEST_OUTPUTS.values():
            if not (ctx.out / rel).exists():
                problems.append(f"missing output {rel}")
        if problems:
            raise BuildError("verification failed:\n  " + "\n  ".join(problems))

        sizes = output_sizes(ctx)
        overlay_size_map = overlay_sizes(ctx)
        manifest = ctx.repo / "manifest" / "maps.json"
        overlays_manifest = ctx.repo / "manifest" / "overlays.json"
        if ctx.fixture:
            target = ctx.repo / "api" / "tests" / "fixtures" / "manifest" / "maps.json"
            write_fixture_manifest(manifest, target, ctx.base_name)
            updated = update_manifest_sizes(target, sizes)
            # The real manifest/overlays.json is never touched in fixture mode -- only this fixture copy is.
            overlays_target = ctx.repo / "api" / "tests" / "fixtures" / "manifest" / "overlays.json"
            index_path = ctx.out / "overlays" / "index.json"
            index = json.loads(index_path.read_text()) if index_path.exists() else {}
            write_fixture_overlays_manifest(overlays_manifest, overlays_target, index)
            updated_overlays = update_manifest_sizes(overlays_target, overlay_size_map)
        else:
            target = manifest
            overlays_target = overlays_manifest
            updated = update_manifest_sizes(target, sizes)
            updated_overlays = update_manifest_sizes(overlays_manifest, overlay_size_map) if overlays_manifest.exists() else []

        # build.json is a build report for humans and CI, not a servable map asset a client could be
        # mid-read of, so it is written directly rather than through the .incoming/ + os.replace staging
        # convention used for the actual map outputs elsewhere in this pipeline (Ruling R10a).
        report = {"fixture": ctx.fixture, "build": ctx.build, "bbox": list(ctx.bbox),
                  "verified_archives": [str(a.relative_to(ctx.out)) for a in found],
                  "sizes": sizes, "overlay_sizes": overlay_size_map,
                  "manifest": str(target.relative_to(ctx.repo)), "updated": updated,
                  "overlays_manifest": str(overlays_target.relative_to(ctx.repo)), "updated_overlays": updated_overlays}
        (ctx.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        log.info("[verify] OK: %d archives verified; sizes written to %s", len(found), target.relative_to(ctx.repo))
