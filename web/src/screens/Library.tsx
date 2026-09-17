import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import { TOOL_TILES } from './Tools';

/** The Library is the box's whole bookshelf, as three shelves a household can tell apart at a glance:
 * the guides the box wrote itself, the books it carries to read, and the sources it searches.
 * Each shelf is its own page; the hub stays short enough to sit on the kiosk without scrolling. */
export function Library() {
  const pagesQ = useQuery(() => api.pages(), []);
  const booksQ = useQuery(() => api.books({ limit: 1 }), []);
  const libQ = useQuery(() => api.library(), []);
  const pageCount = pagesQ.data?.length ?? 0;
  const items = libQ.data?.categories.flatMap((c) => c.items) ?? [];
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
          <Tile to="/library/guides" icon="book" title="Guides" subtitle={guidesLine} big />
          <Tile to="/library/books" icon="library" title="Books" subtitle={booksLine} big disabled={booksQ.data ? !booksQ.data.available : false} />
          <Tile to="/library/sources" icon="globe" title="Sources" subtitle={sourcesLine} big />
        </nav>
      </Body>
    </Screen>
  );
}
