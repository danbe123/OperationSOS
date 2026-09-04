import { describe, it, expect } from 'vitest';
import { OSGB36, IRISH65, latLonToEN, enToLatLon, toOSGB, toIrish, gridRef, parseGridRef, region, osgbLetters, irishLetter } from '../../src/map/grid';

const OSHQ = { lat: 50.9379, lon: -1.4708 };

describe('OSGB36 with the Helmert parameters', () => {
  it('OS head office (Adanac Park) projects to E 437281 N 115517 within 3 m', () => {
    const [e, n] = latLonToEN(OSGB36, OSHQ.lat, OSHQ.lon);
    expect(Math.abs(e - 437281)).toBeLessThan(3);
    expect(Math.abs(n - 115517)).toBeLessThan(3);
    expect(toOSGB(OSHQ.lat, OSHQ.lon)).toBe('SU 3728 1551');
    expect(toOSGB(OSHQ.lat, OSHQ.lon, 6)).toBe('SU 372 155');
  });
  it('inverts back to the lat/lon within 0.0002 degrees', () => {
    const ll = enToLatLon(OSGB36, 437281, 115517);
    expect(Math.abs(ll.lat - OSHQ.lat)).toBeLessThan(0.0002);
    expect(Math.abs(ll.lon - OSHQ.lon)).toBeLessThan(0.0002);
  });
  it('Ben Nevis is NN 166 712', () => {
    const ll = enToLatLon(OSGB36, 216650, 771250);
    expect(Math.abs(ll.lat - 56.7966)).toBeLessThan(0.001);
    expect(Math.abs(ll.lon - -5.0039)).toBeLessThan(0.001);
    expect(toOSGB(ll.lat, ll.lon, 6)).toBe('NN 166 712');
    expect(toOSGB(ll.lat, ll.lon)).toBe('NN 1665 7125'); // round-trip through proj4 lands 0.03mm north of the exact 771250 input, which floors up a digit
  });
  it('letters: skips I and covers Shetland and the Isle of Man', () => {
    expect(osgbLetters(437281, 115517)).toBe('SU');
    expect(osgbLetters(216650, 771250)).toBe('NN');
    expect(osgbLetters(-1, 0)).toBeNull();
    expect(gridRef(60.15, -1.15).text.startsWith('HU ')).toBe(true);
    expect(gridRef(54.1509, -4.4823).text.startsWith('SC ')).toBe(true);
  });
});

describe('Irish Grid (EPSG:29903)', () => {
  it('Belfast City Hall is J 338 740 and Dublin GPO is O 159 346', () => {
    expect(toIrish(54.5973, -5.9301, 6)).toBe('J 338 740');
    expect(toIrish(54.5973, -5.9301)).toBe('J 3382 7408');
    expect(toIrish(53.3498, -6.2603, 6)).toBe('O 159 346');
    expect(irishLetter(333828, 374088)).toBe('J');
    expect(irishLetter(600000, 0)).toBeNull();
    const [e, n] = latLonToEN(IRISH65, 54.5973, -5.9301);
    expect(Math.abs(e - 333828)).toBeLessThan(3);
    expect(Math.abs(n - 374088)).toBeLessThan(3);
  });
});

describe('region and gridRef', () => {
  it('picks OSGB for Great Britain, Irish for the island of Ireland, lat/lon for the Channel Islands and elsewhere', () => {
    expect(region(55.31, -5.8)).toBe('gb'); // Mull of Kintyre
    expect(region(55.29, -6.2)).toBe('ireland'); // Rathlin Island
    expect(region(51.9, -5.3)).toBe('gb'); // Pembrokeshire
    expect(region(49.1868, -2.1036)).toBe('ci'); // St Helier
    expect(region(48.39, -4.49)).toBe('other'); // Brest
    expect(gridRef(55.29, -6.2, 6)).toEqual({ system: 'Irish', text: 'D 144 507' });
    expect(gridRef(49.1868, -2.1036)).toEqual({ system: 'latlon', text: '49.18680, -2.10360' });
    expect(gridRef(OSHQ.lat, OSHQ.lon)).toEqual({ system: 'OSGB', text: 'SU 3728 1551' });
  });
});

describe('parseGridRef', () => {
  it('parses OSGB with or without spaces, Irish refs and decimal lat/lon', () => {
    const a = parseGridRef('SU 3728 1551')!;
    expect(Math.abs(a.lat - OSHQ.lat)).toBeLessThan(0.001);
    expect(Math.abs(a.lon - OSHQ.lon)).toBeLessThan(0.001);
    const b = parseGridRef('su37281551')!;
    expect(Math.abs(b.lat - a.lat)).toBeLessThan(1e-9);
    const c = parseGridRef('J338740')!;
    expect(Math.abs(c.lat - 54.5973)).toBeLessThan(0.002);
    expect(Math.abs(c.lon - -5.9301)).toBeLessThan(0.002);
    expect(parseGridRef('51.5, -0.12')).toEqual({ lat: 51.5, lon: -0.12 });
    expect(parseGridRef('SU 372 15')).toBeNull();
    expect(parseGridRef('hello')).toBeNull();
  });
});
