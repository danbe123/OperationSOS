import type { LayerSpecification, Map as MlMap, SourceSpecification } from 'maplibre-gl';
import type { Overlay } from '../api/types';
import type { Theme } from '../theme/ThemeProvider';
import { overlayPaint, pmtilesUrl } from './layers';

export const REGIONS: Record<string, string> = {
  england: 'England', wales: 'Wales', scotland: 'Scotland', ni: 'Northern Ireland', roi: 'Republic of Ireland', iom: 'Isle of Man', ci: 'Channel Islands',
};

export function coverageNote(overlay: Overlay): string | null {
  if (overlay.coverage_note) return overlay.coverage_note;
  const missing = Object.keys(REGIONS).filter((r) => !overlay.coverage.includes(r));
  return missing.length ? `No data for ${missing.map((r) => REGIONS[r]).join(', ')}` : null;
}

export function overlaySourceId(id: string): string {
  return `sos-overlay-${id}`;
}

export function overlaySpec(overlay: Overlay, theme: Theme): { source: SourceSpecification | null; layers: LayerSpecification[] } {
  if (overlay.kind === 'style-layer' || !overlay.url) return { source: null, layers: [] };
  const source: SourceSpecification = overlay.kind === 'geojson' ? { type: 'geojson', data: overlay.url } : { type: 'vector', url: pmtilesUrl(overlay.url) };
  return { source, layers: overlay.kind === 'geojson' ? overlayLayersFor(overlay, null, theme) : [] };
}

const POLY = ['in', ['geometry-type'], ['literal', ['Polygon', 'MultiPolygon']]];
const LINE = ['in', ['geometry-type'], ['literal', ['LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']]];
const POINT = ['in', ['geometry-type'], ['literal', ['Point', 'MultiPoint']]];

/** A fill/line/circle trio per source layer (null = a GeoJSON source with no source-layer), in the
 * theme's own colours: Mono has no hue to give an overlay, so it separates them by tone and dash. */
export function overlayLayersFor(overlay: Overlay, sourceLayers: string[] | null, theme: Theme): LayerSpecification[] {
  const src = overlaySourceId(overlay.id);
  const paint = overlayPaint(overlay, theme);
  const groups: (string | null)[] = sourceLayers ?? [null];
  return groups.flatMap((sl) => {
    const suffix = sl ? `-${sl}` : '';
    const base = sl ? { source: src, 'source-layer': sl } : { source: src };
    return [
      { id: `${src}${suffix}-fill`, type: 'fill', ...base, filter: POLY, paint: { 'fill-color': paint.color, 'fill-opacity': paint.fillOpacity } },
      { id: `${src}${suffix}-line`, type: 'line', ...base, filter: LINE, paint: { 'line-color': paint.color, 'line-width': 2, ...(paint.dash ? { 'line-dasharray': paint.dash } : {}) } },
      { id: `${src}${suffix}-point`, type: 'circle', ...base, filter: POINT, paint: { 'circle-color': paint.color, 'circle-radius': 6, 'circle-stroke-color': paint.stroke, 'circle-stroke-width': 1.5 } },
    ] as LayerSpecification[];
  });
}

type VectorSourceLike = { vectorLayerIds?: string[] } | undefined;

// Source ids whose vector layers we are still waiting for, per map, so repeated calls never stack listeners.
const pending = new WeakMap<MlMap, Set<string>>();
const desiredVisibility = new WeakMap<MlMap, Map<string, boolean>>();

function rememberVisibility(map: MlMap, id: string, visible: boolean): void {
  const states = desiredVisibility.get(map) ?? new Map<string, boolean>();
  states.set(id, visible);
  desiredVisibility.set(map, states);
}

export function addOverlay(map: MlMap, overlay: Overlay, visible: boolean, theme: Theme): void {
  rememberVisibility(map, overlay.id, visible);
  const visibility = visible ? 'visible' : 'none';
  if (overlay.kind === 'style-layer') {
    if (overlay.layer_id && map.getLayer(overlay.layer_id)) map.setLayoutProperty(overlay.layer_id, 'visibility', visibility);
    return;
  }
  const spec = overlaySpec(overlay, theme);
  if (!spec.source) return;
  const src = overlaySourceId(overlay.id);
  if (!map.getSource(src)) map.addSource(src, spec.source);
  const addLayers = (layers: LayerSpecification[]) => {
    const current = (desiredVisibility.get(map)?.get(overlay.id) ?? visible) ? 'visible' : 'none';
    for (const l of layers) {
      // A layer already there was carried across a style reload with the colours of the theme it was
      // drawn in; a theme switch is exactly when that reload happens, so it is repainted rather than
      // left green on a screen with no green anywhere else.
      if (map.getLayer(l.id)) {
        const paint = ('paint' in l ? l.paint : undefined) ?? {};
        for (const [key, value] of Object.entries(paint)) map.setPaintProperty(l.id, key, value);
        if (l.type === 'line' && !('line-dasharray' in paint)) map.setPaintProperty(l.id, 'line-dasharray', undefined);
        continue;
      }
      map.addLayer({ ...l, layout: { ...('layout' in l ? l.layout : {}), visibility: current } } as LayerSpecification);
    }
  };
  if (overlay.kind === 'geojson') {
    addLayers(spec.layers);
    return;
  }
  const ids = (map.getSource(src) as VectorSourceLike)?.vectorLayerIds;
  if (ids && ids.length > 0) {
    addLayers(overlayLayersFor(overlay, ids, theme));
    return;
  }
  // The vector layer names come from the file's metadata once the source loads.
  const waiting = pending.get(map) ?? new Set<string>();
  pending.set(map, waiting);
  if (waiting.has(src)) return;
  waiting.add(src);
  const onData = (e: { sourceId?: string; isSourceLoaded?: boolean }) => {
    if (e.sourceId !== src || !e.isSourceLoaded) return;
    const loaded = (map.getSource(src) as VectorSourceLike)?.vectorLayerIds;
    if (loaded && loaded.length > 0) {
      addLayers(overlayLayersFor(overlay, loaded, theme));
      map.off('sourcedata', onData);
      waiting.delete(src);
    }
  };
  map.on('sourcedata', onData);
}

export function setOverlayVisible(map: MlMap, overlay: Overlay, visible: boolean): void {
  rememberVisibility(map, overlay.id, visible);
  const visibility = visible ? 'visible' : 'none';
  if (overlay.kind === 'style-layer') {
    if (overlay.layer_id && map.getLayer(overlay.layer_id)) map.setLayoutProperty(overlay.layer_id, 'visibility', visibility);
    return;
  }
  const prefix = `${overlaySourceId(overlay.id)}-`;
  for (const l of map.getStyle().layers) if (l.id.startsWith(prefix)) map.setLayoutProperty(l.id, 'visibility', visibility);
}
