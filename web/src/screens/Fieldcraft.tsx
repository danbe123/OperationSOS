import { useMemo } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Tile } from '../components/Tile';

export function Fieldcraft() {
  const { data, error, loading } = useQuery(() => api.pages(), []);
  const pages = useMemo(() => (data ?? []).filter((p) => p.category === 'fieldcraft').sort((a, b) => a.order - b.order), [data]);
  return (
    <div className="screen">
      <AppBar title="Field craft" />
      <p className="pad muted">Written for Britain and Ireland: our weather, plants, animals, laws and rescue services. Warmth before food; the decision to stay put is a skill.</p>
      {loading && <p className="pad muted">Loading…</p>}
      {error && <p className="pad warning">Pages unavailable: {error}</p>}
      <nav className="grid" aria-label="Field craft pages">
        {pages.map((p) => <Tile key={p.slug} to={`/p/${p.slug}`} icon={p.icon} title={p.title} subtitle={p.summary} />)}
      </nav>
    </div>
  );
}
