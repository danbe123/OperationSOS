import { describe, it, expect, vi } from 'vitest';
import type { Map as MlMap } from 'maplibre-gl';
import { FakeMap } from './fakeMap';
import { coverageNote, overlaySpec, overlayLayersFor, addOverlay, setOverlayVisible, overlaySourceId } from '../../src/map/overlays';
import { mapConfig } from '../fixtures/api';

vi.mock('maplibre-gl', () => ({ default: { addProtocol: vi.fn() }, addProtocol: vi.fn() }));
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class extends Error {} }));

const asMap = (m: FakeMap) => m as unknown as MlMap;
const [health, footpaths, accessLand, , contourLabels] = mapConfig.overlays;

describe('coverageNote', () => {
  it('lists the regions an overlay lacks', () => {
    expect(coverageNote(health)).toBeNull();
    expect(coverageNote(accessLand)).toBe('No data for Scotland, Northern Ireland, Republic of Ireland, Isle of Man, Channel Islands');
  });
});

describe('overlaySpec and layers', () => {
  it('geojson overlays get a data source and a fill/line/point trio in the overlay colour', () => {
    const spec = overlaySpec(health);
    expect(spec.source).toEqual({ type: 'geojson', data: '/maps/overlays/health.geojson' });
    expect(overlayLayersFor(health, null).map((l) => l.id)).toEqual(['sos-overlay-health-fill', 'sos-overlay-health-line', 'sos-overlay-health-point']);
    expect((overlayLayersFor(health, null)[2] as { paint: { 'circle-color': string } }).paint['circle-color']).toBe('#e53935');
  });
  it('pmtiles overlays get one trio per vector layer', () => {
    expect(overlaySpec(footpaths).source).toEqual({ type: 'vector', url: `pmtiles://${window.location.origin}/maps/overlays/footpaths.pmtiles` });
    const layers = overlayLayersFor(footpaths, ['prow', 'other']);
    expect(layers.map((l) => l.id)).toEqual(['sos-overlay-footpaths-prow-fill', 'sos-overlay-footpaths-prow-line', 'sos-overlay-footpaths-prow-point', 'sos-overlay-footpaths-other-fill', 'sos-overlay-footpaths-other-line', 'sos-overlay-footpaths-other-point']);
    expect((layers[0] as { 'source-layer': string })['source-layer']).toBe('prow');
  });
  it('style-layer overlays have no source of their own', () => {
    expect(overlaySpec(contourLabels)).toEqual({ source: null, layers: [] });
  });
});

describe('addOverlay and setOverlayVisible', () => {
  it('adds a geojson overlay hidden or visible and toggles it', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    addOverlay(asMap(map), health, false);
    expect(map.getLayer('sos-overlay-health-point')).toBeDefined();
    expect(map.visibility('sos-overlay-health-point')).toBe('none');
    setOverlayVisible(asMap(map), health, true);
    expect(map.visibility('sos-overlay-health-fill')).toBe('visible');
    expect(map.visibility('sos-overlay-health-point')).toBe('visible');
  });
  it('waits for a pmtiles source to report its vector layers', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    addOverlay(asMap(map), footpaths, true);
    expect(map.style.sources[overlaySourceId('footpaths')]).toBeDefined();
    expect(map.getLayer('sos-overlay-footpaths-footpaths-line')).toBeUndefined();
    map.vectorLayers[overlaySourceId('footpaths')] = ['footpaths'];
    map.emit('sourcedata', { sourceId: overlaySourceId('footpaths'), isSourceLoaded: true });
    expect(map.visibility('sos-overlay-footpaths-footpaths-line')).toBe('visible');
  });
  it('toggles a style-layer overlay by its layer_id', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    map.addLayer({ id: 'contour_label', type: 'symbol', source: 'base' });
    addOverlay(asMap(map), contourLabels, false);
    expect(map.visibility('contour_label')).toBe('none');
    setOverlayVisible(asMap(map), contourLabels, true);
    expect(map.visibility('contour_label')).toBe('visible');
  });
  it('uses the latest toggle when vector metadata arrives later', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    addOverlay(asMap(map), footpaths, false);
    setOverlayVisible(asMap(map), footpaths, true);
    map.vectorLayers[overlaySourceId('footpaths')] = ['footpaths'];
    map.emit('sourcedata', { sourceId: overlaySourceId('footpaths'), isSourceLoaded: true });
    expect(map.visibility('sos-overlay-footpaths-footpaths-line')).toBe('visible');
  });
});
