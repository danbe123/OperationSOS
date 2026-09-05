import { test } from "node:test";
import assert from "node:assert/strict";
import { validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import { buildAll, GLYPHS, VAULT, STYLES } from "./build-styles.mjs";

// The pinned @protomaps/basemaps@5.7.2 hardcodes a Devanagari fallback face inside its multi-script
// place-name formatting, alongside the three Latin faces set via the flavour's regular/bold/italic keys.
// Confirmed against protomaps/basemaps-assets: it ships exactly these four font directories.
const NOTO = new Set(["Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic", "Noto Sans Devanagari Regular v1"]);

// `text-font` is not always a flat array: this library emits case/match expressions whose branches are
// `["literal", [...]]` (or, deeper still, per-substring `text-font` overrides nested inside a `text-field`
// `format` expression). Walk the whole layout tree, collecting every literal font array under any
// "text-font" key, rather than assuming the value is already a flat array of strings.
//
// Only the outermost value of a "text-font" key may be a bare flat array (the style-spec shorthand for
// "this layer always uses these faces"); once inside an expression (case/match/...), a branch that
// resolves to a font array is always wrapped as ["literal", [...]] by this library, so at any nested
// depth a plain array-of-strings is a condition/argument (e.g. ["get", "script"]) and must NOT be
// mistaken for a font list.
function collectFontFaces(expr, out, top = true) {
  if (!Array.isArray(expr)) return;
  if (top && expr.length > 0 && expr.every((f) => typeof f === "string")) {
    for (const f of expr) out.add(f);
    return;
  }
  if (expr[0] === "literal" && Array.isArray(expr[1]) && expr[1].every((f) => typeof f === "string")) {
    for (const f of expr[1]) out.add(f);
    return;
  }
  for (const item of expr) if (Array.isArray(item)) collectFontFaces(item, out, false);
}

function findTextFontFaces(node, out) {
  if (Array.isArray(node)) {
    for (const item of node) findTextFontFaces(item, out);
  } else if (node && typeof node === "object") {
    for (const [key, value] of Object.entries(node)) {
      if (key === "text-font") collectFontFaces(value, out);
      else findTextFontFaces(value, out);
    }
  }
}

test("three styles are generated in the expected order", () => {
  // Ruling R1: filenames follow the map router's `/maps/styles/<base>-<theme>.json` convention
  // (api/sos/routers/map.py), not the generator's internal light/dark flavour names.
  assert.deepEqual(buildAll("pmtiles:///maps/uk-ie.pmtiles").map(([file]) => file),
    ["osm-field.json", "osm-blackout.json", "osm-vault.json"]);
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
      const faces = new Set();
      findTextFontFaces(layer.layout ?? {}, faces);
      for (const face of faces) assert.ok(NOTO.has(face), `${file}/${layer.id} uses ${face}`);
    }
    // Ruling R7: attribution must be plain text with no HTML anchor and no URL of any kind, since the
    // box has no internet and any live link would just be dead weight.
    assert.doesNotMatch(JSON.stringify(style), /https?:\/\//, `${file} contains an external URL`);
  }
});

test("vault flavour is dark-based with the phosphor palette and Noto fonts", () => {
  assert.equal(VAULT.background, "#05090a");
  assert.equal(VAULT.regular, "Noto Sans Regular");
  const vault = STYLES.find((s) => s.file === "osm-vault.json");
  assert.equal(vault.sprite, "/maps/sprites/v4/dark");
});
