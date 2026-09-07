import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Map as MlMap, MapGeoJSONFeature } from 'maplibre-gl';
import { FakeMap, FakePopup, type FakeFeature } from './fakeMap';
import { attachFeatureTooltip, overlayLayerIds, pickFeature, renderDescription } from '../../src/map/tooltip';
import { mapConfig } from '../fixtures/api';

vi.mock('maplibre-gl', async () => {
  const { FakePopup } = await import('./fakeMap');
  const stub = { Popup: FakePopup, addProtocol: vi.fn() };
  return { default: stub, ...stub };
});
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class extends Error {} }));

const asMap = (m: FakeMap) => m as unknown as MlMap;
const hospital: FakeFeature = { id: 1, source: 'sos-overlay-health', layer: { id: 'sos-overlay-health-point' }, properties: { name: 'Southampton General Hospital', amenity: 'hospital', phone: '+44 23 8077 7222' } };
const zone: FakeFeature = { id: 7, source: 'sos-overlay-flood-zones', sourceLayer: 'flood_england', layer: { id: 'sos-overlay-flood-zones-flood_england-fill' }, properties: { zone: '3' } };
const path: FakeFeature = { id: 3, source: 'sos-overlay-footpaths', sourceLayer: 'footpaths', layer: { id: 'sos-overlay-footpaths-footpaths-line' }, properties: { designation: 'public_footpath', highway: 'path' } };
const hospitalAt: FakeFeature = { ...hospital, geometry: { type: 'Point', coordinates: [-1.4353, 50.9333] } };
const zoneAt: FakeFeature = { ...zone, geometry: { type: 'Polygon', coordinates: [[[-1.44, 50.93], [-1.43, 50.93], [-1.43, 50.94], [-1.44, 50.93]]] } };

function mapWithOverlays(): FakeMap {
  const map = new FakeMap();
  map.setStyle('/maps/styles/osm-field.json');
  map.addLayer({ id: 'sos-overlay-health-point', type: 'circle', source: 'sos-overlay-health' });
  map.addLayer({ id: 'sos-overlay-flood-zones-flood_england-fill', type: 'fill', source: 'sos-overlay-flood-zones', layout: { visibility: 'none' } });
  map.addLayer({ id: 'sos-overlay-footpaths-footpaths-line', type: 'line', source: 'sos-overlay-footpaths' });
  map.addLayer({ id: 'sos-pins-point', type: 'circle', source: 'sos-pins' });
  return map;
}
const move = (map: FakeMap, x = 10, y = 10) => map.emit('mousemove', { point: { x, y }, lngLat: { lng: -1.43, lat: 50.93 }, originalEvent: {} });
const click = (map: FakeMap, touch = false) => map.emit('click', { point: { x: 10, y: 10 }, lngLat: { lng: -1.43, lat: 50.93 }, originalEvent: touch ? { pointerType: 'touch' } : {} });
const popup = () => FakePopup.instances[FakePopup.instances.length - 1];

beforeEach(() => { FakePopup.instances.length = 0; document.body.innerHTML = ''; });

describe('overlayLayerIds and pickFeature', () => {
  it('lists only visible sos-overlay layers', () => {
    expect(overlayLayerIds(asMap(mapWithOverlays()))).toEqual(['sos-overlay-health-point', 'sos-overlay-footpaths-footpaths-line']);
  });
  it('prefers a point over a line over a polygon', () => {
    const f = (id: string) => ({ layer: { id } }) as MapGeoJSONFeature;
    expect(pickFeature([f('a-fill'), f('b-line'), f('c-point')])?.layer.id).toBe('c-point');
    expect(pickFeature([f('a-fill'), f('b-line')])?.layer.id).toBe('b-line');
    expect(pickFeature([])).toBeUndefined();
  });
});

describe('renderDescription', () => {
  it('renders the title and the type line as text, never HTML, and no rows', () => {
    const el = renderDescription({ title: '<b>Bold</b>', overlay: 'Fuel stations', typeLine: 'Fuel station', kind: 'fuel', rows: [['Phone', '0123']] });
    expect(el.getAttribute('role')).toBe('tooltip');
    expect(el.querySelector('.map-tip-title')?.textContent).toBe('<b>Bold</b>');
    expect(el.querySelector('b')).toBeNull();
    expect(el.querySelector('.map-tip-type')?.textContent).toBe('Fuel station');
    const unnamed = renderDescription({ title: 'Flood zone 3', overlay: 'Flood zones', typeLine: 'Flood zone 3', kind: 'flood-zone', rows: [] });
    expect(unnamed.querySelector('.map-tip-type')).toBeNull();
    expect(unnamed.textContent).toBe('Flood zone 3');
    // The rows moved to the card a tap opens: a popup that follows the pointer is not the place to read a list.
    expect(el.querySelector('dl')).toBeNull();
    expect(el.textContent).not.toContain('0123');
  });
});

describe('attachFeatureTooltip', () => {
  it('opens one popup while hovering a feature, sets the pointer cursor, and closes it when the pointer leaves', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn());
    expect(FakePopup.instances).toHaveLength(1);
    expect(popup().options).toMatchObject({ closeButton: false, closeOnClick: false, className: 'map-tip-popup' });
    map.renderedFeatures = [hospital];
    move(map);
    expect(map.queryRenderedFeatures).toHaveBeenLastCalledWith([[5, 5], [15, 15]], { layers: ['sos-overlay-health-point', 'sos-overlay-footpaths-footpaths-line'] });
    expect(popup().isOpen()).toBe(true);
    expect(popup().lngLat).toEqual([-1.43, 50.93]);
    expect(map.getCanvas().style.cursor).toBe('pointer');
    const tip = document.querySelector('.map-tip')!;
    expect(tip.querySelector('.map-tip-title')?.textContent).toBe('Southampton General Hospital');
    expect(tip.querySelector('.map-tip-type')?.textContent).toBe('Hospital');
    expect(tip.querySelector('dl')).toBeNull();
    move(map, 11, 11);
    expect(FakePopup.instances).toHaveLength(1);
    map.renderedFeatures = [];
    move(map, 200, 200);
    expect(popup().isOpen()).toBe(false);
    expect(map.getCanvas().style.cursor).toBe('');
  });

  it('describes lines and polygons from pmtiles overlays by their source layer', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn());
    map.renderedFeatures = [path];
    move(map);
    expect(document.querySelector('.map-tip-title')?.textContent).toBe('Public footpath');
    map.setLayoutProperty('sos-overlay-flood-zones-flood_england-fill', 'visibility', 'visible');
    map.renderedFeatures = [zone, path];
    move(map, 12, 12);
    expect(document.querySelector('.map-tip-title')?.textContent).toBe('Public footpath'); // the line wins over the polygon it crosses
    map.renderedFeatures = [zone];
    move(map, 14, 14);
    expect(document.querySelector('.map-tip-title')?.textContent).toBe('Flood zone 3');
    expect(document.querySelector('.map-tip-type')?.textContent).toBe('Flood zone 3');
  });

  it('a tap hands the place to onTap with a wider hit box and closes the popup; a tap on empty map hands null', () => {
    const map = mapWithOverlays();
    const onTap = vi.fn();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, onTap);
    map.renderedFeatures = [hospital];
    move(map);
    expect(popup().isOpen()).toBe(true);
    click(map, true);
    expect(map.queryRenderedFeatures).toHaveBeenLastCalledWith([[-4, -4], [24, 24]], expect.anything());
    // The popup goes: the card the tap opens says all of this, and more, where it can be read.
    expect(popup().isOpen()).toBe(false);
    expect(onTap).toHaveBeenCalledWith({
      title: 'Southampton General Hospital', overlay: 'Hospitals, pharmacies, GP surgeries', typeLine: 'Hospital',
      kind: 'hospital', rows: [['Type', 'Hospital'], ['Phone', '+44 23 8077 7222']],
      overlayId: 'health', lat: 50.93, lon: -1.43,
    });
    map.renderedFeatures = [];
    click(map);
    expect(onTap).toHaveBeenLastCalledWith(null);
  });

  it('a tapped point is the feature\'s own position, not the finger\'s; a polygon has only the tap', () => {
    const map = mapWithOverlays();
    const onTap = vi.fn();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, onTap);
    // The tap lands 400 m off the hospital: within the 14 px box, but the card must say where the
    // hospital is, because its grid reference, its distance and the pin it drops all come off this point.
    map.renderedFeatures = [hospitalAt];
    map.emit('click', { point: { x: 10, y: 10 }, lngLat: { lng: -1.4300, lat: 50.9300 }, originalEvent: { pointerType: 'touch' } });
    expect(onTap).toHaveBeenLastCalledWith(expect.objectContaining({ lat: 50.9333, lon: -1.4353 }));
    // A flood zone has no one point to give, so the tap is the only place worth measuring from.
    map.setLayoutProperty('sos-overlay-flood-zones-flood_england-fill', 'visibility', 'visible');
    map.renderedFeatures = [zoneAt];
    map.emit('click', { point: { x: 10, y: 10 }, lngLat: { lng: -1.4300, lat: 50.9300 }, originalEvent: { pointerType: 'touch' } });
    expect(onTap).toHaveBeenLastCalledWith(expect.objectContaining({ title: 'Flood zone 3', lat: 50.9300, lon: -1.4300 }));
  });

  it('detaching removes the handlers and the popup', () => {
    const map = mapWithOverlays();
    const detach = attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn());
    map.renderedFeatures = [hospital];
    move(map);
    expect(popup().isOpen()).toBe(true);
    detach();
    expect(popup().isOpen()).toBe(false);
    map.queryRenderedFeatures.mockClear();
    move(map);
    expect(map.queryRenderedFeatures).not.toHaveBeenCalled();
  });

  it('does nothing when no overlay layer is on', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn());
    map.renderedFeatures = [hospital];
    move(map);
    expect(map.queryRenderedFeatures).not.toHaveBeenCalled();
    expect(popup().isOpen()).toBe(false);
  });
});
