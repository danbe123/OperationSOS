import { describe, it, expect } from 'vitest';
import { sunTimes, formatDayLength } from '../../src/tools/sun';

const LONDON = { lat: 51.5074, lon: -0.1278 };
const utcHM = (d: Date) => d.getUTCHours() * 60 + d.getUTCMinutes();
const near = (d: Date, hh: number, mm: number, tolMin = 4) => Math.abs(utcHM(d) - (hh * 60 + mm)) <= tolMin;

describe('sunTimes', () => {
  it('matches London on the June solstice (04:43 to 21:21 BST)', () => {
    const t = sunTimes(LONDON.lat, LONDON.lon, new Date(Date.UTC(2026, 5, 21)));
    if (t.polar) throw new Error('unexpected polar');
    expect(near(t.sunrise, 3, 43)).toBe(true);
    expect(near(t.sunset, 20, 21)).toBe(true);
    expect(t.dayLengthMin).toBeGreaterThan(16 * 60 + 30);
    expect(t.civilDawn && t.civilDawn < t.sunrise).toBe(true);
  });
  it('matches London on the December solstice (08:04 to 15:53 GMT)', () => {
    const t = sunTimes(LONDON.lat, LONDON.lon, new Date(Date.UTC(2026, 11, 21)));
    if (t.polar) throw new Error('unexpected polar');
    expect(near(t.sunrise, 8, 4)).toBe(true);
    expect(near(t.sunset, 15, 53)).toBe(true);
  });
  it('matches Lerwick in June (03:38 to 22:34 BST) and reports the long day', () => {
    const t = sunTimes(60.155, -1.145, new Date(Date.UTC(2026, 5, 21)));
    if (t.polar) throw new Error('unexpected polar');
    expect(near(t.sunrise, 2, 38, 6)).toBe(true);
    expect(near(t.sunset, 21, 34, 6)).toBe(true);
    expect(t.civilDusk !== null && t.civilDusk > t.sunset).toBe(true);   // civil dusk comes late but does come at 60 degrees north
  });
  it('gives a short day in the southern hemisphere in June and polar day and night in Svalbard', () => {
    const sydney = sunTimes(-33.87, 151.21, new Date(Date.UTC(2026, 5, 21)));
    if (sydney.polar) throw new Error('unexpected polar');
    expect(sydney.dayLengthMin).toBeLessThan(10 * 60);
    expect(sunTimes(78.22, 15.63, new Date(Date.UTC(2026, 5, 21))).polar).toBe('day');
    expect(sunTimes(78.22, 15.63, new Date(Date.UTC(2026, 11, 21))).polar).toBe('night');
  });
  it('formats day length', () => {
    expect(formatDayLength(996)).toBe('16 h 36 min');
    expect(formatDayLength(60)).toBe('1 h 00 min');
  });
});
