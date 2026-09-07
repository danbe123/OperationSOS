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
  it('renders title, overlay and rows as text, never HTML', () => {
    const el = renderDescription({ title: '<b>Bold</b>', overlay: 'Fuel stations', typeLine: 'Fuel stations', kind: null, rows: [['Phone', '0123']] });
    expect(el.getAttribute('role')).toBe('tooltip');
    expect(el.querySelector('.map-tip-title')?.textContent).toBe('<b>Bold</b>');
    expect(el.querySelector('b')).toBeNull();
    expect(el.querySelector('.map-tip-overlay')?.textContent).toBe('Fuel stations');
    expect([...el.querySelectorAll('dt, dd')].map((n) => n.textContent)).toEqual(['Phone', '0123']);
    expect(renderDescription({ title: 'x', overlay: 'y', typeLine: 'y', kind: null, rows: [] }).querySelector('dl')).toBeNull();
  });
});

describe('attachFeatureTooltip', () => {
  it('opens one popup while hovering a feature, sets the pointer cursor, and closes it when the pointer leaves', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays);
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
    expect(tip.querySelector('.map-tip-overlay')?.textContent).toBe('Hospitals, pharmacies, GP surgeries');
    expect([...tip.querySelectorAll('dd')].map((n) => n.textContent)).toEqual(['Hospital', '+44 23 8077 7222']);
    move(map, 11, 11);
    expect(FakePopup.instances).toHaveLength(1);
    map.renderedFeatures = [];
    move(map, 200, 200);
    expect(popup().isOpen()).toBe(false);
    expect(map.getCanvas().style.cursor).toBe('');
  });

  it('describes lines and polygons from pmtiles overlays by their source layer', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays);
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
    expect([...document.querySelectorAll('.map-tip dd')].map((n) => n.textContent)).toContain('England');
  });

  it('a tap pins the popup with a wider hit box; a tap on empty map closes it', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays);
    map.renderedFeatures = [hospital];
    click(map, true);
    expect(map.queryRenderedFeatures).toHaveBeenLastCalledWith([[-4, -4], [24, 24]], expect.anything());
    expect(popup().isOpen()).toBe(true);
    map.renderedFeatures = [];
    move(map, 300, 300);
    map.getCanvas().dispatchEvent(new Event('mouseleave'));
    expect(popup().isOpen()).toBe(true);
    click(map);
    expect(popup().isOpen()).toBe(false);
  });

  it('detaching removes the handlers and the popup', () => {
    const map = mapWithOverlays();
    const detach = attachFeatureTooltip(asMap(map), () => mapConfig.overlays);
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
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays);
    map.renderedFeatures = [hospital];
    move(map);
    expect(map.queryRenderedFeatures).not.toHaveBeenCalled();
    expect(popup().isOpen()).toBe(false);
  });
});
