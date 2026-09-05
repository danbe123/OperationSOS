import { useMemo, useState } from 'react';
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
      <div className="home-intro">
        <div><p className="eyebrow">Your offline field manual</p><h2>Find your next step.</h2><p className="muted">Practical guidance for you and your household.</p></div>
        <div className="home-search">
        <SearchBar />
        <p className="muted">Search a situation, a place or a skill.</p>
        </div>
      </div>
      {last && <Link className="resume-card" to={`/s/${last.slug}`}><Icon name="plan" /><span><small>Recently opened on this device</small><strong>Continue: {last.title}</strong></span><Icon name="forward" /></Link>}
      <div className="home-section-heading"><p className="eyebrow">Start here</p><h2>What is happening?</h2></div>
      <nav className="situation-grid" aria-label="Quick help">
        <Link className="situation medical-entry" to="/medical"><Icon name="medical" /><span><strong>Someone is hurt</strong><small>First aid and medical guidance</small></span><Icon name="forward" /></Link>
        <Link className="situation" to="/s/grid-collapse"><Icon name="power" /><span><strong>Power is out</strong><small>Blackouts and essential supplies</small></span><Icon name="forward" /></Link>
        <Link className="situation" to="/p/water-disinfection"><Icon name="wave" /><span><strong>Need safe water</strong><small>Water disinfection guidance</small></span><Icon name="forward" /></Link>
        <Link className="situation" to="/s/storms-flooding"><Icon name="plume" /><span><strong>Storms or flooding</strong><small>Prepare and respond</small></span><Icon name="forward" /></Link>
        <Link className="situation" to="/s/severe-winter"><Icon name="snowflake" /><span><strong>Severe cold</strong><small>Warmth and winter disruption</small></span><Icon name="forward" /></Link>
        <a className="situation" href="#all-situations"><Icon name="library" /><span><strong>All situations</strong><small>Browse the complete field manual</small></span><Icon name="forward" /></a>
      </nav>
      <div className="home-section-heading"><p className="eyebrow">Keep within reach</p><h2>Your tools</h2></div>
      <nav className="tiles home-tools" aria-label="Main sections">
        {HOME_TILES.map((t) => <Tile key={t.to} to={t.to} icon={t.icon} title={t.title} subtitle={t.subtitle} />)}
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
