// Generates the two Protomaps styles used by the "osm" base: light (the Field theme) and black (Mono).
// Usage: node build-styles.mjs --out DIR [--tiles pmtiles:///maps/uk-ie.pmtiles]
//
// Output filenames follow the map router's contract (api/sos/routers/map.py): styles live at
// `/maps/styles/<base>-<theme>.json`, so this generator writes osm-field.json and osm-mono.json
// (never osm-light.json/osm-black.json).
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { layers, namedFlavor } from "@protomaps/basemaps";

export const GLYPHS = "/maps/fonts/{fontstack}/{range}.pbf";
// Plain text only: no HTML anchor and no embedded URL. The box has no internet, so a link to
// openstreetmap.org would be dead weight, and the generated style must not reference any external host.
export const ATTRIBUTION = "© OpenStreetMap contributors, © Protomaps";
const FONTS = { regular: "Noto Sans Regular", bold: "Noto Sans Medium", italic: "Noto Sans Italic" };

// Ruling R1: the map router (api/sos/routers/map.py) builds style URLs by pure convention as
// `/maps/styles/<base>-<theme>.json` for theme in (field, mono) and reads no index file, so these two
// filenames are load-bearing. light -> field (the paper-and-ink day theme) and the library's own
// `black` flavour -> mono, which is already a pure greyscale sheet: no hue in any of its colours, which
// is what the Mono theme states of itself (web/src/styles/tokens.css) and what the generator's test
// checks layer by layer. Nothing is hand-tuned here, so a basemaps upgrade cannot smuggle a hue in
// without that test saying so.
export const STYLES = [
  { file: "osm-field.json", name: "SOS Field (Protomaps light)", flavor: { ...namedFlavor("light"), ...FONTS }, sprite: "/maps/sprites/v4/light" },
  { file: "osm-mono.json", name: "SOS Mono (Protomaps black)", flavor: { ...namedFlavor("black"), ...FONTS }, sprite: "/maps/sprites/v4/dark" },
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
