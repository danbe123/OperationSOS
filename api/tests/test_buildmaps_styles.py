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
    # Ruling R1: styles live at /maps/styles/<base>-<theme>.json (api/sos/routers/map.py's own contract,
    # read by pure convention - no index.json is consumed). os-mono points at the OS Night style, the
    # only dark style OS ships.
    index = styles.style_index("test.pmtiles")
    assert index["osm"] == {"field": "/maps/styles/osm-field.json", "mono": "/maps/styles/osm-mono.json",
                            "tiles": "/maps/test.pmtiles"}
    assert index["os"]["field"] == "/maps/styles/os-field.json"
    assert index["os"]["mono"] == "/maps/styles/os-mono.json"
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
    pruned = styles.prune_overlay_fragment(frag, {"water": "pmtiles", "airports": "geojson", "access-land": "geojson"})
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
    # Ruling R1: the Node generator writes osm-field.json and osm-mono.json (not the internal
    # light/dark/black flavour names) so the fake mirrors the real build-styles.mjs output filenames.
    for name in ("osm-field.json", "osm-mono.json"):
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
                                                                 "airports": {"kind": "geojson", "file": "overlays/airports.geojson"}}))
    styles.StylesStep().run(ctx)
    assert runner.find("pnpm", "install")[0] == ["pnpm", "install", "--frozen-lockfile"]
    node = runner.find("node", "build-styles.mjs")[0]
    assert node[node.index("--tiles") + 1] == "pmtiles:///maps/test.pmtiles"
    assert node[node.index("--out") + 1] == str(ctx.incoming / "styles")
    assert not runner.find("aria2c"), "assets already in the cache must not be downloaded"
    out = ctx.out
    assert json.loads((out / "styles" / "index.json").read_text())["osm"]["tiles"] == "/maps/test.pmtiles"
    # Ruling R1: exactly four load-bearing style files, named for the map router's convention.
    field = json.loads((out / "styles" / "os-field.json").read_text())
    assert field["sources"]["os"]["url"] == "pmtiles:///maps/os-zoomstack.pmtiles"
    assert (out / "styles" / "os-mono.json").exists() and (out / "styles" / "osm-mono.json").exists() \
        and (out / "styles" / "osm-field.json").exists()
    assert not (out / "styles" / "os-vault.json").exists() and not (out / "styles" / "os-blackout.json").exists()
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
