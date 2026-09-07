import { describe, it, expect, vi } from 'vitest';
import type { Map as MlMap } from 'maplibre-gl';
import { FakeMap } from './fakeMap';
import { annotationPaint, annotations, carryStyleAcross, overlayPaint, terrainSpec, addTerrain, setTerrainLayerVisible, recreateSource, isEtagMismatch, pmtilesUrl } from '../../src/map/layers';
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
    setTerrainLayerVisible(asMap(map), 'sos-contours', false);
    expect(map.visibility('sos-contours')).toBe('none');
    addTerrain(asMap(map), mapConfig, 'mono'); // idempotent
    expect(map.style.layers).toHaveLength(5);
  });
  it('hides one terrain layer without touching the other: contours and hillshade have a chip each', () => {
    const map = new FakeMap();
    map.setStyle('/maps/styles/osm-field.json');
    addTerrain(asMap(map), mapConfig, 'field');
    setTerrainLayerVisible(asMap(map), 'sos-hillshade', false);
    expect(map.visibility('sos-hillshade')).toBe('none');
    expect(map.visibility('sos-contours')).toBe('visible');
    setTerrainLayerVisible(asMap(map), 'sos-hillshade', true);
    expect(map.visibility('sos-hillshade')).toBe('visible');
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
      here: '#1e88e5', hereStroke: '#ffffff',
      route: '#1b5e20', measure: '#ff3d00',
      labelInk: '#000000', halo: '#ffffff', measureRing: 0,
    });
  });

  /** What the map actually paints, not just what the table holds: every one of these is a value the
   * Field map had before the themes were pulled out into a table, and every one of them is a way of
   * writing something invisible if a token is wired to the wrong property. */
  it('paints the Field layers exactly as it did before the tokens existed', () => {
    const p = annotationPaint('field');
    // Captions are black ink on a white halo. Written in the mark's own colour instead, the home
    // caption is white on a white halo — an invisible word — and pin captions turn amber.
    expect(p['sos-home-label']).toEqual({ 'text-color': '#000000', 'text-halo-color': '#ffffff', 'text-halo-width': 1.5 });
    expect(p['sos-pins-label']).toEqual({ 'text-color': '#000000', 'text-halo-color': '#ffffff', 'text-halo-width': 1.5 });
    // Measuring points are bare orange dots on paper: no ring, as before.
    expect(p['sos-measure-point']).toEqual({ 'circle-radius': 5, 'circle-color': '#ff3d00', 'circle-stroke-color': '#000000', 'circle-stroke-width': 0 });
    expect(p['sos-measure-line']).toEqual({ 'line-color': '#ff3d00', 'line-width': 3, 'line-dasharray': [2, 1] });
    expect(p['sos-home-point']).toEqual({ 'circle-radius': 11, 'circle-color': '#1b5e20', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 3 });
    expect(p['sos-here-point']).toEqual({ 'circle-radius': 8, 'circle-color': '#1e88e5', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 3 });
    expect(annotationPaint('mono')['sos-here-point']).toMatchObject({ 'circle-color': '#ffffff', 'circle-stroke-color': '#000000' });
    expect(p['sos-route-line']).toEqual({ 'line-color': '#1b5e20', 'line-width': 4, 'line-dasharray': [3, 1.5] });
    expect(p['sos-pins-point']).toEqual({
      'circle-radius': 8, 'circle-color': ['match', ['get', 'kind'], 'label', '#1e88e5', '#ffb000'],
      'circle-stroke-color': '#000000', 'circle-stroke-width': 2,
    });
  });

  it('writes Mono captions white on a black halo, and rings the measuring points', () => {
    const p = annotationPaint('mono');
    expect(p['sos-home-label']).toEqual({ 'text-color': '#ffffff', 'text-halo-color': '#000000', 'text-halo-width': 1.5 });
    expect(p['sos-pins-label']).toEqual({ 'text-color': '#ffffff', 'text-halo-color': '#000000', 'text-halo-width': 1.5 });
    // A white dot over a white road needs the ring Field does not.
    expect(p['sos-measure-point']['circle-stroke-width']).toBe(1.5);
    expect(p['sos-measure-point']['circle-stroke-color']).toBe('#000000');
    // The home marker is the one drawn inside out: black disc, white ring.
    expect(p['sos-home-point']['circle-color']).toBe('#000000');
    expect(p['sos-home-point']['circle-stroke-color']).toBe('#ffffff');
  });

  it('names a paint entry for every layer the box draws, in both themes', () => {
    const ids = ['sos-pins-point', 'sos-pins-label', 'sos-home-point', 'sos-home-label', 'sos-here-halo', 'sos-here-point', 'sos-route-line', 'sos-measure-line', 'sos-measure-point'];
    for (const theme of ['field', 'mono'] as const) expect(Object.keys(annotationPaint(theme)).sort()).toEqual([...ids].sort());
  });

  it('draws every annotation in Mono without a hue anywhere', () => {
    const c = annotations('mono');
    for (const [name, value] of Object.entries(c)) {
      if (typeof value === 'number') continue;   // measureRing is a width, not a colour
      expect(value, name).toMatch(GREY);
    }
    // Pins, the measuring line and the line to a facility are white; the label point is the one
    // thing told from a pin by tone rather than by hue, so it is a light grey rather than white.
    expect([c.pin, c.measure, c.route]).toEqual(['#ffffff', '#ffffff', '#ffffff']);
    expect(c.label).toBe('#d0d0d0');
    expect(c.label).not.toBe(c.pin);
    // Home is the one marker drawn the other way round: a white ring on black, so it is never read
    // as another dropped pin.
    expect(c.home).toBe('#000000');
    expect(c.homeStroke).toBe('#ffffff');
    // Whatever the sheet under it, an annotation carries its own outline, and a caption is white ink
    // on a black halo rather than the colour of the mark it names.
    expect(c.pinStroke).toBe('#000000');
    expect(c.halo).toBe('#000000');
    expect(c.labelInk).toBe('#ffffff');
    expect(c.labelInk).not.toBe(c.halo);
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
