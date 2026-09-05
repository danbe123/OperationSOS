// Generates the three Protomaps styles used by the "osm" base: light (Field theme), dark (Blackout) and
// the custom Vault flavour. Usage: node build-styles.mjs --out DIR [--tiles pmtiles:///maps/uk-ie.pmtiles]
//
// Output filenames follow the map router's contract (api/sos/routers/map.py): styles live at
// `/maps/styles/<base>-<theme>.json`, so this generator writes osm-field.json, osm-blackout.json and
// osm-vault.json (never osm-light.json/osm-dark.json).
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { layers, namedFlavor } from "@protomaps/basemaps";

export const GLYPHS = "/maps/fonts/{fontstack}/{range}.pbf";
// Plain text only: no HTML anchor and no embedded URL. The box has no internet, so a link to
// openstreetmap.org would be dead weight, and the generated style must not reference any external host.
export const ATTRIBUTION = "© OpenStreetMap contributors, © Protomaps";
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

// Ruling R1: the map router (api/sos/routers/map.py) builds style URLs by pure convention as
// `/maps/styles/<base>-<theme>.json` for theme in (vault, field, blackout) and reads no index file, so
// these three filenames are load-bearing. light -> field (the day/outdoor theme), the custom phosphor
// VAULT flavour -> vault (the dedicated dark bunker theme), and plain dark -> blackout (the low-light
// fallback theme distinct from Vault's custom palette).
export const STYLES = [
  { file: "osm-field.json", name: "SOS Field (Protomaps light)", flavor: { ...namedFlavor("light"), ...FONTS }, sprite: "/maps/sprites/v4/light" },
  { file: "osm-blackout.json", name: "SOS Blackout (Protomaps dark)", flavor: { ...namedFlavor("dark"), ...FONTS }, sprite: "/maps/sprites/v4/dark" },
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
