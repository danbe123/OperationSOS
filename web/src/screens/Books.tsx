import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Icon } from '../icons';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import type { BookShelf, BookSummary, ReadingEntry } from '../api/types';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import './books.css';

const PAGE = 40;          // a page of a shelf or a search
const FRONT = 12;         // the most-read books on the front of the shelf
const FRONT_SHELVES = 12; // the shelves with tiles on the front; the rest wait behind "All shelves"

/** One icon per Library of Congress shelf, for its tile. A shelf with no icon of its own reads as a book. */
export const SHELF_ICONS: Record<string, string> = {
  PS: 'book', PR: 'book', PZ: 'child', D: 'globe', B: 'brain', A: 'library', Q: 'atom', E: 'flag', F: 'map',
  H: 'people', T: 'tools', PQ: 'book', G: 'mountain', N: 'pin', PN: 'book', PT: 'book', S: 'wheat', R: 'medical',
  Z: 'library', M: 'speaker', C: 'clock', J: 'flag', L: 'book', PA: 'book', U: 'shield', K: 'lock', V: 'wave',
};

function useDebounced<T>(value: T, ms: number): T {
  const [slow, setSlow] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setSlow(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return slow;
}

const count = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n.toLocaleString('en-GB')} ${many}`);

/** A cover, or a drawn spine with the title on it when there is none (or the file is missing). */
function Cover({ title, url, percent }: { title: string; url: string | null; percent?: number }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => { setBroken(false); }, [url]);
  return (
    <span className="book-cover">
      {url && !broken
        ? <img src={url} alt="" loading="lazy" onError={() => setBroken(true)} />
        : <span className="book-spine" aria-hidden="true"><span>{title}</span></span>}
      {percent !== undefined && (
        <span className="book-progress" aria-hidden="true"><span style={{ width: `${Math.max(2, Math.min(100, percent))}%` }} /></span>
      )}
    </span>
  );
}

/** One book as a card: its cover, its title and its author, the whole of it a link into the reader. */
function BookCard({ to, title, author, cover, percent, meta, action }: {
  to: string; title: string; author?: string | null; cover: string | null; percent?: number; meta?: string; action?: ReactNode;
}) {
  return (
    <li className="book-card">
      <Link to={to} className="book-card-link">
        <Cover title={title} url={cover} percent={percent} />
        <span className="book-card-title">{title}</span>
        {author && <span className="book-card-author">{author}</span>}
        {meta && <span className="book-card-meta">{meta}</span>}
      </Link>
      {action}
    </li>
  );
}

export function BookGrid({ items, label }: { items: BookSummary[]; label: string }) {
  return (
    <ul className="book-grid" aria-label={label}>
      {items.map((b) => <BookCard key={b.id} to={`/book/gutenberg/${b.id}`} title={b.title} author={b.author} cover={b.cover_url} />)}
    </ul>
  );
}

/** The books a household is in the middle of, most recent first, each opening where it was left. */
export function ContinueReading({ entries, onForget }: { entries: ReadingEntry[]; onForget: (key: string) => void }) {
  return (
    <section aria-label="Continue reading">
      <div className="books-head"><h2>Continue reading</h2></div>
      <ul className="book-strip" aria-label="Continue reading">
        {entries.map((r) => (
          <BookCard key={r.key} to={r.url ?? '/library/books'} title={r.title} author={r.author} cover={r.cover_url}
                    percent={r.percent} meta={`${Math.round(r.percent)}% read`}
                    action={(
                      <button type="button" className="btn btn-small book-forget" aria-label={`Forget ${r.title}`} title="Forget this book" onClick={() => onForget(r.key)}>
                        <Icon name="close" size={18} />
                      </button>
                    )} />
        ))}
      </ul>
    </section>
  );
}

/** The Gutenberg shelf of the Library. The front of it: the books you are reading, one search, the
 * shelves as tiles and the most-read books as covers. Behind a tile or a search: that shelf, as a
 * grid of covers, most-read first or A to Z, a page at a time. */
export function Books() {
  const [params, setParams] = useSearchParams();
  const shelf = params.get('shelf') ?? '';
  const q = (params.get('q') ?? '').trim();
  const sort = params.get('sort') === 'title' ? 'title' : 'popular';
  const listing = Boolean(shelf || q || params.get('all'));
  const [typed, setTyped] = useState(q);
  const slow = useDebounced(typed.trim(), 300);
  useEffect(() => {
    if (slow === q) return;
    setParams((p) => {
      const next = new URLSearchParams(p);
      if (slow) next.set('q', slow); else next.delete('q');
      return next;
    }, { replace: true });
  }, [slow, q, setParams]);

  const shelves = useQuery(() => api.bookShelves(), []);
  const reading = useQuery(() => api.reading(), []);
  const [allShelves, setAllShelves] = useState(false);
  const [more, setMore] = useState<BookSummary[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const { data, error, loading } = useQuery(
    () => api.books({ q: q || undefined, shelf: shelf || undefined, sort, limit: listing ? PAGE : FRONT, offset: 0 }),
    [q, shelf, sort, listing],
  );
  const queryKey = [q, shelf, sort].join('|');
  const queryKeyRef = useRef(queryKey);
  queryKeyRef.current = queryKey;
  useEffect(() => { setMore([]); }, [queryKey]);

  const items = [...(data?.items ?? []), ...more];
  const total = data?.total ?? 0;
  const showMore = async () => {
    setLoadingMore(true);
    try {
      const page = await api.books({ q: q || undefined, shelf: shelf || undefined, sort, limit: PAGE, offset: items.length });
      if (queryKeyRef.current === queryKey) setMore((m) => [...m, ...page.items]); // a page for a query you have since left is dropped
    } finally {
      setLoadingMore(false);
    }
  };
  const forget = (key: string) => void api.deleteReading(key).then(() => reading.refetch());
  const withParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    return `?${next.toString()}`;
  };

  if (data && !data.available) {
    return (
      <Screen title="Books" backTo="/library" search={false}>
        <Body><p className="warning">Project Gutenberg is not on this box yet. It arrives with the core content; until then the Library lists what is here.</p></Body>
      </Screen>
    );
  }

  const shelfName = shelves.data?.find((s) => s.code === shelf)?.name ?? (shelf ? 'Shelf' : '');
  const title = q ? 'Search the books' : shelf ? shelfName : listing ? 'Most read' : 'Books';
  const searchBox = (
    <div className="books-search">
      <input type="search" aria-label="Search the books" placeholder="Title or author" value={typed} onChange={(e) => setTyped(e.target.value)} />
    </div>
  );
  const status = (
    <>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="warning">Could not load the books: {error}</p>}
    </>
  );

  if (listing) {
    return (
      <Screen title={title} backTo="/library/books" search={false}>
        <Body>
          {searchBox}
          <div className="books-head">
            {data && <p className="books-count muted">{count(total, 'book', 'books')}{q ? ` for “${q}”` : ''}{shelf && q ? ` on ${shelfName}` : ''}</p>}
            <div className="row" role="group" aria-label="Order">
              <Link className={sort === 'popular' ? 'btn btn-small active' : 'btn btn-small'} aria-current={sort === 'popular' ? 'page' : undefined} to={withParam('sort', null)}>Most read</Link>
              <Link className={sort === 'title' ? 'btn btn-small active' : 'btn btn-small'} aria-current={sort === 'title' ? 'page' : undefined} to={withParam('sort', 'title')}>A to Z</Link>
            </div>
          </div>
          {status}
          <BookGrid items={items} label="Books" />
          {items.length < total && (
            <button type="button" className="btn" onClick={() => void showMore()} disabled={loadingMore}>Show more</button>
          )}
        </Body>
      </Screen>
    );
  }

  const shown: BookShelf[] = shelves.data ? (allShelves ? shelves.data : shelves.data.slice(0, FRONT_SHELVES)) : [];
  return (
    <Screen title="Books" backTo="/library" search={false}>
      <Body>
        {reading.data && reading.data.length > 0 && <ContinueReading entries={reading.data} onForget={forget} />}
        {searchBox}
        {shelves.data && shelves.data.length > 0 && (
          <section aria-label="Shelves">
            <div className="books-head">
              <h2>Shelves</h2>
              {shelves.data.length > FRONT_SHELVES && (
                <button type="button" className="btn btn-quiet btn-small" aria-expanded={allShelves} onClick={() => setAllShelves((v) => !v)}>
                  {allShelves ? 'Fewer shelves' : `All ${shelves.data.length} shelves`}
                </button>
              )}
            </div>
            <nav className="tiles" aria-label="Shelves">
              {shown.map((s) => (
                <Tile key={s.code} to={`/library/books?shelf=${encodeURIComponent(s.code)}`} icon={SHELF_ICONS[s.code] ?? 'book'} title={s.name} subtitle={count(s.count, 'book', 'books')} />
              ))}
            </nav>
          </section>
        )}
        <section aria-label="Most read">
          <div className="books-head">
            <h2>Most read</h2>
            {data && <Link className="btn btn-quiet btn-small" to="/library/books?all=1">All {total.toLocaleString('en-GB')} books <Icon name="forward" size={18} /></Link>}
          </div>
          {status}
          <BookGrid items={items} label="Most read" />
        </section>
      </Body>
    </Screen>
  );
}
