import maplibregl, { type LayerSpecification, type Map as MlMap, type SourceSpecification, type TransformStyleFunction } from 'maplibre-gl';
import { EtagMismatch, Protocol } from 'pmtiles';
import type { MapConfig } from '../api/types';
import type { Theme } from '../theme/ThemeProvider';

export const SOS_PREFIX = 'sos-';
export const TERRAIN_LAYER_IDS = ['sos-hillshade', 'sos-contours'];

let registered = false;
export function registerPmtilesProtocol(): void {
  if (registered) return;
  const protocol = new Protocol({ metadata: true });
  maplibregl.addProtocol('pmtiles', protocol.tile);
  registered = true;
}

/** `pmtiles://` + the absolute URL of a file under /maps. */
export function pmtilesUrl(path: string): string {
  return `pmtiles://${new URL(path, window.location.origin).href}`;
}

/** For setStyle: keep every sos- source and layer. Terrain goes below the first symbol layer of the new base; overlays go on top. */
export const carryStyleAcross: TransformStyleFunction = (previous, next) => {
  if (!previous) return next;
  const sources: Record<string, SourceSpecification> = { ...next.sources };
  for (const [id, src] of Object.entries(previous.sources ?? {})) if (id.startsWith(SOS_PREFIX)) sources[id] = src;
  const kept = (previous.layers ?? []).filter((l) => l.id.startsWith(SOS_PREFIX));
  const terrain = kept.filter((l) => TERRAIN_LAYER_IDS.includes(l.id));
  const overlays = kept.filter((l) => !TERRAIN_LAYER_IDS.includes(l.id));
  const layers = [...next.layers];
  const firstSymbol = layers.findIndex((l) => l.type === 'symbol');
  if (firstSymbol === -1) layers.push(...terrain);
  else layers.splice(firstSymbol, 0, ...terrain);
  return { ...next, sources, layers: [...layers, ...overlays] };
};

/** Every colour the box draws on top of the base map, by theme.
 *
 * Field is paper and ink and keeps its hues: an amber pin, a green home, an orange measuring line.
 * Mono states no hue anywhere, the map included, and a mono base sheet is white lines on black — so
 * an annotation there is white or a light grey with a black outline behind it, which is what makes
 * it a pin rather than another road. */
export type Annotations = {
  /** A pin somebody dropped. */
  pin: string;
  /** The one point a `?label=` link asked the map to show. */
  label: string;
  /** The outline around both, so a pin is still a pin over a bright sheet. */
  pinStroke: string;
  /** Where the household lives: a filled disc and the ring around it. */
  home: string;
  homeStroke: string;
  /** The straight line drawn to a facility, and the line being measured. */
  route: string;
  measure: string;
  /** The ink a caption is written in, and the halo behind it. The two are opposites and are the one
   * pair that must never be read from the mark they name: "⌂ Home" written in the home marker's own
   * white ring, over a white halo, is a white word on white paper. */
  labelInk: string;
  halo: string;
  /** How thick a ring the measuring points carry. Field draws them as bare orange dots, as it always
   * has; Mono needs the ring to keep a white dot off a white road. */
  measureRing: number;
};

const FIELD_ANNOTATIONS: Annotations = {
  pin: '#ffb000', label: '#1e88e5', pinStroke: '#000000',
  home: '#1b5e20', homeStroke: '#ffffff',
  route: '#1b5e20', measure: '#ff3d00',
  labelInk: '#000000', halo: '#ffffff', measureRing: 0,
};

/** White on black, and a light grey where two things must be told apart without hue. */
const MONO_ANNOTATIONS: Annotations = {
  pin: '#ffffff', label: '#d0d0d0', pinStroke: '#000000',
  home: '#000000', homeStroke: '#ffffff',
  route: '#ffffff', measure: '#ffffff',
  labelInk: '#ffffff', halo: '#000000', measureRing: 1.5,
};

export function annotations(theme: Theme): Annotations {
  return theme === 'mono' ? MONO_ANNOTATIONS : FIELD_ANNOTATIONS;
}

/** The paint for every layer the box draws over the base map, keyed by layer id.
 *
 * One table, so what the screen paints and what a test reads are the same object rather than two
 * copies of the same intention that can drift apart. `MapView` adds each layer with its entry and
 * sets the same entry again afterwards, which is what repaints a layer carried across the style
 * reload a theme switch causes. */
export function annotationPaint(theme: Theme): Record<string, Record<string, unknown>> {
  const c = annotations(theme);
  const caption = { 'text-color': c.labelInk, 'text-halo-color': c.halo, 'text-halo-width': 1.5 };
  return {
    'sos-pins-point': {
      'circle-radius': 8,
      'circle-color': ['match', ['get', 'kind'], 'label', c.label, c.pin],
      'circle-stroke-color': c.pinStroke, 'circle-stroke-width': 2,
    },
    'sos-pins-label': { ...caption },
    'sos-home-point': { 'circle-radius': 11, 'circle-color': c.home, 'circle-stroke-color': c.homeStroke, 'circle-stroke-width': 3 },
    'sos-home-label': { ...caption },
    'sos-route-line': { 'line-color': c.route, 'line-width': 4, 'line-dasharray': [3, 1.5] },
    'sos-measure-line': { 'line-color': c.measure, 'line-width': 3, 'line-dasharray': [2, 1] },
    'sos-measure-point': { 'circle-radius': 5, 'circle-color': c.measure, 'circle-stroke-color': c.pinStroke, 'circle-stroke-width': c.measureRing },
  };
}

/** How one overlay is painted in this theme. The overlay's own colour is the manifest's, and Field
 * uses it as it stands; Mono has no hue to spend, so the footpaths — the overlay a walker opens the
 * map for — are white and dashed, which tells them from the white roads under them, and everything
 * else is a light grey. A fill sits lighter on black than on paper, where a fifth of a hue is quiet
 * and a fifth of white is a wash over the sheet. */
export function overlayPaint(overlay: { id: string; color: string }, theme: Theme): {
  color: string; fillOpacity: number; stroke: string; dash: number[] | null;
} {
  if (theme !== 'mono') return { color: overlay.color, fillOpacity: 0.22, stroke: '#ffffff', dash: null };
  if (overlay.id === 'footpaths') return { color: '#ffffff', fillOpacity: 0.12, stroke: '#000000', dash: [2, 1.5] };
  return { color: '#d0d0d0', fillOpacity: 0.12, stroke: '#000000', dash: null };
}

export function terrainSpec(config: MapConfig, theme: Theme): { sources: Record<string, SourceSpecification>; layers: LayerSpecification[] } {
  const sources: Record<string, SourceSpecification> = {};
  const layers: LayerSpecification[] = [];
  if (config.terrain.hillshade) {
    sources['sos-hillshade'] = { type: 'raster', url: pmtilesUrl(config.terrain.hillshade), tileSize: 256 };
    layers.push({ id: 'sos-hillshade', type: 'raster', source: 'sos-hillshade', paint: { 'raster-opacity': theme === 'field' ? 0.35 : 0.22 } });
  }
  if (config.terrain.contours) {
    sources['sos-contours'] = { type: 'vector', url: pmtilesUrl(config.terrain.contours) };
    layers.push({
      id: 'sos-contours', type: 'line', source: 'sos-contours', 'source-layer': 'contour_line', minzoom: 11,
      paint: { 'line-color': contourColour(theme), 'line-width': 0.8, 'line-opacity': 0.7 },
    });
  }
  return { sources, layers };
}
function contourColour(theme: Theme): string {
  // Mono states no hue anywhere, the map included, so its contours are a plain grey.
  return theme === 'mono' ? '#6e6e6e' : '#b08050';
}

export function addTerrain(map: MlMap, config: MapConfig, theme: Theme): void {
  const spec = terrainSpec(config, theme);
  for (const [id, source] of Object.entries(spec.sources)) if (!map.getSource(id)) map.addSource(id, source);
  const firstSymbol = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;
  for (const layer of spec.layers) {
    if (map.getLayer(layer.id)) continue;
    map.addLayer(layer, firstSymbol);
  }
  if (map.getLayer('sos-contours')) map.setPaintProperty('sos-contours', 'line-color', contourColour(theme));
}

/** Contours and hillshade have a chip each, so each is shown or hidden on its own. */
export function setTerrainLayerVisible(map: MlMap, id: 'sos-contours' | 'sos-hillshade', on: boolean): void {
  if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
}

export function isEtagMismatch(err: unknown): boolean {
  return err instanceof EtagMismatch || (err instanceof Error && err.name === 'EtagMismatch');
}

/** The PMTiles file changed underneath us (a map update landed): rebuild the source and its layers in place. */
export function recreateSource(map: MlMap, sourceId: string): void {
  const style = map.getStyle();
  const source = style.sources[sourceId];
  if (!source) return;
  const layers = style.layers;
  const mine = layers.filter((l) => 'source' in l && l.source === sourceId);
  const positions = mine.map((layer) => {
    const idx = layers.indexOf(layer);
    const before = layers.slice(idx + 1).find((x) => !mine.includes(x));
    return { layer, before: before?.id };
  });
  for (const l of mine) map.removeLayer(l.id);
  map.removeSource(sourceId);
  map.addSource(sourceId, source);
  for (const p of positions) map.addLayer(p.layer, p.before);
}
