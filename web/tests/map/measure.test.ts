import { describe, it, expect } from 'vitest';
import { distanceKm, bearingDeg, pathLengthKm, formatDistance, formatBearing, formatWalk, naismithMinutes } from '../../src/map/measure';

const london = { lat: 51.5074, lon: -0.1278 };
const paris = { lat: 48.8566, lon: 2.3522 };
const edinburgh = { lat: 55.9533, lon: -3.1883 };

describe('measure', () => {
  it('haversine distance and initial bearing', () => {
    expect(Math.abs(distanceKm(london, paris) - 343.56)).toBeLessThan(0.1);
    expect(Math.abs(bearingDeg(london, paris) - 148.1)).toBeLessThan(0.2);
    expect(Math.abs(distanceKm(london, edinburgh) - 533.65)).toBeLessThan(0.1);
    expect(Math.abs(bearingDeg(london, edinburgh) - 339.1)).toBeLessThan(0.2);
    expect(pathLengthKm([london, paris, edinburgh])).toBeCloseTo(distanceKm(london, paris) + distanceKm(paris, edinburgh), 6);
    expect(pathLengthKm([london])).toBe(0);
  });
  it('formats metres under 1 km, two decimals under 10 km, one above; bearings with compass points', () => {
    expect(formatDistance(0.42)).toBe('420 m');
    expect(formatDistance(3.456)).toBe('3.46 km');
    expect(formatDistance(343.556)).toBe('343.6 km');
    expect(formatBearing(148.1)).toBe('148° SSE');
    expect(formatBearing(0)).toBe('000° N');
    expect(formatBearing(359.7)).toBe('360° N');
  });
  it('walks at Naismith: an hour per 5 km, a minute per 10 m of climb', () => {
    expect(naismithMinutes(5)).toBe(60);
    expect(naismithMinutes(1.5)).toBe(18);
    expect(naismithMinutes(0)).toBe(0);
    expect(naismithMinutes(5, 300)).toBe(90);
    expect(formatWalk(18)).toBe('18 min');
    expect(formatWalk(85)).toBe('1 h 25 min');
    expect(formatWalk(-3)).toBe('0 min');
  });
});
