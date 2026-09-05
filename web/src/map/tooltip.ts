import maplibregl, { type Map as MlMap, type MapGeoJSONFeature, type MapMouseEvent } from 'maplibre-gl';
import type { Overlay } from '../api/types';
import { describeFeature, type FeatureDescription } from './describe';

const SOURCE_PREFIX = 'sos-overlay-';
/** Half-width in px of the box queried around the pointer: thin footpath lines are hard to hit exactly, and a finger is wider than a mouse. */
const HOVER_PAD = 5;
const TAP_PAD = 14;

type Point = { x: number; y: number };
type PointerEventLike = MapMouseEvent & { point: Point; lngLat: { lng: number; lat: number }; originalEvent?: { pointerType?: string } };

/** The overlay layer ids currently in the style and switched on. */
export function overlayLayerIds(map: MlMap): string[] {
  return map.getStyle().layers
    .filter((l) => l.id.startsWith(SOURCE_PREFIX) && (l.layout?.visibility ?? 'visible') !== 'none')
    .map((l) => l.id);
}

/** Points over lines over polygons: the small thing under the pointer, not the flood zone it sits in. */
export function pickFeature(features: MapGeoJSONFeature[]): MapGeoJSONFeature | undefined {
  const rank = (f: MapGeoJSONFeature) => (f.layer.id.endsWith('-point') ? 0 : f.layer.id.endsWith('-line') ? 1 : 2);
  return [...features].sort((a, b) => rank(a) - rank(b))[0];
}

export function describeMapFeature(feature: MapGeoJSONFeature, overlays: Overlay[]): FeatureDescription {
  const overlayId = feature.source.startsWith(SOURCE_PREFIX) ? feature.source.slice(SOURCE_PREFIX.length) : feature.source;
  const overlay = overlays.find((o) => o.id === overlayId);
  return describeFeature(overlayId, feature.properties, { sourceLayer: feature.sourceLayer, overlayTitle: overlay?.title });
}

/** Plain DOM (text nodes only, so property values are never parsed as HTML). */
export function renderDescription(d: FeatureDescription): HTMLElement {
  const root = document.createElement('div');
  root.className = 'map-tip';
  root.setAttribute('role', 'tooltip');
  const title = document.createElement('strong');
  title.className = 'map-tip-title';
  title.textContent = d.title;
  root.appendChild(title);
  const overlay = document.createElement('div');
  overlay.className = 'map-tip-overlay';
  overlay.textContent = d.overlay;
  root.appendChild(overlay);
  if (d.rows.length) {
    const list = document.createElement('dl');
    list.className = 'map-tip-rows';
    for (const [label, value] of d.rows) {
      const row = document.createElement('div');
      const dt = document.createElement('dt');
      dt.textContent = label;
      const dd = document.createElement('dd');
      dd.textContent = value;
      row.append(dt, dd);
      list.appendChild(row);
    }
    root.appendChild(list);
  }
  return root;
}

/**
 * One popup for every overlay feature: it follows the pointer over points, lines and polygons, and a tap
 * (or click) pins it until the next tap on empty map. The popup is a DOM overlay and the handlers hang off
 * the map, not the style, so both survive a base switch through setStyle. Returns a detach function.
 */
export function attachFeatureTooltip(map: MlMap, overlays: () => Overlay[]): () => void {
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, closeOnMove: false, focusAfterOpen: false, className: 'map-tip-popup', maxWidth: 'none', offset: 12 });
  let pinned = false;
  let shownKey: string | null = null;

  const featureAt = (point: Point, pad: number): MapGeoJSONFeature | undefined => {
    const layers = overlayLayerIds(map);
    if (!layers.length) return undefined;
    const box: [[number, number], [number, number]] = [[point.x - pad, point.y - pad], [point.x + pad, point.y + pad]];
    return pickFeature(map.queryRenderedFeatures(box, { layers }));
  };
  const keyOf = (f: MapGeoJSONFeature) => `${f.layer.id}:${f.id ?? JSON.stringify(f.properties)}`;
  const setCursor = (pointer: boolean) => { map.getCanvas().style.cursor = pointer ? 'pointer' : ''; };

  const show = (feature: MapGeoJSONFeature, at: { lng: number; lat: number }) => {
    const key = keyOf(feature);
    if (key !== shownKey) {
      popup.setDOMContent(renderDescription(describeMapFeature(feature, overlays())));
      shownKey = key;
    }
    popup.setLngLat([at.lng, at.lat]);
    if (!popup.isOpen()) popup.addTo(map);
  };
  const hide = () => {
    if (popup.isOpen()) popup.remove();
    shownKey = null;
    pinned = false;
  };

  const onMove = (e: PointerEventLike) => {
    const feature = featureAt(e.point, HOVER_PAD);
    setCursor(Boolean(feature));
    if (pinned) return;
    if (feature) show(feature, e.lngLat);
    else if (popup.isOpen()) hide();
  };
  const onLeave = () => {
    setCursor(false);
    if (!pinned) hide();
  };
  const onClick = (e: PointerEventLike) => {
    const touch = e.originalEvent?.pointerType === 'touch';
    const feature = featureAt(e.point, touch ? TAP_PAD : HOVER_PAD);
    if (!feature) { hide(); return; }
    pinned = false;
    show(feature, e.lngLat);
    pinned = true;
  };

  map.on('mousemove', onMove);
  map.on('click', onClick);
  map.getCanvas().addEventListener('mouseleave', onLeave);
  return () => {
    map.off('mousemove', onMove);
    map.off('click', onClick);
    map.getCanvas().removeEventListener('mouseleave', onLeave);
    hide();
  };
}
