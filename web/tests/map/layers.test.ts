import { describe, it, expect, vi } from 'vitest';
import type { Map as MlMap } from 'maplibre-gl';
import { FakeMap } from './fakeMap';
import { annotations, carryStyleAcross, overlayPaint, terrainSpec, addTerrain, setTerrainVisible, recreateSource, isEtagMismatch, pmtilesUrl } from '../../src/map/layers';
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
    const spec = terrainSpec(mapConfig, 'mono');
    expect(Object.keys(spec.sources)).toEqual(['sos-hillshade', 'sos-contours']);
    expect(spec.layers.map((l) => l.id)).toEqual(['sos-hillshade', 'sos-contours']);
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    addTerrain(asMap(map), mapConfig, 'mono');
    expect(map.style.layers.map((l) => l.id)).toEqual(['land', 'roads', 'sos-hillshade', 'sos-contours', 'labels']);
    setTerrainVisible(asMap(map), false);
    expect(map.visibility('sos-contours')).toBe('none');
    addTerrain(asMap(map), mapConfig, 'mono'); // idempotent
    expect(map.style.layers).toHaveLength(5);
  });
  it('skips terrain the box does not have', () => {
    const spec = terrainSpec({ ...mapConfig, terrain: { contours: null, hillshade: null } }, 'field');
    expect(spec.layers).toEqual([]);
  });
  it('draws its own colours in the theme: ochre contours on paper, a plain grey in mono', () => {
    const paint = (theme: 'field' | 'mono') => {
      const spec = terrainSpec(mapConfig, theme);
      const contours = spec.layers.find((l) => l.id === 'sos-contours') as { paint: Record<string, unknown> };
      const hillshade = spec.layers.find((l) => l.id === 'sos-hillshade') as { paint: Record<string, unknown> };
      return { contour: contours.paint['line-color'] as string, shade: hillshade.paint['raster-opacity'] as number };
    };
    expect(paint('field').contour).toBe('#b08050');
    // Mono states no hue anywhere, the map included.
    const mono = paint('mono').contour;
    expect(mono).toMatch(/^#([0-9a-f]{2})\1\1$/);
    // Hillshade sits lighter on the black theme, where the relief is the only thing carrying shape.
    expect(paint('mono').shade).toBeLessThan(paint('field').shade);
  });
});

/** A hex colour with no hue in it: #000000 through #ffffff, all three channels equal. */
const GREY = /^#([0-9a-f]{2})\1\1$/;

describe('annotation colours', () => {
  it('keeps the Field hues exactly as they were', () => {
    expect(annotations('field')).toEqual({
      pin: '#ffb000', label: '#1e88e5', pinStroke: '#000000',
      home: '#1b5e20', homeStroke: '#ffffff',
      route: '#1b5e20', measure: '#ff3d00', halo: '#ffffff',
    });
  });

  it('draws every annotation in Mono without a hue anywhere', () => {
    const c = annotations('mono');
    for (const [name, value] of Object.entries(c)) expect(value, name).toMatch(GREY);
    // Pins, the measuring line and the line to a facility are white; the label point is the one
    // thing told from a pin by tone rather than by hue, so it is a light grey rather than white.
    expect([c.pin, c.measure, c.route]).toEqual(['#ffffff', '#ffffff', '#ffffff']);
    expect(c.label).toBe('#d0d0d0');
    expect(c.label).not.toBe(c.pin);
    // Home is the one marker drawn the other way round: a white ring on black, so it is never read
    // as another dropped pin.
    expect(c.home).toBe('#000000');
    expect(c.homeStroke).toBe('#ffffff');
    // Whatever the sheet under it, an annotation carries its own outline and its labels a black halo.
    expect(c.pinStroke).toBe('#000000');
    expect(c.halo).toBe('#000000');
  });
});

describe('overlay colours', () => {
  const footpaths = { id: 'footpaths', color: '#3fb950' };
  const accessLand = { id: 'access-land', color: '#b58900' };

  it('leaves an overlay its own colour on paper', () => {
    expect(overlayPaint(footpaths, 'field')).toEqual({ color: '#3fb950', fillOpacity: 0.22, stroke: '#ffffff', dash: null });
    expect(overlayPaint(accessLand, 'field').color).toBe('#b58900');
  });

  it('gives Mono a white dashed footpath and a light grey wash for access land', () => {
    const paths = overlayPaint(footpaths, 'mono');
    // White, and dashed: the roads under it are white too, and a dash is what tells a path from one.
    expect(paths.color).toBe('#ffffff');
    expect(paths.dash).toEqual([2, 1.5]);
    expect(paths.stroke).toBe('#000000');
    const land = overlayPaint(accessLand, 'mono');
    expect(land.color).toMatch(GREY);
    expect(land.color).not.toBe('#ffffff');
    // A fill of white over a black sheet is a wash, so it sits lighter than it does on paper.
    expect(land.fillOpacity).toBeLessThan(overlayPaint(accessLand, 'field').fillOpacity);
    expect(land.dash).toBeNull();
  });
});

describe('recreateSource', () => {
  it('removes and re-adds the source and its layers in their original positions', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
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
