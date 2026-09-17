import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { LibraryItemCard } from '../components/LibraryItemCard';
import { Icon } from '../icons';
import { Screen, Body } from '../shell/Screen';

export function Library() {
  const { data, error, loading } = useQuery(() => api.library(), []);
  const shelf = useQuery(() => api.reading(), []);
  const location = useLocation();
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    if (!data || !location.hash) return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' });
  }, [data, location.hash]);

  const all = data?.categories.flatMap((c) => c.items) ?? [];
  const shown = data?.categories.filter((c) => !filter || c.id === filter) ?? [];

  return (
    <Screen title="Library">
      <Body>
        {loading && <p className="muted">Loading the library…</p>}
        {error && <p className="warning">Library unavailable: {error}</p>}
        {data && (
          <>
            <p className="muted">{all.length} items, {all.filter((i) => i.available).length} available on this box.</p>
            {shelf.data && shelf.data.length > 0 && (
              <section aria-label="My books">
                <h2>My books</h2>
                <ul className="list items" aria-label="My books">
                  {shelf.data.map((r) => (
                    <li key={r.key} className="item-card">
                      <div className="row">
                        {r.cover_url && <img src={r.cover_url} alt="" width={40} height={60} loading="lazy" />}
                        {r.url ? <Link to={r.url}><strong>{r.title}</strong></Link> : <strong>{r.title}</strong>}
                        {r.author && <span className="muted">{r.author}</span>}
                        <span className="muted">{Math.round(r.percent)}% read</span>
                        <button type="button" className="btn btn-small" aria-label={`Forget ${r.title}`}
                                onClick={() => void api.deleteReading(r.key).then(() => shelf.refetch())}>
                          <Icon name="close" size={16} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}
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
