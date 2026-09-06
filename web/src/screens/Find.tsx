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
import { Screen, Body } from '../shell/Screen';

/** Find: one search across everything, then the library behind it, then the assistant when it is on. */
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
  const libQ = useQuery(() => api.library(), []);
  // One row per target, the box's own first, and the chips counted from the very rows below them.
  const shown = useMemo(() => (data ? dedupe(data.results) : []), [data]);
  const grouped = useMemo(() => groupResults(shown), [shown]);
  // Keep the unfiltered chips so they stay visible, and stay countable, while a filter is on.
  const [unfiltered, setUnfiltered] = useState<{ q: string; chips: ReturnType<typeof chipsFor> } | null>(null);
  useEffect(() => {
    if (data && sources.length === 0) setUnfiltered({ q: data.q, chips: chipsFor(groupResults(dedupe(data.results))) });
  }, [data, sources.length]);
  const chips = unfiltered?.q === q ? unfiltered.chips : chipsFor(grouped);
  // On the kiosk the on-screen keyboard covers the bottom of the screen, so an answer that arrives
  // under it has not arrived. Scrolling the count line up instead pushed the field off the top, so
  // the screen showed "5 results." and two results with no way to see or edit what was typed. The
  // content column goes to the top: the field, the count and the first results are visible together.
  const found = useRef<HTMLParagraphElement>(null);
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

  const categories = libQ.data?.categories ?? [];
  const all = categories.flatMap((c) => c.items);
  const ai = status?.ai.state ?? 'off';

  return (
    <Screen title="Find" search={false} back={false}>
      <Body>
        <SearchBar initial={q} autoFocus />
        {!q.trim() && <p className="muted">Search Wikipedia, the NHS pages, the manuals, the maps and the guides. A place name or a postcode opens the map.</p>}
        {chips.length > 0 && (
          <div className="chips" role="group" aria-label="Filter by source">
            {chips.map((g) => {
              const on = g.sources.every((x) => sources.includes(x));
              return (
                <button key={g.key} type="button" className={on ? 'chip active' : 'chip'} aria-pressed={on} onClick={() => toggle(g.sources)}>
                  {g.title} ({g.count})
                </button>
              );
            })}
          </div>
        )}
        {data?.partial && <p className="warning">Some sources timed out, so these results may be incomplete. Try again in a moment.</p>}
        {loading && q.trim() && <p className="muted">Searching…</p>}
        {error && <p className="warning">Search failed: {error}</p>}
        {data && !loading && shown.length === 0 && (
          <p>Nothing found for “{data.q}”. Try fewer words, or a place name or postcode for the map.</p>
        )}
        {shown.length > 0 && data && (
          <p className="muted" ref={found}>
            {shown.length === 1 ? '1 result' : `${shown.length} results`}
            {data.query !== data.q ? ` for “${data.query}”` : ''}.
          </p>
        )}
        {/* The box's own guides, quick cards, modules and pages first, under their own heading: they
            are what this box was built to answer with, and the engine's one ranked list put them
            below a mirror of the NHS medicines A to Z. */}
        {grouped.map((g) => (
          <section key={g.key} className="results-group" aria-label={g.title}>
            <h2>{g.title}</h2>
            <ResultList results={g.results} label={g.title} />
          </section>
        ))}

        {(ai === 'ready' || ai === 'busy') && (
          <section className="panel" aria-label="The assistant">
            <div className="panel-head"><h2>Ask the assistant</h2></div>
            <p className="muted">It answers only from the library on this box, and shows the pages it used.</p>
            <p><Link className="btn" to="/ai"><Icon name="ai" size={18} /><span>Open the assistant</span></Link></p>
          </section>
        )}

        <section aria-label="The library">
          <h2>Browse the library</h2>
          {libQ.loading && <p className="muted">Loading the library…</p>}
          {libQ.error && <p className="warning">Library unavailable: {libQ.error}</p>}
          {libQ.data && (
            <>
              <p className="muted">{all.length} items, {all.filter((i) => i.available).length} available on this box.</p>
              <div className="chips" role="group" aria-label="Library categories">
                {categories.map((c) => (
                  <Link key={c.id} className="chip" to={`/library#cat-${c.id}`}>{c.title} ({c.items.length})</Link>
                ))}
              </div>
              <p><Link className="btn" to="/library"><Icon name="library" size={18} /><span>Open the library</span></Link></p>
            </>
          )}
        </section>
      </Body>
    </Screen>
  );
}
