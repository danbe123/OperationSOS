export type LngLat = { lon: number; lat: number };
const R = 6371.0088;
const rad = (d: number) => (d * Math.PI) / 180;

export function distanceKm(a: LngLat, b: LngLat): number {
  const p1 = rad(a.lat);
  const p2 = rad(b.lat);
  const dp = rad(b.lat - a.lat);
  const dl = rad(b.lon - a.lon);
  const h = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function bearingDeg(a: LngLat, b: LngLat): number {
  const p1 = rad(a.lat);
  const p2 = rad(b.lat);
  const dl = rad(b.lon - a.lon);
  const y = Math.sin(dl) * Math.cos(p2);
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

export function pathLengthKm(points: LngLat[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i++) total += distanceKm(points[i - 1], points[i]);
  return total;
}

export function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  if (km < 10) return `${km.toFixed(2)} km`;
  return `${km.toFixed(1)} km`;
}

const POINTS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
export function formatBearing(deg: number): string {
  const whole = Math.round(deg);
  const point = POINTS[Math.round((deg % 360) / 22.5) % 16];
  return `${whole.toString().padStart(3, '0')}° ${point}`;
}

/** Naismith's rule: an hour for every 5 km on the flat, plus a minute for every 10 m of climb.
 * The box has no elevation data, so `ascentM` is usually zero and the answer is a floor, not a promise. */
export function naismithMinutes(km: number, ascentM = 0): number {
  return Math.round(km * 12 + ascentM / 10);
}

/** "18 min", "1 h 25 min": a walking time a household can plan around. */
export function formatWalk(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${(m % 60).toString().padStart(2, '0')} min`;
}
