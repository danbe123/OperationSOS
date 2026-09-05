import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { SearchBar } from '../components/SearchBar';
import { StatusStrip } from '../components/StatusStrip';
import { Tile } from '../components/Tile';
import { Icon } from '../icons';
import './home.css';
import { situationLine } from '../components/SituationClock';
import { Briefing } from '../situation/Briefing';
import { SituationStrip } from '../situation/SituationStrip';
import { useSituation } from '../situation/SituationProvider';

export type HomeTile = { to: string; icon: string; title: string; subtitle: string };

export const HOME_TILES: HomeTile[] = [
  { to: '/medical', icon: 'medical', title: 'Medical', subtitle: 'Quick cards, NHS' },
  { to: '/map', icon: 'map', title: 'Maps', subtitle: 'UK and Ireland, offline' },
  { to: '/library', icon: 'library', title: 'Library', subtitle: 'Wikipedia, manuals, books' },
  { to: '/radio', icon: 'radio', title: 'Phone and radio', subtitle: 'Numbers, PMR446, what works' },
  { to: '/plan', icon: 'plan', title: 'Plan', subtitle: 'Household, stock, notes, pins' },
  { to: '/tools', icon: 'hammer', title: 'Tools', subtitle: 'Timers, sun, sums, log' },
];

/** The overlays a scenario wants open the moment the map is reached for. */
export const SCENARIO_OVERLAYS: Record<string, string> = { 'storms-flooding': 'flood-zones' };

/** With `map_first` set (a flood, say) the map leads the tile row, carrying the scenario's own
 * overlay so the flood zones are already drawn; otherwise the order is fixed. */
export function homeTiles(mapFirst: boolean, scenario?: string | null): HomeTile[] {
  const overlay = scenario ? SCENARIO_OVERLAYS[scenario] : undefined;
  const tiles = HOME_TILES.map((t) => (overlay && t.to === '/map' ? { ...t, to: `/map?overlay=${overlay}`, subtitle: 'UK and Ireland, flood zones on' } : { ...t }));
  if (!mapFirst) return tiles;
  const map = tiles.find((t) => t.to.startsWith('/map'));
  return map ? [map, ...tiles.filter((t) => t !== map)] : tiles;
}

export function Home() {
  const { data, error, loading } = useQuery(() => api.playbooks(), []);
  const { status } = useStatus();
  const { view } = useSituation();
  const situation = status?.situation ?? null;
  const tiles = homeTiles(view?.modes.map_first ?? false, view?.scenario?.slug ?? null);
  const sorted = useMemo(() => (data ?? []).slice().sort((a, b) => a.order - b.order), [data]);
  const [lastSlug] = useState(() => {
    try { return localStorage.getItem('sos.lastPlaybook'); } catch { return null; }
  });
  const last = sorted.find((p) => p.slug === lastSlug);
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
      <SituationStrip />
      <Briefing />
      <div className="home-intro">
        <div><p className="eyebrow">Your offline field manual</p><h2>Find your next step.</h2><p className="muted">Practical guidance for you and your household.</p></div>
        <div className="home-search">
        <SearchBar />
        <p className="muted">Search a situation, a place or a skill.</p>
        </div>
      </div>
      {situation && <Link className="resume-card situation-card" to={`/s/${situation.slug}`}><Icon name="alert" /><span><small>Active situation, {situationLine({ ...situation, title: null, elapsed_s: 0, phase: 'right-now' })}</small><strong>{(data ?? []).find((p) => p.slug === situation.slug)?.title ?? situation.slug}</strong></span><Icon name="forward" /></Link>}
      {last && last.slug !== situation?.slug && <Link className="resume-card" to={`/s/${last.slug}`}><Icon name="plan" /><span><small>Recently opened on this device</small><strong>Continue: {last.title}</strong></span><Icon name="forward" /></Link>}
      <div className="home-section-heading"><p className="eyebrow">Keep within reach</p><h2>Your tools</h2></div>
      <nav className="tiles home-tools" aria-label="Main sections">
        {tiles.map((t) => <Tile key={t.to} to={t.to} icon={t.icon} title={t.title} subtitle={t.subtitle} />)}
      </nav>
      <div className="home-section-heading" id="all-situations"><p className="eyebrow">The field manual</p><h2>All situations</h2></div>
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
