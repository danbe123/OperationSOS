import { describe, it, expect, vi } from 'vitest';
import type { Map as MlMap } from 'maplibre-gl';
import { FakeMap } from './fakeMap';
import { carryStyleAcross, terrainSpec, addTerrain, setTerrainVisible, recreateSource, isEtagMismatch, pmtilesUrl } from '../../src/map/layers';
import { mapConfig } from '../fixtures/api';

vi.mock('maplibre-gl', () => ({ default: { addProtocol: vi.fn() }, addProtocol: vi.fn() }));
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class EtagMismatch extends Error { constructor() { super('etag'); this.name = 'EtagMismatch'; } } }));

const asMap = (m: FakeMap) => m as unknown as MlMap;

describe('pmtilesUrl', () => {
  it('produces an absolute pmtiles:// URL', () => {
    expect(pmtilesUrl('/maps/uk-ie.pmtiles')).toBe(`pmtiles://${window.location.origin}/maps/uk-ie.pmtiles`);
  });
});

describe('carryStyleAcross', () => {
  it('keeps sos- sources and layers, placing terrain before the first symbol layer and overlays at the end', () => {
    const prev = { version: 8 as const, sources: { base: { type: 'vector' }, 'sos-hillshade': { type: 'raster' }, 'sos-overlay-health': { type: 'geojson' } }, layers: [{ id: 'old', type: 'fill' }, { id: 'sos-hillshade', type: 'raster' }, { id: 'sos-overlay-health-point', type: 'circle' }] };
    const next = { version: 8 as const, sources: { base2: { type: 'vector' } }, layers: [{ id: 'land', type: 'fill' }, { id: 'labels', type: 'symbol' }] };
    const out = carryStyleAcross(prev as never, next as never) as typeof prev;
    expect(Object.keys(out.sources)).toEqual(['base2', 'sos-hillshade', 'sos-overlay-health']);
    expect(out.layers.map((l) => l.id)).toEqual(['land', 'sos-hillshade', 'labels', 'sos-overlay-health-point']);
  });
});

describe('terrain', () => {
  it('builds hillshade and contour sources from the config and adds them below labels', () => {
    const spec = terrainSpec(mapConfig, 'vault');
    expect(Object.keys(spec.sources)).toEqual(['sos-hillshade', 'sos-contours']);
    expect(spec.layers.map((l) => l.id)).toEqual(['sos-hillshade', 'sos-contours']);
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-vault.json');
    addTerrain(asMap(map), mapConfig, 'vault');
    expect(map.style.layers.map((l) => l.id)).toEqual(['land', 'roads', 'sos-hillshade', 'sos-contours', 'labels']);
    setTerrainVisible(asMap(map), false);
    expect(map.visibility('sos-contours')).toBe('none');
    addTerrain(asMap(map), mapConfig, 'vault'); // idempotent
    expect(map.style.layers).toHaveLength(5);
  });
  it('skips terrain the box does not have', () => {
    const spec = terrainSpec({ ...mapConfig, terrain: { contours: null, hillshade: null } }, 'field');
    expect(spec.layers).toEqual([]);
  });
});

describe('recreateSource', () => {
  it('removes and re-adds the source and its layers in their original positions', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-vault.json');
    map.addSource('sos-overlay-health', { type: 'geojson', data: '/maps/overlays/health.geojson' });
    map.addLayer({ id: 'sos-overlay-health-point', type: 'circle', source: 'sos-overlay-health' }, 'labels');
    recreateSource(asMap(map), 'sos-overlay-health');
    expect(map.style.layers.map((l) => l.id)).toEqual(['land', 'roads', 'sos-overlay-health-point', 'labels']);
    expect(map.style.sources['sos-overlay-health']).toEqual({ type: 'geojson', data: '/maps/overlays/health.geojson' });
  });
  it('isEtagMismatch recognises the pmtiles error by class or name', async () => {
    const { EtagMismatch } = await import('pmtiles');
    expect(isEtagMismatch(new EtagMismatch())).toBe(true);
    const named = new Error('x');
    named.name = 'EtagMismatch';
    expect(isEtagMismatch(named)).toBe(true);
    expect(isEtagMismatch(new Error('y'))).toBe(false);
  });
});
