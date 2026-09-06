import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Page } from '../api/types';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { Screen, Body } from '../shell/Screen';
import { Tile } from '../components/Tile';
import { useSituation } from '../situation/SituationProvider';
import { TOOL_TILES } from './Tools';
import './guides.css';

type Group = { id: string; title: string; note: string; entries: { to: string; icon: string; title: string; sub?: string }[] };

const PAGE_GROUPS: { id: string; title: string; note: string; categories: string[] }[] = [
  { id: 'fieldcraft', title: 'Field craft', note: 'Shelter, fire, water, wild food, moving about.', categories: ['fieldcraft'] },
  { id: 'comms', title: 'Phone and radio', note: 'Numbers, PMR446, what still works.', categories: ['comms'] },
  { id: 'reference', title: 'Reference', note: 'The pages the guides link to.', categories: ['reference', 'plan', 'about'] },
];

function matches(term: string, ...text: (string | undefined)[]): boolean {
  if (!term) return true;
  const t = term.toLowerCase();
  return text.some((x) => (x ?? '').toLowerCase().includes(t));
}

/** Guides: the manual. Scenarios first, then the pages and the tools, all filterable in one field. */
export function Guides() {
  const playbooksQ = useQuery(() => api.playbooks(), []);
  const pagesQ = useQuery(() => api.pages(), []);
  const { view } = useSituation();
  const [term, setTerm] = useState('');
  const [only, setOnly] = useState<string | null>(null);
  const active = view?.scenario ?? null;

  const scenarios = useMemo(() => (playbooksQ.data ?? []).slice().sort((a, b) => a.order - b.order), [playbooksQ.data]);
  const pages: Page[] = useMemo(() => (pagesQ.data ?? []).slice().sort((a, b) => a.order - b.order), [pagesQ.data]);

  const groups: Group[] = [
    {
      id: 'scenarios', title: 'Situations', note: 'Twenty situations: what to do right now and over the months after.',
      entries: scenarios.map((p) => ({ to: `/s/${p.slug}`, icon: p.icon, title: p.title, sub: p.summary })),
    },
    ...PAGE_GROUPS.map((g) => ({
      id: g.id, title: g.title, note: g.note,
      entries: pages.filter((p) => g.categories.includes(p.category)).map((p) => ({ to: `/p/${p.slug}`, icon: p.icon, title: p.title, sub: p.summary })),
    })),
    { id: 'tools', title: 'Tools', note: 'Small offline tools. Nothing here needs the internet.', entries: TOOL_TILES.map((t) => ({ to: t.to, icon: t.icon, title: t.title, sub: t.subtitle })) },
  ];

  const shown = groups
    .filter((g) => !only || g.id === only)
    .map((g) => ({ ...g, entries: g.entries.filter((e) => matches(term, e.title, e.sub)) }))
    .filter((g) => g.entries.length > 0);
  const found = shown.reduce((n, g) => n + g.entries.length, 0);

  return (
    <Screen title="Guides" back={false}>
      <Body>
        <label className="field guides-filter">
          <span>Filter the guides</span>
          <input type="search" aria-label="Filter the guides" value={term} placeholder="flood, water, radio, cold" onChange={(e) => setTerm(e.target.value)} />
        </label>
        <div className="chips" role="group" aria-label="Kinds of guide">
          <button type="button" className={only === null ? 'chip active' : 'chip'} aria-pressed={only === null} onClick={() => setOnly(null)}>Everything</button>
          {groups.filter((g) => g.entries.length > 0).map((g) => (
            <button key={g.id} type="button" className={only === g.id ? 'chip active' : 'chip'} aria-pressed={only === g.id} onClick={() => setOnly(only === g.id ? null : g.id)}>
              {g.title} ({g.entries.length})
            </button>
          ))}
        </div>
        {active && (
          <p className="panel panel-warn">
            <Icon name="alert" size={18} /> <strong>{active.title}</strong> is running.{' '}
            <Link to={`/s/${active.slug}`}>Open its guide</Link>.
          </p>
        )}
        {playbooksQ.loading && <p className="muted">Loading the guides…</p>}
        {playbooksQ.error && <p className="warning">Guides unavailable: {playbooksQ.error}</p>}
        {pagesQ.error && <p className="warning">Pages unavailable: {pagesQ.error}</p>}
        {term && <p className="muted" role="status">{found === 1 ? '1 guide matches' : `${found} guides match`} “{term}”.</p>}
        {term && found === 0 && <p>Nothing matches. Try a shorter word, or <Link to={`/search?q=${encodeURIComponent(term)}`}>search the whole box</Link>.</p>}
        {shown.map((g) => (
          <section key={g.id} aria-label={g.title}>
            <h2>{g.title}</h2>
            <p className="muted">{g.note}</p>
            <nav className={g.id === 'scenarios' ? 'tiles' : 'tiles tiles-wide'} aria-label={g.title === 'Situations' ? 'Scenarios' : g.title}>
              {g.entries.map((e) => <Tile key={e.to} to={e.to} icon={e.icon} title={e.title} subtitle={e.sub} />)}
            </nav>
          </section>
        ))}
      </Body>
    </Screen>
  );
}
