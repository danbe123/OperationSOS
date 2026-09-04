import proj4 from 'proj4';

/** OSGB36 / British National Grid with the OS Helmert parameters (about 2 m accuracy). */
export const OSGB36 = '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs';
/** TM75 / Irish Grid (EPSG:29903). */
export const IRISH65 = '+proj=tmerc +lat_0=53.5 +lon_0=-8 +k=1.000035 +x_0=200000 +y_0=250000 +ellps=mod_airy +towgs84=482.5,-130.6,564.6,-1.042,-0.214,-0.631,8.15 +units=m +no_defs';
const WGS84 = 'EPSG:4326';
const LETTERS = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'; // no I

export type Region = 'gb' | 'ireland' | 'ci' | 'other';

// Coarse outline of the island of Ireland (lon, lat); Kintyre and Islay stay outside, Rathlin and the Copeland Islands inside.
const IRELAND: [number, number][] = [[-10.9, 51.3], [-5.9, 51.3], [-5.35, 53.3], [-5.35, 54.55], [-5.6, 55.1], [-6.05, 55.5], [-8.6, 55.6], [-10.9, 54.3]];

function inPolygon(x: number, y: number, poly: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export function latLonToEN(def: string, lat: number, lon: number): [number, number] {
  const [e, n] = proj4(WGS84, def, [lon, lat]);
  return [e, n];
}
export function enToLatLon(def: string, e: number, n: number): { lat: number; lon: number } {
  const [lon, lat] = proj4(def, WGS84, [e, n]);
  return { lat, lon };
}

export function region(lat: number, lon: number): Region {
  if (lat > 49.1 && lat < 49.95 && lon > -3.0 && lon < -1.8) return 'ci';
  if (inPolygon(lon, lat, IRELAND)) return 'ireland';
  const [e, n] = latLonToEN(OSGB36, lat, lon);
  return e >= 0 && e < 700_000 && n >= 0 && n < 1_300_000 ? 'gb' : 'other';
}

function figures(e: number, n: number, count: 6 | 8 | 10): string {
  const digits = count / 2;
  const div = 10 ** (5 - digits);
  const ee = Math.floor((e % 100_000) / div).toString().padStart(digits, '0');
  const nn = Math.floor((n % 100_000) / div).toString().padStart(digits, '0');
  return `${ee} ${nn}`;
}

export function osgbLetters(e: number, n: number): string | null {
  if (e < 0 || e >= 700_000 || n < 0 || n >= 1_300_000) return null;
  const e100 = Math.floor(e / 100_000);
  const n100 = Math.floor(n / 100_000);
  let l1 = 19 - n100 - ((19 - n100) % 5) + Math.floor((e100 + 10) / 5);
  let l2 = (((19 - n100) * 5) % 25) + (e100 % 5);
  if (l1 > 7) l1++;
  if (l2 > 7) l2++;
  return String.fromCharCode(65 + l1) + String.fromCharCode(65 + l2);
}

export function irishLetter(e: number, n: number): string | null {
  if (e < 0 || e >= 500_000 || n < 0 || n >= 500_000) return null;
  let idx = (4 - Math.floor(n / 100_000)) * 5 + Math.floor(e / 100_000);
  if (idx >= 8) idx++;
  return String.fromCharCode(65 + idx);
}

export function toOSGB(lat: number, lon: number, count: 6 | 8 = 8): string | null {
  const [e, n] = latLonToEN(OSGB36, lat, lon);
  const letters = osgbLetters(e, n);
  return letters ? `${letters} ${figures(e, n, count)}` : null;
}
export function toIrish(lat: number, lon: number, count: 6 | 8 = 8): string | null {
  const [e, n] = latLonToEN(IRISH65, lat, lon);
  const letter = irishLetter(e, n);
  return letter ? `${letter} ${figures(e, n, count)}` : null;
}

export type GridRef = { system: 'OSGB' | 'Irish' | 'latlon'; text: string };

export function gridRef(lat: number, lon: number, count: 6 | 8 = 8): GridRef {
  const r = region(lat, lon);
  if (r === 'gb') {
    const t = toOSGB(lat, lon, count);
    if (t) return { system: 'OSGB', text: t };
  }
  if (r === 'ireland') {
    const t = toIrish(lat, lon, count);
    if (t) return { system: 'Irish', text: t };
  }
  return { system: 'latlon', text: `${lat.toFixed(5)}, ${lon.toFixed(5)}` };
}

function splitDigits(a: string, b: string | undefined): [string, string] | null {
  if (b !== undefined) return a.length === b.length ? [a, b] : null;
  if (a.length % 2 !== 0) return null;
  return [a.slice(0, a.length / 2), a.slice(a.length / 2)];
}
function centreOf(hundredKmE: number, hundredKmN: number, digits: [string, string]): [number, number] {
  const div = 10 ** (5 - digits[0].length);
  return [hundredKmE * 100_000 + Number(digits[0]) * div + div / 2, hundredKmN * 100_000 + Number(digits[1]) * div + div / 2];
}

/** Splits a run of grid digits into an equal-length [easting, northing] pair: two space-separated groups if given, otherwise the run is halved (so "37281551" becomes "3728"/"1551" just as "3728 1551" does). */
function digitGroups(raw: string): [string, string] | null {
  const parts = raw.trim().split(' ').filter(Boolean);
  if (parts.length === 2) return splitDigits(parts[0], parts[1]);
  if (parts.length === 1) return splitDigits(parts[0], undefined);
  return null;
}

/** Accepts "SU 3728 1551", "SU37281551", "J 338 740", "J338740" and "51.5, -0.12". */
export function parseGridRef(text: string): { lat: number; lon: number } | null {
  const t = text.trim().toUpperCase().replace(/\s+/g, ' ');
  const gb = /^([A-HJ-Z]{2}) ?([\d ]+)$/.exec(t);
  if (gb) {
    const digits = digitGroups(gb[2]);
    if (!digits || digits[0].length < 3) return null;
    const l1 = LETTERS.indexOf(gb[1][0]);
    const l2 = LETTERS.indexOf(gb[1][1]);
    if (l1 < 0 || l2 < 0) return null;
    const e100 = ((l1 - 2) % 5) * 5 + (l2 % 5);
    const n100 = 19 - Math.floor(l1 / 5) * 5 - Math.floor(l2 / 5);
    if (e100 < 0 || e100 > 6 || n100 < 0 || n100 > 12) return null;
    const [e, n] = centreOf(e100, n100, digits);
    return enToLatLon(OSGB36, e, n);
  }
  const ie = /^([A-HJ-Z]) ?([\d ]+)$/.exec(t);
  if (ie) {
    const digits = digitGroups(ie[2]);
    if (!digits || digits[0].length < 3) return null;
    const idx = LETTERS.indexOf(ie[1]);
    const [e, n] = centreOf(idx % 5, 4 - Math.floor(idx / 5), digits);
    return enToLatLon(IRISH65, e, n);
  }
  const ll = /^(-?\d+(?:\.\d+)?)[, ] ?(-?\d+(?:\.\d+)?)$/.exec(t);
  if (ll) {
    const lat = Number(ll[1]);
    const lon = Number(ll[2]);
    if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) return { lat, lon };
  }
  return null;
}
