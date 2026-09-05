import { useMemo } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';

export function Fieldcraft() {
  const { data, error, loading } = useQuery(() => api.pages(), []);
  const pages = useMemo(() => (data ?? []).filter((p) => p.category === 'fieldcraft').sort((a, b) => a.order - b.order), [data]);
  return (
    <Screen title="Field craft">
      <Body>
        <p className="muted measure">Written for Britain and Ireland: our weather, plants, animals, laws and rescue services. Warmth before food; the decision to stay put is a skill.</p>
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Pages unavailable: {error}</p>}
        <nav className="tiles tiles-wide" aria-label="Field craft pages">
          {pages.map((p) => <Tile key={p.slug} to={`/p/${p.slug}`} icon={p.icon} title={p.title} subtitle={p.summary} />)}
        </nav>
      </Body>
    </Screen>
  );
}
