import { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl, { type Map as MlMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { MapConfig, Note } from '../api/types';
import type { Theme } from '../theme/ThemeProvider';
import { addTerrain, carryStyleAcross, isEtagMismatch, recreateSource, registerPmtilesProtocol, setTerrainVisible } from './layers';
import { addOverlay, setOverlayVisible } from './overlays';
import { attachFeatureTooltip } from './tooltip';
import type { LngLat } from './measure';

// e2e exposure: window.__sosMap is the live map instance; __styleVersion is bumped on every
// completed style load (base switches included) so tests can observe a reload without relying on
// a diffed-out setStyle (see the setStyle call below).
type ExposedMap = MlMap & { __styleVersion?: number };

export type MapViewProps = {
  config: MapConfig;
  theme: Theme;
  baseId: 'osm' | 'os';
  overlaysOn: string[];
  terrainOn: boolean;
  center: [number, number];
  zoom: number;
  pins: Note[];
  labelPoint: { lat: number; lon: number; label: string } | null;
  measurePoints: LngLat[];
  onMoveEnd: (view: { lon: number; lat: number; zoom: number }) => void;
  onClick: (p: LngLat) => void;
  onLongPress: (p: LngLat) => void;
  onReady: (map: MlMap) => void;
};

const LONG_PRESS_MS = 600;

function syncPins(map: MlMap, pins: Note[], labelPoint: MapViewProps['labelPoint']): void {
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
  if (!map.getLayer('sos-pins-point')) {
    map.addLayer({ id: 'sos-pins-point', type: 'circle', source: 'sos-pins', paint: { 'circle-radius': 8, 'circle-color': ['match', ['get', 'kind'], 'label', '#1e88e5', '#ffb000'], 'circle-stroke-color': '#000000', 'circle-stroke-width': 2 } });
  }
  if (!map.getLayer('sos-pins-label') && map.getStyle().glyphs) {
    map.addLayer({ id: 'sos-pins-label', type: 'symbol', source: 'sos-pins', layout: { 'text-field': ['get', 'title'], 'text-font': ['Noto Sans Regular'], 'text-size': 13, 'text-offset': [0, 1.2], 'text-anchor': 'top' }, paint: { 'text-halo-color': '#ffffff', 'text-halo-width': 1.5 } });
  }
}

function syncMeasure(map: MlMap, points: LngLat[]): void {
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
  if (!map.getLayer('sos-measure-line')) map.addLayer({ id: 'sos-measure-line', type: 'line', source: 'sos-measure', paint: { 'line-color': '#ff3d00', 'line-width': 3, 'line-dasharray': [2, 1] } });
  if (!map.getLayer('sos-measure-point')) map.addLayer({ id: 'sos-measure-point', type: 'circle', source: 'sos-measure', paint: { 'circle-radius': 5, 'circle-color': '#ff3d00' } });
}

export function MapView(props: MapViewProps) {
  const { config, theme, baseId, overlaysOn, terrainOn, pins, labelPoint, measurePoints } = props;
  const hostRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const [styleVersion, setStyleVersion] = useState(0);
  const currentStyle = useRef<string | null>(null);

  const styleUrl = useMemo(() => {
    const base = config.bases.find((b) => b.id === baseId && b.available) ?? config.bases.find((b) => b.available);
    return base?.styles[theme] ?? null;
  }, [config, baseId, theme]);
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
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
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
    const detachTooltip = attachFeatureTooltip(map, () => propsRef.current.config.overlays);
    mapRef.current = map;
    (window as unknown as { __sosMap?: ExposedMap }).__sosMap = map as ExposedMap;
    propsRef.current.onReady(map);
    return () => {
      detachTooltip();
      map.remove();
      mapRef.current = null;
    };
    // The map is created once; base and theme changes go through setStyle below.
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
    setTerrainVisible(map, terrainOn);
    for (const o of config.overlays) {
      if (!o.available) continue;
      addOverlay(map, o, overlaysOn.includes(o.id));
      setOverlayVisible(map, o, overlaysOn.includes(o.id));
    }
    syncPins(map, pins, labelPoint);
    syncMeasure(map, measurePoints);
  }, [styleVersion, config, theme, overlaysOn, terrainOn, pins, labelPoint, measurePoints]);

  if (!hasStyle) return <p className="pad warning">No base map is installed. Run the map build on the PC and copy the outputs to the box.</p>;
  return <div ref={hostRef} className="map-canvas" data-testid="map-canvas" />;
}
