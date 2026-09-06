"""Step `styles`: Protomaps styles from Node, OS Open Zoomstack styles rewritten, sprites and glyphs vendored.

Ruling R1: the map router (api/sos/routers/map.py) builds style URLs by pure convention as
`/maps/styles/<base>-<theme>.json` for base in ("osm", "os") and theme in ("field", "mono"). It
reads no index file, so exactly four style files must exist under `styles/`: osm-field.json and
osm-mono.json (from the Node Protomaps generator) and os-field.json and os-mono.json (from the OS style
rewrite below, where os-mono.json is the OS Night style — the only dark style OS ships). `style_index`
below still writes a `styles/index.json` informational side-table, but it is not load-bearing for any
consumer.
"""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Iterable

from .common import BuildError, Context, fetch_github_tarball, log, pmtiles_metadata, vector_layer_ids

# The pinned @protomaps/basemaps@5.7.2 references a Devanagari fallback face inside its multi-script
# place-name formatting alongside the three Latin faces, so all four must be vendored to keep the style
# self-contained (protomaps/basemaps-assets ships exactly these four font directories).
NOTO_FACES = ("Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic", "Noto Sans Devanagari Regular v1")
OS_FACES = ("Source Sans Pro Regular", "Source Sans Pro Bold", "Source Sans Pro Italic",
            "Source Sans Pro SemiBold", "Open Sans Regular")
FIXTURE_GLYPH_RANGES = ("0-255", "256-511")
# Source OS style file -> the output filename(s) it feeds (Ruling R1). The Outdoor (day/light) style
# becomes os-field.json and the Night (dark) style becomes os-mono.json. OS ships no greyscale style,
# so os-mono.json is the nearest thing it has: a dark sheet the map screen washes with the theme's own
# ground colour (web/src/screens/map.css).
OS_STYLE_MAP: dict[str, tuple[str, ...]] = {
    "OS Open Zoomstack - Outdoor.json": ("os-field.json",),
    "OS Open Zoomstack - Night.json": ("os-mono.json",),
}
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
    """Informational side-table only (Ruling R1): no consumer reads this file. The map router builds
    style URLs by convention (`/maps/styles/<base>-<theme>.json`), which is what actually matters."""
    return {
        "osm": {"field": "/maps/styles/osm-field.json", "mono": "/maps/styles/osm-mono.json",
                "tiles": f"/maps/{base_name}"},
        "os": {"field": "/maps/styles/os-field.json", "mono": "/maps/styles/os-mono.json",
               "tiles": "/maps/os-zoomstack.pmtiles"},
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
        return ["styles/index.json", "styles/osm-field.json", "styles/osm-mono.json",
                "styles/os-field.json", "styles/os-mono.json",
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
        for src_name, out_names in OS_STYLE_MAP.items():
            style = json.loads((os_gl / src_name).read_text())
            new = rewrite_os_style(style)
            missing = missing_source_layers(new, present)
            if missing:
                raise BuildError(f"{src_name} uses source-layers absent from os-zoomstack.pmtiles: {sorted(missing)}")
            unknown_fonts = style_fonts(new) - set(OS_FACES)
            if unknown_fonts:
                raise BuildError(f"{src_name} uses fonts that are not vendored: {sorted(unknown_fonts)}")
            rendered = json.dumps(new, indent=1) + "\n"
            for out_name in out_names:
                (styles_dir / out_name).write_text(rendered)

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
