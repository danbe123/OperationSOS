import { useMemo } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Tile } from '../components/Tile';

export function Radio() {
  const { data, error, loading } = useQuery(() => api.pages(), []);
  const comms = useMemo(() => (data ?? []).filter((p) => p.category === 'comms').sort((a, b) => a.order - b.order), [data]);
  return (
    <div className="screen">
      <AppBar title="Phone and radio" />
      <p className="pad warning">Emergency 999 · NHS 111 · Power cut 105 · Floodline 0345 988 1188</p>
      {loading && <p className="pad muted">Loading…</p>}
      {error && <p className="pad warning">Pages unavailable: {error}</p>}
      <nav className="grid" aria-label="Comms pages">
        {comms.map((p) => (
          <Tile key={p.slug} to={`/p/${p.slug}`} icon={p.icon} title={p.title} />
        ))}
      </nav>
    </div>
  );
}
