import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Tile } from './Tile';
import { TOOL_TILES } from '../screens/Tools';

/** The Library's four shelves as tiles, each saying what is on it: the Library's front, and the same
 * four under Find before anything is searched, so an empty Find is a way into the shelves too. */
export function ShelfTiles({ label = 'Shelves' }: { label?: string } = {}) {
  const cardsQ = useQuery(() => api.cards(), []);
  const pagesQ = useQuery(() => api.pages(), []);
  const booksQ = useQuery(() => api.books({ limit: 1 }), []);
  const libQ = useQuery(() => api.library(), []);
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
    <nav className="tiles tiles-wide" aria-label={label}>
      <Tile to="/library/medical" icon="medical" title="Medical" subtitle={medicalLine} big />
      <Tile to="/library/guides" icon="book" title="Guides" subtitle={guidesLine} big />
      <Tile to="/library/books" icon="library" title="Books" subtitle={booksLine} big disabled={booksQ.data ? !booksQ.data.available : false} />
      <Tile to="/library/sources" icon="globe" title="Sources" subtitle={sourcesLine} big />
    </nav>
  );
}
