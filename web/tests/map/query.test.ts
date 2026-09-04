import { describe, it, expect } from 'vitest';
import { parseMapQuery, mapQueryString } from '../../src/map/query';

describe('parseMapQuery', () => {
  it('reads lat, lon, z, repeated overlay and label', () => {
    expect(parseMapQuery('?lat=51.5&lon=-0.12&z=12&overlay=health&overlay=water&label=Home')).toEqual({ lat: 51.5, lon: -0.12, z: 12, overlays: ['health', 'water'], label: 'Home' });
  });
  it('drops out-of-range or malformed numbers', () => {
    expect(parseMapQuery('?lat=99&lon=abc&z=30')).toEqual({ lat: null, lon: null, z: null, overlays: [], label: null });
    expect(parseMapQuery('')).toEqual({ lat: null, lon: null, z: null, overlays: [], label: null });
  });
});

describe('mapQueryString', () => {
  it('serialises with five-decimal coordinates and one-decimal zoom', () => {
    expect(mapQueryString({ lat: 50.937880244, lon: -1.470738, z: 13.26, overlays: ['health'], label: 'OS HQ' })).toBe('?lat=50.93788&lon=-1.47074&z=13.3&overlay=health&label=OS+HQ');
    expect(mapQueryString({ overlays: [] })).toBe('');
  });
});
