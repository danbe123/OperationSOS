import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { SearchResponse } from '../api/types';
import { useQuery } from '../api/useQuery';
import { chipsFor, dedupe } from '../api/results';
import { Icon } from '../icons';
import { ResultList } from '../components/ResultList';
import { SearchBar } from '../components/SearchBar';
import { ShelfTiles } from '../components/ShelfTiles';
import { Screen, Body } from '../shell/Screen';
import { useWide } from '../shell/useWide';
import { ThemeButton } from '../theme/ThemeButton';
import './find.css';

/** How many source chips stand on the screen before the rest go behind "More sources". */
export const CHIP_ROW = 4;

/** What a household reaches for first: one tap each, before the keyboard. */
export const QUICK_FINDS = ['CPR', 'Bleeding', 'Burns', 'Water', 'Power cut', 'Hypothermia', 'Radio', 'Iodine'];

/** Find: the field first, and nothing above it. Before a search, the handful of things people look
 * for most as one-tap chips; after one, the source chips with the count, then one list of results in
 * the engine's order, the box's own and the library's together. No heading, no paragraph: the rail says
 * Find, and the row they took was a row of results on the kiosk. */
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
  // One row per target, in the engine's order, and the chips counted from the very rows below them.
  const shown = useMemo(() => (data ? dedupe(data.results) : []), [data]);
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

  // No head, so no theme button in it: on a phone, where the rail's footer is not drawn, it rides beside the field.
  const wide = useWide();
  const ai = status?.ai.state ?? 'off';
  const searching = Boolean(q.trim());

  return (
    <Screen title="Find" search={false} back={false} head={false}>
      <Body className="find">
        {/* Arriving with a query is arriving to read: on the kiosk an autofocused field brings the
            keyboard up over the forty results somebody came for. */}
        <div className="find-top">
          <SearchBar initial={q} autoFocus={!searching} placeholder="Search the box" />
          {!wide && <ThemeButton />}
        </div>
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
        {/* One list, by relevance. The box's own rows used to stand in a group of their own above the
            library's, from when the engine ranked the box's Severe bleeding card below a mirror of the NHS
            medicines A to Z; the engine keeps the cards and the medicine a query names in its first three
            itself now, and the group put twelve of the box's weak rows ("broke my toe": Economic collapse,
            Tools and repair) above the library's fracture pages. */}
        {shown.length > 0 && (
          <section className="results-group" aria-label="Results">
            <ResultList results={shown} label="Results" query={data?.query || q} />
          </section>
        )}
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
