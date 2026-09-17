import { useEffect } from 'react';
import { Navigate, useLocation, useParams } from 'react-router';
import { api } from '../api/client';
import type { LibraryItem } from '../api/types';
import { useQuery } from '../api/useQuery';
import { LibraryItemCard } from '../components/LibraryItemCard';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';

/** One icon per category of source, as the Library's other tiles have theirs. */
export const CATEGORY_ICONS: Record<string, string> = {
  'uk-official': 'flag', medical: 'medical', survival: 'fire', reference: 'globe', practical: 'tools',
  maps: 'map', education: 'book', books: 'library', media: 'speaker', ai: 'ai', playbooks: 'plan',
};

/** A catalogue title cut to the part a tile has room for: what comes before the colon, the bracket or
 * the dash, so "NHS website: conditions, symptoms, medicines" reads "NHS website". */
export function shortTitle(title: string): string {
  return title.split(/[:(—–]| - /)[0].trim();
}

/** The line under a category tile: how many sources it holds and two of them by name, the shortest
 * names first so the tile stays two or three lines on the kiosk. */
export function categoryLine(items: LibraryItem[]): string {
  const onBox = items.filter((i) => i.available).length;
  const short = items.map((i) => shortTitle(i.title));
  const names = [...short].sort((a, b) => a.length - b.length).slice(0, 2).sort((a, b) => short.indexOf(a) - short.indexOf(b));
  const rest = items.length - names.length;
  const count = items.length === 1 ? '1 source' : `${items.length} sources`;
  const have = onBox === items.length ? '' : `, ${onBox} on this box`;
  return `${count}${have}: ${names.join(', ')}${rest > 0 ? ` and ${rest} more` : ''}`;
}

/** The Sources shelf of the Library: what the box searches, one tile per kind, each naming what is
 * in it. Two hundred cards in one scroll told nobody anything; ten tiles do. */
export function Sources() {
  const { data, error, loading } = useQuery(() => api.library(), []);
  return (
    <Screen title="Sources" backTo="/library">
      <Body>
        {loading && <p className="muted">Loading the library…</p>}
        {error && <p className="warning">Library unavailable: {error}</p>}
        {data && (
          <nav className="tiles" aria-label="Kinds of source">
            {data.categories.map((c) => (
              <Tile key={c.id} to={`/library/sources/${c.id}`} icon={CATEGORY_ICONS[c.id] ?? 'drive'} title={c.title} subtitle={categoryLine(c.items)} />
            ))}
          </nav>
        )}
      </Body>
    </Screen>
  );
}

/** One kind of source: its cards, and a scroll to the one named in the hash. */
export function SourceCategory() {
  const { category = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.library(), []);
  const location = useLocation();
  const group = data?.categories.find((c) => c.id === category);

  useEffect(() => {
    if (!group || !location.hash) return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' });
  }, [group, location.hash]);

  if (data && !group) return <Navigate to="/library/sources" replace />;
  return (
    <Screen title={group?.title ?? 'Sources'} backTo="/library/sources">
      <Body>
        {loading && <p className="muted">Loading the library…</p>}
        {error && <p className="warning">Library unavailable: {error}</p>}
        {group && (
          <>
            <p className="muted">{categoryLine(group.items).split(':')[0]}.</p>
            <ul className="list items" aria-label={group.title}>
              {group.items.map((item) => <LibraryItemCard key={item.id} item={item} />)}
            </ul>
          </>
        )}
      </Body>
    </Screen>
  );
}
