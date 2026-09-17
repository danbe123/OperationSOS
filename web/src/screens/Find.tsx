import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { SearchResponse } from '../api/types';
import { useQuery } from '../api/useQuery';
import { chipsFor, dedupe, groupResults } from '../api/results';
import { Icon } from '../icons';
import { ResultList } from '../components/ResultList';
import { SearchBar } from '../components/SearchBar';
import { ShelfTiles } from '../components/ShelfTiles';
import { Screen, Body } from '../shell/Screen';
import './find.css';

/** How many source chips stand on the screen before the rest go behind "More sources". */
export const CHIP_ROW = 4;

/** What a household reaches for first: one tap each, before the keyboard. */
export const QUICK_FINDS = ['CPR', 'Bleeding', 'Burns', 'Water', 'Power cut', 'Hypothermia', 'Radio', 'Iodine'];

/** Find: the field first, and nothing above it. Before a search, the handful of things people look
 * for most as one-tap chips; after one, the source chips with the count, then the box's own guidance
 * and every other source in a group of its own. No heading, no paragraph: the rail says Find, and
 * the row they took was a row of results on the kiosk. */
export function Find() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const sourcesParam = params.get('sources') ?? '';
  const sources = sourcesParam.split(',').filter(Boolean);
  const { status } = useStatus();
  const { data, error, loading } = useQuery<SearchResponse | null>(
    () => (q.trim() ? api.search(q, { sources: sources.length ? sources : undefined }) : Promise.resolve(null)),
    [q, sourcesParam],
  );
  // One row per target, the box's own first, and the chips counted from the very rows below them.
  const shown = useMemo(() => (data ? dedupe(data.results) : []), [data]);
  const grouped = useMemo(() => groupResults(shown), [shown]);
  // Keep the unfiltered chips so they stay visible, and stay countable, while a filter is on.
  const [unfiltered, setUnfiltered] = useState<{ q: string; chips: ReturnType<typeof chipsFor> } | null>(null);
  useEffect(() => {
    if (data && sources.length === 0) setUnfiltered({ q: data.q, chips: chipsFor(dedupe(data.results)) });
  }, [data, sources.length]);
  const chips = unfiltered?.q === q ? unfiltered.chips : chipsFor(shown);
  // Four chips is one row on the kiosk and two on a phone; the rest are behind one control. Eight
  // chips over four rows put the first result 553 px down a 480 px screen, before the on-screen
  // keyboard was even open.
  const [moreSources, setMoreSources] = useState(false);
  const shownChips = moreSources ? chips : chips.slice(0, CHIP_ROW);
  const hiddenChips = chips.length - shownChips.length;
  // On the kiosk the on-screen keyboard covers the bottom of the screen, so an answer that arrives
  // under it has not arrived. Scrolling the count line up instead pushed the field off the top, so
  // the screen showed "5 results." and two results with no way to see or edit what was typed. The
  // content column goes to the top: the field, the count and the first results are visible together.
  const found = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!data || data.results.length === 0) return;
    const kb = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--kb-height'));
    if (kb > 0) found.current?.closest('.content')?.scrollTo({ top: 0 });
  }, [data]);

  const toggle = (group: string[]) => {
    const on = group.every((g) => sources.includes(g));
    const next = on ? sources.filter((s) => !group.includes(s)) : [...new Set([...sources, ...group])];
    const p = new URLSearchParams(params);
    if (next.length) p.set('sources', next.join(','));
    else p.delete('sources');
    setParams(p);
  };

  const ai = status?.ai.state ?? 'off';
  const searching = Boolean(q.trim());

  return (
    <Screen title="Find" search={false} back={false} head={false}>
      <Body className="find">
        {/* Arriving with a query is arriving to read: on the kiosk an autofocused field brings the
            keyboard up over the forty results somebody came for. */}
        <SearchBar initial={q} autoFocus={!searching} placeholder="Search the box" />
        {!searching && (
          <>
            <nav className="chips find-quick" aria-label="Quick finds">
              {QUICK_FINDS.map((term) => <Link key={term} className="chip" to={`/search?q=${encodeURIComponent(term)}`}>{term}</Link>)}
            </nav>
            <p className="muted find-hint">
              Wikipedia, the NHS, the manuals, the maps and the guides. A place name or a postcode opens the map.
            </p>
            {/* The Library's four shelves, in the room under the field: an empty Find is a way in as well. */}
            <ShelfTiles label="Shelves" />
          </>
        )}
        {searching && (
          <div className="find-bar" ref={found}>
            {chips.length > 0 && (
              <div className="chips" role="group" aria-label="Filter by source">
                {shownChips.map((g) => {
                  const on = g.sources.every((x) => sources.includes(x));
                  return (
                    <button key={g.key} type="button" className={on ? 'chip active' : 'chip'} aria-pressed={on} onClick={() => toggle(g.sources)}>
                      {g.title} <span className="find-chip-count">{g.count}</span>
                    </button>
                  );
                })}
                {(hiddenChips > 0 || moreSources) && (
                  <button type="button" className="chip" aria-expanded={moreSources} onClick={() => setMoreSources((v) => !v)}>
                    {moreSources ? 'Fewer' : `More (${hiddenChips})`}
                  </button>
                )}
              </div>
            )}
            {shown.length > 0 && data && (
              <p className="muted find-count">
                {shown.length === 1 ? '1 result' : `${shown.length} results`}
                {data.query !== data.q ? ` for “${data.query}”` : ''}
              </p>
            )}
          </div>
        )}
        {data?.partial && <p className="warning">Some sources timed out, so these results may be incomplete. Try again in a moment.</p>}
        {loading && searching && <p className="muted">Searching…</p>}
        {error && <p className="warning">Search failed: {error}</p>}
        {data && !loading && shown.length === 0 && (
          <p>Nothing found for “{data.q}”. Try fewer words, or a place name or postcode for the map.</p>
        )}
        {/* The box's own guides, quick cards, modules and pages first, under their own heading: they
            are what this box was built to answer with, and the engine's one ranked list put them
            below a mirror of the NHS medicines A to Z. */}
        {grouped.map((g) => (
          <section key={g.key} className="results-group" aria-label={g.title}>
            <h2>{g.title}</h2>
            <ResultList results={g.results} label={g.title} query={data?.query || q} />
          </section>
        ))}
        {searching && data && !loading && (ai === 'ready' || ai === 'busy') && (
          <p className="find-ask" role="region" aria-label="Ask the assistant">
            <span className="muted">Not what you were after?</span>
            <Link className="btn btn-small" to={`/ai?q=${encodeURIComponent(q)}`}><Icon name="ai" size={18} /><span>Ask the assistant</span></Link>
          </p>
        )}
      </Body>
    </Screen>
  );
}
