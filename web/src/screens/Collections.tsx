import { useEffect, useState } from 'react';
import { useLocation } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { LibraryItemCard } from '../components/LibraryItemCard';
import { Screen, Body } from '../shell/Screen';

/** The Collections shelf of the Library: every ZIM, document and map pack the box carries, by category. */
export function Collections() {
  const { data, error, loading } = useQuery(() => api.library(), []);
  const location = useLocation();
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    if (!data || !location.hash) return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' });
  }, [data, location.hash]);

  const all = data?.categories.flatMap((c) => c.items) ?? [];
  const shown = data?.categories.filter((c) => !filter || c.id === filter) ?? [];

  return (
    <Screen title="Collections" backTo="/library">
      <Body>
        {loading && <p className="muted">Loading the library…</p>}
        {error && <p className="warning">Library unavailable: {error}</p>}
        {data && (
          <>
            <p className="muted">{all.length} items, {all.filter((i) => i.available).length} available on this box.</p>
            <div className="chips" role="group" aria-label="Categories">
              {data.categories.map((c) => (
                <button key={c.id} type="button" className={filter === c.id ? 'chip active' : 'chip'} aria-pressed={filter === c.id} onClick={() => setFilter(filter === c.id ? null : c.id)}>
                  {c.title} ({c.items.length})
                </button>
              ))}
            </div>
            {shown.map((c) => (
              <section key={c.id} aria-label={c.title}>
                <h2 id={`cat-${c.id}`}>{c.title}</h2>
                <ul className="list items" aria-label={c.title}>
                  {c.items.map((item) => <LibraryItemCard key={item.id} item={item} />)}
                </ul>
              </section>
            ))}
          </>
        )}
      </Body>
    </Screen>
  );
}
