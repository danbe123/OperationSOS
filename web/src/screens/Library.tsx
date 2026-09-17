import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { Screen, Body } from '../shell/Screen';
import { ShelfTiles } from '../components/ShelfTiles';
import { Strip } from '../components/Strip';
import { KIND_ICON, KIND_WORD } from '../reader/recent';
import type { RecentEntry } from '../api/types';
import { BookCard } from './Books';
import './books.css';

/** The Library is the box's whole bookshelf, as four shelves a household can tell apart at a glance:
 * the medical shelf first (999, the quick cards, the NHS), then the guides the box wrote itself, the
 * books it carries to read, and the sources it searches. Each shelf is its own page; the tiles sit
 * on the kiosk without scrolling, and under them is one strip: the last things anyone on the box
 * opened, whatever shelf they came from ("we need aggregated last viewed across all library items only"). */
export function Library() {
  const recent = useQuery(() => api.recent(12), [], { refetchOnFocus: true });
  return (
    <Screen title="Library" back={false}>
      <Body>
        <ShelfTiles />
        {recent.data && recent.data.length > 0 && <LastViewed entries={recent.data} />}
      </Body>
    </Screen>
  );
}

/** A thing opened lately, as a card in the strip: a book by its cover; anything else by the icon of
 * what it is, its title, and the word for it. */
function RecentCard({ entry }: { entry: RecentEntry }) {
  if (entry.kind === 'book') return <BookCard to={entry.url} title={entry.title} cover={entry.cover_url} meta={KIND_WORD.book} />;
  return (
    <li className="book-card">
      <Link to={entry.url} className="book-card-link">
        <span className="book-cover recent-cover"><Icon name={KIND_ICON[entry.kind]} size={34} /></span>
        <span className="book-card-title">{entry.title}</span>
        <span className="book-card-meta">{KIND_WORD[entry.kind]}</span>
      </Link>
    </li>
  );
}

function LastViewed({ entries }: { entries: RecentEntry[] }) {
  return (
    <section aria-label="Last viewed">
      <div className="books-head"><h2>Last viewed</h2></div>
      <Strip label="Last viewed">
        {entries.map((e) => <RecentCard key={e.key} entry={e} />)}
      </Strip>
    </section>
  );
}
