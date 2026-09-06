import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { SearchResponse } from '../api/types';
import { useQuery } from '../api/useQuery';
import { sourceWord } from '../api/words';
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
  // Keep the unfiltered groups so the chips stay visible while a filter is on.
  const [groups, setGroups] = useState<{ q: string; groups: SearchResponse['groups'] } | null>(null);
  useEffect(() => {
    if (data && sources.length === 0) setGroups({ q: data.q, groups: data.groups });
  }, [data, sources.length]);
  const chips = groups?.q === q ? groups.groups : (data?.groups ?? []);
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

  const toggle = (source: string) => {
    const next = sources.includes(source) ? sources.filter((s) => s !== source) : [...sources, source];
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
            {chips.map((g) => (
              <button key={g.source} type="button" className={sources.includes(g.source) ? 'chip active' : 'chip'} aria-pressed={sources.includes(g.source)} onClick={() => toggle(g.source)}>
                {sourceWord(g.badge)} ({g.count})
              </button>
            ))}
          </div>
        )}
        {data?.partial && <p className="warning">Some sources timed out, so these results may be incomplete. Try again in a moment.</p>}
        {loading && q.trim() && <p className="muted">Searching…</p>}
        {error && <p className="warning">Search failed: {error}</p>}
        {data && !loading && data.results.length === 0 && (
          <p>Nothing found for “{data.q}”. Try fewer words, or a place name or postcode for the map.</p>
        )}
        {data && data.results.length > 0 && (
          <p className="muted" ref={found}>
            {data.results.length === 1 ? '1 result' : `${data.results.length} results`}
            {data.query !== data.q ? ` for “${data.query}”` : ''}.
          </p>
        )}
        {data && <ResultList results={data.results} />}

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
