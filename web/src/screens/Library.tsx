import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Tile } from '../components/Tile';
import { Icon } from '../icons';
import { Screen, Body } from '../shell/Screen';
import { BookGrid, ContinueReading } from './Books';
import { TOOL_TILES } from './Tools';
import './books.css';

/** The Library is the box's whole bookshelf, as four shelves a household can tell apart at a glance:
 * the medical shelf first (999, the quick cards, the NHS), then the guides the box wrote itself, the
 * books it carries to read, and the sources it searches. Each shelf is its own page; the tiles sit
 * on the kiosk without scrolling, and under them ("the library has space under the tiles we should
 * be using") are the books the household is in the middle of and the most-read of the collection. */
export function Library() {
  const cardsQ = useQuery(() => api.cards(), []);
  const pagesQ = useQuery(() => api.pages(), []);
  const booksQ = useQuery(() => api.books({ limit: 12 }), []);
  const libQ = useQuery(() => api.library(), []);
  const reading = useQuery(() => api.reading(), []);
  const forget = (key: string) => void api.deleteReading(key).then(() => reading.refetch());
  const pageCount = pagesQ.data?.length ?? 0;
  const items = libQ.data?.categories.flatMap((c) => c.items) ?? [];
  const medicalLine = cardsQ.data ? `999, ${cardsQ.data.length} quick cards, the NHS A to Z, children's doses` : '999, the quick cards, the NHS A to Z';
  const guidesLine = pagesQ.data ? `${pageCount} pages and ${TOOL_TILES.length} tools, written for this box` : 'The manual this box wrote itself';
  const booksLine = booksQ.data
    ? (booksQ.data.available ? `${booksQ.data.total.toLocaleString('en-GB')} books to read, Project Gutenberg` : 'Project Gutenberg is not on this box yet')
    : 'Novels, histories, classics to read';
  const sourcesLine = libQ.data
    ? `Wikipedia, the NHS, manuals, maps: ${items.length} sources, ${items.filter((i) => i.available).length} on this box`
    : 'Wikipedia, the NHS, manuals, maps';
  return (
    <Screen title="Library" back={false}>
      <Body>
        <nav className="tiles tiles-wide" aria-label="Shelves">
          <Tile to="/library/medical" icon="medical" title="Medical" subtitle={medicalLine} big />
          <Tile to="/library/guides" icon="book" title="Guides" subtitle={guidesLine} big />
          <Tile to="/library/books" icon="library" title="Books" subtitle={booksLine} big disabled={booksQ.data ? !booksQ.data.available : false} />
          <Tile to="/library/sources" icon="globe" title="Sources" subtitle={sourcesLine} big />
        </nav>
        {reading.data && reading.data.length > 0 && <ContinueReading entries={reading.data} onForget={forget} />}
        {booksQ.data?.available && booksQ.data.items.length > 0 && (
          <section aria-label="Most read">
            <div className="books-head">
              <h2>Most read</h2>
              <Link className="btn btn-quiet btn-small" to="/library/books?all=1">All {booksQ.data.total.toLocaleString('en-GB')} books <Icon name="forward" size={18} /></Link>
            </div>
            <BookGrid items={booksQ.data.items} label="Most read" />
          </section>
        )}
      </Body>
    </Screen>
  );
}
