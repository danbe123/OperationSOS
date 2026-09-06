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

export function setTerrainVisible(map: MlMap, on: boolean): void {
  for (const id of TERRAIN_LAYER_IDS) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
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
