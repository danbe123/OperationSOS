export type MapQuery = { lat: number | null; lon: number | null; z: number | null; overlays: string[]; label: string | null };

export function parseMapQuery(search: string): MapQuery {
  const p = new URLSearchParams(search);
  const num = (key: string, min: number, max: number): number | null => {
    if (!p.has(key)) return null;
    const v = Number(p.get(key));
    return Number.isFinite(v) && v >= min && v <= max ? v : null;
  };
  return { lat: num('lat', -90, 90), lon: num('lon', -180, 180), z: num('z', 0, 22), overlays: p.getAll('overlay').filter(Boolean), label: p.get('label') };
}

export function mapQueryString(q: Partial<MapQuery>): string {
  const p = new URLSearchParams();
  if (q.lat != null && q.lon != null) {
    p.set('lat', q.lat.toFixed(5));
    p.set('lon', q.lon.toFixed(5));
  }
  if (q.z != null) p.set('z', String(Math.round(q.z * 10) / 10));
  for (const o of q.overlays ?? []) p.append('overlay', o);
  if (q.label) p.set('label', q.label);
  const s = p.toString();
  return s ? `?${s}` : '';
}
