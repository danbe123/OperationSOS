import type { LayerSpecification, Map as MlMap, SourceSpecification } from 'maplibre-gl';
import type { Overlay } from '../api/types';
import { pmtilesUrl } from './layers';

export const REGIONS: Record<string, string> = {
  england: 'England', wales: 'Wales', scotland: 'Scotland', ni: 'Northern Ireland', roi: 'Republic of Ireland', iom: 'Isle of Man', ci: 'Channel Islands',
};

export function coverageNote(overlay: Overlay): string | null {
  const missing = Object.keys(REGIONS).filter((r) => !overlay.coverage.includes(r));
  return missing.length ? `No data for ${missing.map((r) => REGIONS[r]).join(', ')}` : null;
}

export function overlaySourceId(id: string): string {
  return `sos-overlay-${id}`;
}

export function overlaySpec(overlay: Overlay): { source: SourceSpecification | null; layers: LayerSpecification[] } {
  if (overlay.kind === 'style-layer' || !overlay.url) return { source: null, layers: [] };
  const source: SourceSpecification = overlay.kind === 'geojson' ? { type: 'geojson', data: overlay.url } : { type: 'vector', url: pmtilesUrl(overlay.url) };
  return { source, layers: overlay.kind === 'geojson' ? overlayLayersFor(overlay, null) : [] };
}

const POLY = ['in', ['geometry-type'], ['literal', ['Polygon', 'MultiPolygon']]];
const LINE = ['in', ['geometry-type'], ['literal', ['LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']]];
const POINT = ['in', ['geometry-type'], ['literal', ['Point', 'MultiPoint']]];

/** A fill/line/circle trio per source layer (null = a GeoJSON source with no source-layer). */
export function overlayLayersFor(overlay: Overlay, sourceLayers: string[] | null): LayerSpecification[] {
  const src = overlaySourceId(overlay.id);
  const groups: (string | null)[] = sourceLayers ?? [null];
  return groups.flatMap((sl) => {
    const suffix = sl ? `-${sl}` : '';
    const base = sl ? { source: src, 'source-layer': sl } : { source: src };
    return [
      { id: `${src}${suffix}-fill`, type: 'fill', ...base, filter: POLY, paint: { 'fill-color': overlay.color, 'fill-opacity': 0.22 } },
      { id: `${src}${suffix}-line`, type: 'line', ...base, filter: LINE, paint: { 'line-color': overlay.color, 'line-width': 2 } },
      { id: `${src}${suffix}-point`, type: 'circle', ...base, filter: POINT, paint: { 'circle-color': overlay.color, 'circle-radius': 6, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.5 } },
    ] as LayerSpecification[];
  });
}

type VectorSourceLike = { vectorLayerIds?: string[] } | undefined;

// Source ids whose vector layers we are still waiting for, per map, so repeated calls never stack listeners.
const pending = new WeakMap<MlMap, Set<string>>();

export function addOverlay(map: MlMap, overlay: Overlay, visible: boolean): void {
  const visibility = visible ? 'visible' : 'none';
  if (overlay.kind === 'style-layer') {
    if (overlay.layer_id && map.getLayer(overlay.layer_id)) map.setLayoutProperty(overlay.layer_id, 'visibility', visibility);
    return;
  }
  const spec = overlaySpec(overlay);
  if (!spec.source) return;
  const src = overlaySourceId(overlay.id);
  if (!map.getSource(src)) map.addSource(src, spec.source);
  const addLayers = (layers: LayerSpecification[]) => {
    for (const l of layers) if (!map.getLayer(l.id)) map.addLayer({ ...l, layout: { ...('layout' in l ? l.layout : {}), visibility } } as LayerSpecification);
  };
  if (overlay.kind === 'geojson') {
    addLayers(spec.layers);
    return;
  }
  const ids = (map.getSource(src) as VectorSourceLike)?.vectorLayerIds;
  if (ids && ids.length > 0) {
    addLayers(overlayLayersFor(overlay, ids));
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
      addLayers(overlayLayersFor(overlay, loaded));
      map.off('sourcedata', onData);
      waiting.delete(src);
    }
  };
  map.on('sourcedata', onData);
}

export function setOverlayVisible(map: MlMap, overlay: Overlay, visible: boolean): void {
  const visibility = visible ? 'visible' : 'none';
  if (overlay.kind === 'style-layer') {
    if (overlay.layer_id && map.getLayer(overlay.layer_id)) map.setLayoutProperty(overlay.layer_id, 'visibility', visibility);
    return;
  }
  const prefix = `${overlaySourceId(overlay.id)}-`;
  for (const l of map.getStyle().layers) if (l.id.startsWith(prefix)) map.setLayoutProperty(l.id, 'visibility', visibility);
}
