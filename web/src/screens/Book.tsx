import { Navigate, useLocation, useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { useTheme } from '../theme/ThemeProvider';
import { EpubReader } from './Doc';
import { useRecordView } from '../reader/recent';

/** One Gutenberg book, read in the app's own EPUB reader straight out of the ZIM. A book the scraper
 * shipped without an EPUB (a few hundred, mostly scans and music) goes to the Kiwix page instead. */
export function Book() {
  const { id = '' } = useParams();
  const { theme } = useTheme();
  // Back returns to the shelf or the search the book was opened from; only a book opened by a deep
  // link, with nothing behind it, goes to the front of the Books instead.
  const backTo = useLocation().key === 'default' ? '/library/books' : undefined;
  const { data, error, loading } = useQuery(() => api.book(id), [id]);
  useRecordView(data?.available ? { key: `gutenberg:${data.id}`, kind: 'book', title: data.title, url: `/book/gutenberg/${data.id}`, coverUrl: data.cover_url } : null);
  if (loading) return <Screen title="Book" search={false} backTo={backTo}><Body><p className="muted">Opening…</p></Body></Screen>;
  if (error || !data) {
    return <Screen title="Book" search={false} backTo={backTo}><Body><p className="warning">Could not open this book: {error ?? 'not found'}</p></Body></Screen>;
  }
  if (!data.available) {
    return <Screen title={data.title} search={false} backTo={backTo}><Body><p className="warning">Project Gutenberg is not on this box yet.</p></Body></Screen>;
  }
  if (!data.epub_url) return <Navigate to={data.html_url ?? '/books'} replace />;
  return (
    <Screen title={data.title} search={false} fill backTo={backTo}>
      <EpubReader
        url={data.epub_url}
        theme={theme}
        leading={data.author ? <span className="muted">{data.author}</span> : undefined}
        memory={{ key: `gutenberg:${data.id}`, title: data.title, author: data.author, coverUrl: data.cover_url, startCfi: data.position?.cfi ?? null }}
      />
    </Screen>
  );
}
