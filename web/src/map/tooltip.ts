import maplibregl, { type Map as MlMap, type MapGeoJSONFeature, type MapMouseEvent } from 'maplibre-gl';
import type { Overlay, PlaceGuidance } from '../api/types';
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

/** The overlay a feature came from: its source id less the `sos-overlay-` prefix. */
export function overlayIdOf(feature: MapGeoJSONFeature): string {
  return feature.source.startsWith(SOURCE_PREFIX) ? feature.source.slice(SOURCE_PREFIX.length) : feature.source;
}

/** One tapped place: everything the describer said about the feature, plus where on the ground it was tapped. */
export type TappedPlace = FeatureDescription & { lat: number; lon: number; overlayId: string };

export function describeMapFeature(feature: MapGeoJSONFeature, overlays: Overlay[]): FeatureDescription {
  const overlayId = overlayIdOf(feature);
  const overlay = overlays.find((o) => o.id === overlayId);
  return describeFeature(overlayId, feature.properties, { sourceLayer: feature.sourceLayer, overlayTitle: overlay?.title });
}

/** Where the card should say the place is. A tap is a fat finger with a 14 px hit box around it, so for a
 * point — a hospital, a pump, a station — the feature's own coordinates are the answer, and the card's grid
 * reference, distance and pinned position are the building's, not the finger's. A line or a polygon has no
 * one point to give, so there the tap itself is the best thing to measure from. */
export function placePoint(feature: MapGeoJSONFeature, tap: { lng: number; lat: number }): { lat: number; lon: number } {
  const geometry = feature.geometry;
  if (geometry?.type === 'Point') {
    const [lon, lat] = geometry.coordinates as [number, number];
    return { lat, lon };
  }
  return { lat: tap.lat, lon: tap.lng };
}

/** Everything the box knows about the thing under the pointer: the name, the type, the rows off its own
 * data, and — where the kind has guidance — what is usually there, when it is worth going, when to stay
 * away and how to go about it. A household hovering a hospital is looking for survival answers, not a
 * label, and the popup is the fastest way to read them; the card a tap opens says the same words with
 * the framing paragraph and the actions, for a finger that cannot hold still.
 *
 * The feature's own values are text nodes, so an OSM name is never parsed as HTML. The guidance is the
 * box's own rendered content and goes in as HTML; the popup takes no pointer events, so its links are
 * only ink and the guide is named as a line instead. */
export function renderDescription(d: FeatureDescription, guidance?: PlaceGuidance | null): HTMLElement {
  const root = document.createElement('div');
  root.className = 'map-tip';
  root.setAttribute('role', 'tooltip');
  const title = document.createElement('strong');
  title.className = 'map-tip-title';
  title.textContent = d.title;
  root.appendChild(title);
  // An unnamed place is titled by its type; saying it twice tells nobody anything.
  if (d.typeLine && d.typeLine !== d.title) {
    const type = document.createElement('div');
    type.className = 'map-tip-type';
    type.textContent = d.typeLine;
    root.appendChild(type);
  }
  // The type is already the line above the rows, exactly as on the card.
  const rows = d.rows.filter(([label]) => label !== 'Type');
  if (rows.length) {
    const list = document.createElement('dl');
    list.className = 'map-tip-rows';
    for (const [label, value] of rows) {
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
  if (guidance) {
    for (const part of guidance.sections) {
      const section = document.createElement('section');
      section.className = 'map-tip-section';
      const heading = document.createElement('h4');
      heading.textContent = part.title;
      section.appendChild(heading);
      section.insertAdjacentHTML('beforeend', part.html);
      root.appendChild(section);
    }
    const guide = document.createElement('div');
    guide.className = 'map-tip-guide';
    guide.textContent = `Guide: ${guidance.link.title}`;
    root.appendChild(guide);
  }
  return root;
}

/**
 * One popup for every overlay feature: it follows the pointer over points, lines and polygons and says
 * what the thing is and what it is worth to somebody surviving. A tap (or click) hands the place to
 * `onTap` — the screen opens the card — and takes the popup away; a tap on empty map hands `null`.
 * `guidance` is read on every show, because `GET /api/map/places` lands after the first hover can.
 * The popup is a DOM overlay and the handlers hang off the map, not the style, so both survive a base
 * switch through setStyle. Returns a detach function.
 */
export function attachFeatureTooltip(
  map: MlMap,
  overlays: () => Overlay[],
  onTap: (place: TappedPlace | null) => void,
  guidance: () => Record<string, PlaceGuidance> | null,
): () => void {
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, closeOnMove: false, focusAfterOpen: false, className: 'map-tip-popup', maxWidth: 'none', offset: 12 });
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
    const described = describeMapFeature(feature, overlays());
    const guide = described.kind ? guidance()?.[described.kind] ?? null : null;
    // The guidance is part of the key: it arrives from the API after the map does, and the first
    // feature hovered must pick it up rather than stay a bare label until the pointer moves on.
    const key = `${keyOf(feature)}:${guide ? 'guided' : 'plain'}`;
    if (key !== shownKey) {
      popup.setDOMContent(renderDescription(described, guide));
      shownKey = key;
    }
    popup.setLngLat([at.lng, at.lat]);
    if (!popup.isOpen()) popup.addTo(map);
  };
  const hide = () => {
    if (popup.isOpen()) popup.remove();
    shownKey = null;
  };

  const onMove = (e: PointerEventLike) => {
    const feature = featureAt(e.point, HOVER_PAD);
    setCursor(Boolean(feature));
    if (feature) show(feature, e.lngLat);
    else if (popup.isOpen()) hide();
  };
  const onLeave = () => {
    setCursor(false);
    hide();
  };
  const onClick = (e: PointerEventLike) => {
    const touch = e.originalEvent?.pointerType === 'touch';
    const feature = featureAt(e.point, touch ? TAP_PAD : HOVER_PAD);
    hide();
    if (!feature) { onTap(null); return; }
    const at = placePoint(feature, e.lngLat);
    onTap({ ...describeMapFeature(feature, overlays()), overlayId: overlayIdOf(feature), lat: at.lat, lon: at.lon });
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
