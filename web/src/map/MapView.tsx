import { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl, { type LayerSpecification, type Map as MlMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { MapConfig, Note, PlaceGuidance } from '../api/types';
import type { Terrain } from './LayerChips';
import type { Theme } from '../theme/ThemeProvider';
import { addTerrain, annotationPaint, carryStyleAcross, isEtagMismatch, recreateSource, registerPmtilesProtocol, setTerrainLayerVisible } from './layers';
import { addOverlay, setOverlayVisible } from './overlays';
import { attachFeatureTooltip, type TappedPlace } from './tooltip';
import type { LngLat } from './measure';

// e2e exposure: window.__sosMap is the live map instance; __styleVersion is bumped on every
// completed style load so tests can observe a reload without relying on
// a diffed-out setStyle (see the setStyle call below).
type ExposedMap = MlMap & { __styleVersion?: number };

export type MapViewProps = {
  config: MapConfig;
  overlaysOn: string[];
  /** Contours and hillshade are two chips, and two answers: either can be on without the other. */
  terrain: Terrain;
  center: [number, number];
  zoom: number;
  pins: Note[];
  labelPoint: { lat: number; lon: number; label: string } | null;
  measurePoints: LngLat[];
  /** Where the household lives: its own marker, so it is never mistaken for a pin. */
  home: { lat: number; lon: number; label: string } | null;
  /** Two points: the straight line drawn to a facility, with its bearing shown in the readout. */
  routePoints: LngLat[];
  onMoveEnd: (view: { lon: number; lat: number; zoom: number }) => void;
  onClick: (p: LngLat) => void;
  /** What to expect at each kind of place, keyed by `PlaceKind`: the hover tooltip reads the feature's
   * kind out of it. `null` until `GET /api/map/places` answers, and the tooltip then picks it up. */
  guidance: Record<string, PlaceGuidance> | null;
  /** A tap on an overlay feature, described; `null` when the tap landed on empty map. */
  onFeatureTap: (place: TappedPlace | null) => void;
  /** A guide link inside the hover panel, sent through the app's router. */
  onNavigate: (href: string) => void;
  onLongPress: (p: LngLat) => void;
  onReady: (map: MlMap) => void;
};

const LONG_PRESS_MS = 600;

/** Add a layer the box draws, or — when it is already there, carried across a style reload —
 * repaint it in the colours it should be wearing. */
function drawn(map: MlMap, theme: Theme, spec: { id: string; type: 'circle' | 'line' | 'symbol'; source: string; layout?: Record<string, unknown> }): void {
  const props = annotationPaint(theme)[spec.id] ?? {};
  if (!map.getLayer(spec.id)) map.addLayer({ ...spec, paint: props } as LayerSpecification);
  for (const [key, value] of Object.entries(props)) map.setPaintProperty(spec.id, key, value);
}

function syncPins(map: MlMap, pins: Note[], labelPoint: MapViewProps['labelPoint'], theme: Theme): void {
  const features = [
    ...pins.filter((p) => p.lat !== null && p.lon !== null).map((p) => ({ type: 'Feature' as const, properties: { title: p.title, kind: 'pin' }, geometry: { type: 'Point' as const, coordinates: [p.lon as number, p.lat as number] } })),
    ...(labelPoint ? [{ type: 'Feature' as const, properties: { title: labelPoint.label, kind: 'label' }, geometry: { type: 'Point' as const, coordinates: [labelPoint.lon, labelPoint.lat] } }] : []),
  ];
  const data = { type: 'FeatureCollection' as const, features };
  const existing = map.getSource('sos-pins') as { setData?: (d: unknown) => void } | undefined;
  if (existing?.setData) {
    existing.setData(data);
  } else {
    map.addSource('sos-pins', { type: 'geojson', data });
  }
  drawn(map, theme, { id: 'sos-pins-point', type: 'circle', source: 'sos-pins' });
  if (map.getLayer('sos-pins-label') || map.getStyle().glyphs) {
    drawn(map, theme, { id: 'sos-pins-label', type: 'symbol', source: 'sos-pins', layout: { 'text-field': ['get', 'title'], 'text-font': ['Noto Sans Regular'], 'text-size': 13, 'text-offset': [0, 1.2], 'text-anchor': 'top' } });
  }
}

function syncHome(map: MlMap, home: MapViewProps['home'], theme: Theme): void {
  const data = {
    type: 'FeatureCollection' as const,
    features: home ? [{ type: 'Feature' as const, properties: { title: `\u2302 ${home.label}` }, geometry: { type: 'Point' as const, coordinates: [home.lon, home.lat] } }] : [],
  };
  const existing = map.getSource('sos-home') as { setData?: (d: unknown) => void } | undefined;
  if (existing?.setData) existing.setData(data);
  else map.addSource('sos-home', { type: 'geojson', data });
  drawn(map, theme, { id: 'sos-home-point', type: 'circle', source: 'sos-home' });
  if (map.getLayer('sos-home-label') || map.getStyle().glyphs) {
    drawn(map, theme, { id: 'sos-home-label', type: 'symbol', source: 'sos-home', layout: { 'text-field': ['get', 'title'], 'text-font': ['Noto Sans Regular'], 'text-size': 14, 'text-offset': [0, 1.4], 'text-anchor': 'top' } });
  }
}

function syncRoute(map: MlMap, points: LngLat[], theme: Theme): void {
  const coords = points.map((p) => [p.lon, p.lat]);
  const data = {
    type: 'FeatureCollection' as const,
    features: coords.length >= 2 ? [{ type: 'Feature' as const, properties: {}, geometry: { type: 'LineString' as const, coordinates: coords } }] : [],
  };
  const existing = map.getSource('sos-route') as { setData?: (d: unknown) => void } | undefined;
  if (existing?.setData) existing.setData(data);
  else map.addSource('sos-route', { type: 'geojson', data });
  drawn(map, theme, { id: 'sos-route-line', type: 'line', source: 'sos-route' });
}

function syncMeasure(map: MlMap, points: LngLat[], theme: Theme): void {
  const coords = points.map((p) => [p.lon, p.lat]);
  const data = {
    type: 'FeatureCollection' as const,
    features: [
      ...(coords.length >= 2 ? [{ type: 'Feature' as const, properties: {}, geometry: { type: 'LineString' as const, coordinates: coords } }] : []),
      ...coords.map((c) => ({ type: 'Feature' as const, properties: {}, geometry: { type: 'Point' as const, coordinates: c } })),
    ],
  };
  const existing = map.getSource('sos-measure') as { setData?: (d: unknown) => void } | undefined;
  if (existing?.setData) existing.setData(data);
  else map.addSource('sos-measure', { type: 'geojson', data });
  drawn(map, theme, { id: 'sos-measure-line', type: 'line', source: 'sos-measure' });
  drawn(map, theme, { id: 'sos-measure-point', type: 'circle', source: 'sos-measure' });
}

const MAP_THEME: Theme = 'field';

export function MapView(props: MapViewProps) {
  const { config, overlaysOn, terrain, pins, labelPoint, measurePoints, home, routePoints } = props;
  // The map is drawn as the paper it is: the black-and-white theme darkens everything around the
  // map, not the map, because an inverted OpenStreetMap sheet is one more thing to learn to read
  // when the lights are out. Every colour the box draws on it is the daylight set for the same reason.
  const theme: Theme = MAP_THEME;
  const hostRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const [styleVersion, setStyleVersion] = useState(0);
  const currentStyle = useRef<string | null>(null);

  const styleUrl = useMemo(() => {
    // One base map, and it is OpenStreetMap: a household choosing between two renderings of the
    // same ground is a choice that only ever cost it a tap. Anything else the box has is a fallback.
    const base = config.bases.find((b) => b.id === 'osm' && b.available) ?? config.bases.find((b) => b.available);
    return base?.styles[theme] ?? null;
  }, [config, theme]);
  const hasStyle = styleUrl !== null;

  useEffect(() => {
    if (!hostRef.current || !hasStyle || !styleUrl) return;
    registerPmtilesProtocol();
    currentStyle.current = styleUrl;
    const map = new maplibregl.Map({
      container: hostRef.current,
      style: styleUrl,
      center: propsRef.current.center,
      zoom: propsRef.current.zoom,
      maxZoom: 18,
      attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true }, // needed for the print snapshot
    });
    // MapLibre's own navigation control is three wordless icons whose compass announces itself as an
    // instruction ("Drag to rotate map, click to reset north"). Every other control in the box is an
    // icon and a word, so the map draws its own (`screens/Map.tsx`) and the vendor's stays off. The
    // scale bar has no buttons and no words to miss, so it stays.
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');
    map.on('style.load', () => {
      const exposed = map as ExposedMap;
      exposed.__styleVersion = (exposed.__styleVersion ?? 0) + 1;
      setStyleVersion((v) => v + 1);
    });
    map.on('moveend', () => {
      const c = map.getCenter();
      propsRef.current.onMoveEnd({ lon: c.lng, lat: c.lat, zoom: map.getZoom() });
    });
    map.on('click', (e) => propsRef.current.onClick({ lon: e.lngLat.lng, lat: e.lngLat.lat }));
    let timer: number | undefined;
    const down = (e: { lngLat: { lng: number; lat: number } }) => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => propsRef.current.onLongPress({ lon: e.lngLat.lng, lat: e.lngLat.lat }), LONG_PRESS_MS);
    };
    const cancel = () => window.clearTimeout(timer);
    map.on('mousedown', down);
    map.on('touchstart', down);
    map.on('mouseup', cancel);
    map.on('touchend', cancel);
    map.on('move', cancel);
    map.on('error', (e) => {
      const ev = e as { error?: unknown; sourceId?: string };
      if (ev.sourceId && isEtagMismatch(ev.error)) recreateSource(map, ev.sourceId);
    });
    const detachTooltip = attachFeatureTooltip(map, () => propsRef.current.config.overlays, (p) => propsRef.current.onFeatureTap(p), () => propsRef.current.guidance, (href) => propsRef.current.onNavigate(href));
    mapRef.current = map;
    (window as unknown as { __sosMap?: ExposedMap }).__sosMap = map as ExposedMap;
    propsRef.current.onReady(map);
    return () => {
      detachTooltip();
      map.remove();
      mapRef.current = null;
    };
    // The map is created once; a style change goes through setStyle below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasStyle]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleUrl || currentStyle.current === styleUrl) return;
    currentStyle.current = styleUrl;
    map.setStyle(styleUrl, { transformStyle: carryStyleAcross });
  }, [styleUrl]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || styleVersion === 0) return;
    addTerrain(map, config, theme);
    setTerrainLayerVisible(map, 'sos-contours', terrain.contours);
    setTerrainLayerVisible(map, 'sos-hillshade', terrain.hillshade);
    for (const o of config.overlays) {
      if (!o.available) continue;
      addOverlay(map, o, overlaysOn.includes(o.id), theme);
      setOverlayVisible(map, o, overlaysOn.includes(o.id));
    }
    syncPins(map, pins, labelPoint, theme);
    syncMeasure(map, measurePoints, theme);
    syncHome(map, home, theme);
    syncRoute(map, routePoints, theme);
  }, [styleVersion, config, theme, overlaysOn, terrain, pins, labelPoint, measurePoints, home, routePoints]);

  if (!hasStyle) return <p className="map-note warning">No base map is installed. Run the map build on the PC and copy the outputs to the box.</p>;
  return <div ref={hostRef} className="map-canvas" data-testid="map-canvas" />;
}
