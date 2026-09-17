import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { Icon } from '../icons';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import type { BookSummary } from '../api/types';
import { Screen, Body } from '../shell/Screen';

const PAGE = 40;

function useDebounced<T>(value: T, ms: number): T {
  const [slow, setSlow] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setSlow(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return slow;
}

/** The Gutenberg catalogue: the most-read books first, a search over titles and authors, and the
 * Library of Congress shelves as chips. Every card opens the book in the app's reader. */
export function Books() {
  const [typed, setTyped] = useState('');
  const q = useDebounced(typed.trim(), 300);
  const [shelf, setShelf] = useState<string | null>(null);
  const [more, setMore] = useState<BookSummary[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const shelves = useQuery(() => api.bookShelves(), []);
  const reading = useQuery(() => api.reading(), []);
  const { data, error, loading } = useQuery(
    () => api.books({ q: q || undefined, shelf: shelf ?? undefined, limit: PAGE, offset: 0 }),
    [q, shelf],
  );
  const queryKey = `${q}\u0000${shelf ?? ''}`;
  const queryKeyRef = useRef(queryKey);
  queryKeyRef.current = queryKey;
  useEffect(() => { setMore([]); }, [queryKey]);

  const items = [...(data?.items ?? []), ...more];
  const total = data?.total ?? 0;
  const showMore = async () => {
    setLoadingMore(true);
    try {
      const page = await api.books({ q: q || undefined, shelf: shelf ?? undefined, limit: PAGE, offset: items.length });
      if (queryKeyRef.current === queryKey) setMore((m) => [...m, ...page.items]); // a page for a query you have since left is dropped
    } finally {
      setLoadingMore(false);
    }
  };

  if (data && !data.available) {
    return (
      <Screen title="Books" backTo="/library">
        <Body><p className="warning">Project Gutenberg is not on this box yet. It arrives with the core content; until then the Library lists what is here.</p></Body>
      </Screen>
    );
  }
  return (
    <Screen title="Books" backTo="/library">
      <Body>
        {reading.data && reading.data.length > 0 && (
          <section aria-label="My books">
            <h2>My books</h2>
            <ul className="list items" aria-label="My books">
              {reading.data.map((r) => (
                <li key={r.key} className="item-card">
                  <div className="row">
                    {r.cover_url && <img src={r.cover_url} alt="" width={40} height={60} loading="lazy" />}
                    {r.url ? <Link to={r.url}><strong>{r.title}</strong></Link> : <strong>{r.title}</strong>}
                    {r.author && <span className="muted">{r.author}</span>}
                    <span className="muted">{Math.round(r.percent)}% read</span>
                    <button type="button" className="btn btn-small" aria-label={`Forget ${r.title}`}
                            onClick={() => void api.deleteReading(r.key).then(() => reading.refetch())}>
                      <Icon name="close" size={16} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}
        <input type="search" aria-label="Search the books" placeholder="Title or author" value={typed} onChange={(e) => setTyped(e.target.value)} />
        {shelves.data && shelves.data.length > 0 && (
          <div className="chips" role="group" aria-label="Shelves">
            {shelves.data.map((s) => (
              <button key={s.code} type="button" className={shelf === s.code ? 'chip active' : 'chip'} aria-pressed={shelf === s.code}
                      onClick={() => setShelf(shelf === s.code ? null : s.code)}>
                {s.name} ({s.count})
              </button>
            ))}
          </div>
        )}
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Could not load the books: {error}</p>}
        {data && <p className="muted">{total === 1 ? '1 book' : `${total.toLocaleString('en-GB')} books`}{q ? ` for “${q}”` : ''}</p>}
        <ul className="list items" aria-label="Books">
          {items.map((b) => (
            <li key={b.id} className="item-card">
              <Link to={`/book/gutenberg/${b.id}`} className="row">
                {b.cover_url && <img src={b.cover_url} alt="" width={40} height={60} loading="lazy" />}
                <span>
                  <strong>{b.title}</strong>
                  {b.author && <span className="muted"> — {b.author}</span>}
                  {b.shelf_name && <span className="muted"> · {b.shelf_name}</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {items.length < total && (
          <button type="button" className="btn" onClick={() => void showMore()} disabled={loadingMore}>Show more</button>
        )}
      </Body>
    </Screen>
  );
}
