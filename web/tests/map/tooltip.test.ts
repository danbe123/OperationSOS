import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Map as MlMap, MapGeoJSONFeature } from 'maplibre-gl';
import { FakeMap, type FakeFeature } from './fakeMap';
import { attachFeatureTooltip, overlayLayerIds, pickFeature, renderDescription } from '../../src/map/tooltip';
import { mapConfig, mapPlaces } from '../fixtures/api';

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
/** The docked panel, if it is up: a child of the map container, never of the document body. */
const dock = (map: FakeMap) => map.getContainer().querySelector('.map-tip-dock');
const tip = (map: FakeMap, sel = '.map-tip') => map.getContainer().querySelector(sel);
const leaveCanvas = (map: FakeMap, to: Node | null = null) => map.getCanvas().dispatchEvent(new MouseEvent('mouseleave', { relatedTarget: to }));
const leaveDock = (map: FakeMap, to: Node | null = null) => dock(map)!.dispatchEvent(new MouseEvent('mouseleave', { relatedTarget: to }));

beforeEach(() => { document.body.innerHTML = ''; });

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
  it('renders the title, the type line and the rows as text, never HTML', () => {
    const el = renderDescription({ title: '<b>Bold</b>', overlay: 'Fuel stations', typeLine: 'Fuel station', kind: 'fuel', rows: [['Type', 'Fuel station'], ['Phone', '0123']] });
    expect(el.getAttribute('role')).toBe('tooltip');
    expect(el.querySelector('.map-tip-title')?.textContent).toBe('<b>Bold</b>');
    expect(el.querySelector('b')).toBeNull();
    expect(el.querySelector('.map-tip-type')?.textContent).toBe('Fuel station');
    const rows = [...el.querySelectorAll('.map-tip-rows > div')].map((r) => [r.querySelector('dt')?.textContent, r.querySelector('dd')?.textContent]);
    // The type is the line above the rows; repeating it as a row says nothing the reader has not read.
    expect(rows).toEqual([['Phone', '0123']]);
    // No guidance for the kind: the name, the type and the rows, and nothing invented under them.
    expect(el.querySelector('.map-tip-section')).toBeNull();
    expect(el.querySelector('.map-tip-guide')).toBeNull();
  });

  it('an unnamed place says its type once and carries no type line', () => {
    const unnamed = renderDescription({ title: 'Flood zone 3', overlay: 'Flood zones', typeLine: 'Flood zone 3', kind: 'flood-zone', rows: [] });
    expect(unnamed.querySelector('.map-tip-type')).toBeNull();
    expect(unnamed.textContent).toBe('Flood zone 3');
  });

  it('carries the four guidance sections, their bullets and the guide it came from', () => {
    const el = renderDescription(
      { title: 'Southampton General Hospital', overlay: 'Hospitals', typeLine: 'Hospital', kind: 'hospital', rows: [['Beds', '1200']] },
      mapPlaces.hospital,
    );
    expect([...el.querySelectorAll('.map-tip-section h4')].map((h) => h.textContent))
      .toEqual(['Usually here', 'Worth going when', 'Stay away when', 'How to go about it']);
    const bullets = [...el.querySelectorAll('.map-tip-section li')].map((li) => li.textContent);
    expect(bullets).toContain('Mains power on generators for a few days');
    expect(bullets).toContain('Take medicines and a written list');
    // The guidance is the box's own rendered HTML, so its markup is markup...
    expect(el.querySelector('.map-tip-section a')?.getAttribute('href')).toBe('/m/water');
    // ...while the feature's own values stay text, whatever OSM put in them.
    expect(el.querySelector('.map-tip-rows dd')?.textContent).toBe('1200');
    // The guide is named rather than linked: opening one is the card's business, not the hover's.
    expect(el.querySelector('.map-tip-guide')?.textContent).toBe('Guide: Medical');
  });
});

describe('attachFeatureTooltip', () => {
  it('docks a panel inside the map while hovering a feature, sets the pointer cursor, and takes it away when the pointer leaves', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => null);
    expect(dock(map)).toBeNull();
    map.renderedFeatures = [hospital];
    move(map);
    expect(map.queryRenderedFeatures).toHaveBeenLastCalledWith([[5, 5], [15, 15]], { layers: ['sos-overlay-health-point', 'sos-overlay-footpaths-footpaths-line'] });
    const panel = dock(map)!;
    // The panel is inside the map, not the page: it is bounded by the map's own edges.
    expect(panel.parentElement).toBe(map.getContainer());
    // The pointer is in the left half of a 1000 px map, so the reading goes on the right.
    expect(panel.className).toBe('map-tip-dock map-tip-dock-right');
    expect(map.getCanvas().style.cursor).toBe('pointer');
    expect(tip(map, '.map-tip-title')?.textContent).toBe('Southampton General Hospital');
    expect(tip(map, '.map-tip-type')?.textContent).toBe('Hospital');
    expect(tip(map, '.map-tip-rows dd')?.textContent).toBe('+44 23 8077 7222');
    // The same feature under a moved pointer is the same panel, in the same place: a panel that
    // re-docked on every mousemove would flicker from side to side as the pointer crossed the middle.
    move(map, 900, 11);
    expect(dock(map)).toBe(panel);
    expect(panel.className).toBe('map-tip-dock map-tip-dock-right');
    map.renderedFeatures = [];
    move(map, 200, 200);
    expect(dock(map)).toBeNull();
    expect(map.getCanvas().style.cursor).toBe('');
  });

  it('docks on the side of the map away from the pointer', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => null);
    map.renderedFeatures = [hospital];
    move(map, 900, 40);
    expect(dock(map)!.className).toBe('map-tip-dock map-tip-dock-left');
    // A different feature is a fresh reading, so the side is settled again off the pointer that found it.
    map.renderedFeatures = [path];
    move(map, 40, 40);
    expect(dock(map)!.className).toBe('map-tip-dock map-tip-dock-right');
  });

  it('stays while the pointer moves into it to read or scroll it, and goes when the pointer leaves both', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => null);
    map.renderedFeatures = [hospital];
    move(map);
    // Off the canvas and into the panel: the reader is reading, and the pointer cursor is done with.
    leaveCanvas(map, tip(map, '.map-tip-title'));
    expect(dock(map)).not.toBeNull();
    expect(map.getCanvas().style.cursor).toBe('');
    // Back out of the panel onto the map: the next mousemove decides, so the panel is left alone.
    leaveDock(map, map.getCanvas());
    expect(dock(map)).not.toBeNull();
    // Out of the panel and off the map altogether: nothing is being read.
    leaveDock(map, null);
    expect(dock(map)).toBeNull();
    // And leaving the canvas for anywhere but the panel takes it away too.
    move(map);
    expect(dock(map)).not.toBeNull();
    leaveCanvas(map, null);
    expect(dock(map)).toBeNull();
  });

  it('puts the guidance for the feature\'s kind in the panel, even when it arrives after the first hover', () => {
    const map = mapWithOverlays();
    // `GET /api/map/places` answers after the map is up: a hospital hovered in that gap is a label,
    // and the same hospital hovered again once the answer lands must carry the sections.
    let places: Record<string, typeof mapPlaces.hospital> | null = null;
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => places);
    map.renderedFeatures = [hospital];
    move(map);
    expect(tip(map, '.map-tip-section')).toBeNull();
    places = mapPlaces;
    move(map, 11, 11);
    expect([...map.getContainer().querySelectorAll('.map-tip-section h4')].map((h) => h.textContent))
      .toEqual(['Usually here', 'Worth going when', 'Stay away when', 'How to go about it']);
    expect(tip(map, '.map-tip-guide')?.textContent).toBe('Guide: Medical');
    // A kind the box has no guidance for stays the name, the type and the rows.
    map.renderedFeatures = [path];
    move(map, 12, 12);
    expect(tip(map, '.map-tip-section')).toBeNull();
  });

  it('describes lines and polygons from pmtiles overlays by their source layer', () => {
    const map = mapWithOverlays();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => null);
    map.renderedFeatures = [path];
    move(map);
    expect(tip(map, '.map-tip-title')?.textContent).toBe('Public footpath');
    map.setLayoutProperty('sos-overlay-flood-zones-flood_england-fill', 'visibility', 'visible');
    map.renderedFeatures = [zone, path];
    move(map, 12, 12);
    expect(tip(map, '.map-tip-title')?.textContent).toBe('Public footpath'); // the line wins over the polygon it crosses
    map.renderedFeatures = [zone];
    move(map, 14, 14);
    expect(tip(map, '.map-tip-title')?.textContent).toBe('Flood zone 3');
    expect(tip(map, '.map-tip-type')).toBeNull(); // unnamed: the type is already the title
  });

  it('a tap hands the place to onTap with a wider hit box and takes the panel away; a tap on empty map hands null', () => {
    const map = mapWithOverlays();
    const onTap = vi.fn();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, onTap, () => null);
    map.renderedFeatures = [hospital];
    move(map);
    expect(dock(map)).not.toBeNull();
    click(map, true);
    expect(map.queryRenderedFeatures).toHaveBeenLastCalledWith([[-4, -4], [24, 24]], expect.anything());
    // The panel goes: the card the tap opens says all of this, and more, where it can be read.
    expect(dock(map)).toBeNull();
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
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, onTap, () => null);
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

  it('detaching removes the handlers and the panel', () => {
    const map = mapWithOverlays();
    const detach = attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => null);
    map.renderedFeatures = [hospital];
    move(map);
    expect(dock(map)).not.toBeNull();
    detach();
    expect(dock(map)).toBeNull();
    map.queryRenderedFeatures.mockClear();
    move(map);
    expect(map.queryRenderedFeatures).not.toHaveBeenCalled();
  });

  it('does nothing when no overlay layer is on', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => null);
    map.renderedFeatures = [hospital];
    move(map);
    expect(map.queryRenderedFeatures).not.toHaveBeenCalled();
    expect(dock(map)).toBeNull();
  });
});

describe('guide links in the docked panel', () => {
  it('sends an in-app href through onNavigate and leaves other links alone', () => {
    const map = mapWithOverlays();
    const guidance = { hospital: { ...mapPlaces.hospital, sections: [{ id: 'have', title: 'Usually here', html: '<ul><li><a href="/m/water">Water</a> and <a href="https://example.org">site</a></li></ul>' }] } };
    const onNavigate = vi.fn();
    attachFeatureTooltip(asMap(map), () => mapConfig.overlays, vi.fn(), () => guidance as never, onNavigate);
    map.renderedFeatures = [hospital];
    move(map);
    const inApp = map.getContainer().querySelector('a[href="/m/water"]') as HTMLAnchorElement;
    const inAppEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
    inApp.dispatchEvent(inAppEvent);
    expect(onNavigate).toHaveBeenCalledWith('/m/water');
    expect(inAppEvent.defaultPrevented).toBe(true);
    const external = map.getContainer().querySelector('a[href="https://example.org"]') as HTMLAnchorElement;
    const externalEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
    external.dispatchEvent(externalEvent);
    expect(onNavigate).toHaveBeenCalledTimes(1);
    expect(externalEvent.defaultPrevented).toBe(false);
  });
});
