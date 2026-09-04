import { useMemo } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { SearchBar } from '../components/SearchBar';
import { StatusStrip } from '../components/StatusStrip';
import { Tile } from '../components/Tile';
import { Icon } from '../icons';

export const HOME_TILES = [
  { to: '/medical', icon: 'medical', title: 'Medical', subtitle: 'Quick cards, NHS' },
  { to: '/map', icon: 'map', title: 'Maps', subtitle: 'UK and Ireland, offline' },
  { to: '/library', icon: 'library', title: 'Library', subtitle: 'Wikipedia, manuals, books' },
  { to: '/radio', icon: 'radio', title: 'Phone and radio', subtitle: 'Numbers, PMR446, what works' },
  { to: '/plan', icon: 'plan', title: 'Plan', subtitle: 'Household plan, notes, pins' },
] as const;

export function Home() {
  const { data, error, loading } = useQuery(() => api.playbooks(), []);
  const sorted = useMemo(() => (data ?? []).slice().sort((a, b) => a.order - b.order), [data]);
  return (
    <div className="screen home">
      <AppBar
        title="Operation SOS"
        back={false}
        search={false}
        actions={
          <>
            <Link to="/ai" className="btn btn-chrome"><Icon name="ai" /><span>AI</span></Link>
            <Link to="/system" className="btn btn-chrome"><Icon name="settings" /><span>System</span></Link>
          </>
        }
      />
      <div className="pad">
        <SearchBar />
      </div>
      <nav className="tiles" aria-label="Main sections">
        {HOME_TILES.map((t) => (
          <Tile key={t.to} to={t.to} icon={t.icon} title={t.title} subtitle={t.subtitle} big />
        ))}
      </nav>
      <h2 className="pad">What is happening?</h2>
      {loading && <p className="pad muted">Loading playbooks…</p>}
      {error && <p className="pad warning">Playbooks unavailable: {error}</p>}
      <nav className="grid" aria-label="Scenarios">
        {sorted.map((p) => (
          <Tile key={p.slug} to={`/s/${p.slug}`} icon={p.icon} title={p.title} subtitle={p.summary} />
        ))}
      </nav>
      <StatusStrip />
    </div>
  );
}
