import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { api } from '../api/client';
import type { SearchResponse } from '../api/types';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { ResultList } from '../components/ResultList';
import { SearchBar } from '../components/SearchBar';

export function Search() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const sourcesParam = params.get('sources') ?? '';
  const sources = sourcesParam.split(',').filter(Boolean);
  const { data, error, loading } = useQuery<SearchResponse | null>(
    () => (q.trim() ? api.search(q, { sources: sources.length ? sources : undefined }) : Promise.resolve(null)),
    [q, sourcesParam],
  );
  // Keep the unfiltered groups so chips stay visible while a filter is active.
  const [groups, setGroups] = useState<{ q: string; groups: SearchResponse['groups'] } | null>(null);
  useEffect(() => {
    if (data && sources.length === 0) setGroups({ q: data.q, groups: data.groups });
  }, [data, sources.length]);
  const chips = groups?.q === q ? groups.groups : (data?.groups ?? []);

  const toggle = (source: string) => {
    const next = sources.includes(source) ? sources.filter((s) => s !== source) : [...sources, source];
    const p = new URLSearchParams(params);
    if (next.length) p.set('sources', next.join(','));
    else p.delete('sources');
    setParams(p);
  };

  return (
    <div className="screen">
      <AppBar title="Search" search={false} />
      <div className="pad">
        <SearchBar initial={q} autoFocus />
      </div>
      {chips.length > 0 && (
        <div className="chips" role="group" aria-label="Filter by source">
          {chips.map((g) => (
            <button key={g.source} type="button" className={sources.includes(g.source) ? 'chip active' : 'chip'} aria-pressed={sources.includes(g.source)} onClick={() => toggle(g.source)}>
              {g.badge} ({g.count})
            </button>
          ))}
        </div>
      )}
      {data?.partial && <p className="pad warning">Some sources timed out; results may be incomplete. Try again in a moment.</p>}
      {loading && q.trim() && <p className="pad muted">Searching…</p>}
      {error && <p className="pad warning">Search failed: {error}</p>}
      {data && !loading && data.results.length === 0 && (
        <p className="pad">Nothing found for “{data.q}”. Try fewer words, or a place name or postcode for the map.</p>
      )}
      {data && <ResultList results={data.results} />}
      {data && data.results.length > 0 && (
        <p className="pad muted">
          {data.results.length} results in {data.took_ms} ms{data.query !== data.q ? ` (searched for “${data.query}”)` : ''}
        </p>
      )}
    </div>
  );
}
