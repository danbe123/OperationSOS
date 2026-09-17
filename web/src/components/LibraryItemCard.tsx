import { Link } from 'react-router';
import type { LibraryItem } from '../api/types';
import { Icon } from '../icons';
import { sourceWord } from '../api/words';
import { Badge } from './Badge';

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v < 10 ? v.toFixed(1) : Math.round(v)} ${units[i]}`;
}

export const KIND_ICON: Record<string, string> = {
  zim: 'globe', pdf: 'pdf', epub: 'book', pmtiles: 'map', geojson: 'map', style: 'map', glyphs: 'map', sprites: 'map',
  places: 'map', mwm: 'phone', apk: 'phone', model: 'ai', dir: 'drive',
};

/** Where "Open" goes for an item, by kind; null when it cannot be opened in the app. */
export function itemOpenPath(item: LibraryItem): string | null {
  if (!item.available) return null;
  switch (item.kind) {
    case 'zim':
      return item.url;
    case 'pdf':
    case 'epub':
      return `/doc/${item.id}`;
    case 'pmtiles':
    case 'geojson':
    case 'style':
    case 'glyphs':
    case 'sprites':
    case 'places':
      return '/map';
    case 'mwm':
    case 'apk':
      return item.url;
    default:
      return null;
  }
}

/** What an absent item's card says instead of a button: why it is not here and what brings it. */
export function absentLine(item: LibraryItem): string {
  switch (item.fetch) {
    case 'download': return 'Not on this box yet.';
    case 'drive': return 'On the external drive. Plug it in and it appears.';
    case 'build': return `Made on a PC with sos ${item.build_tool ?? 'build'} and copied here.`;
    case 'own': return 'Your own files: copy them onto the drive and they appear.';
    default: return 'Not available.';
  }
}

/** One source, as a card: what it is, how big and how old, and one action — Open when it is here,
 * "Get it" when the box can fetch it itself, otherwise a line saying what brings it. `onFetch` is the
 * page's PIN-gated fetch; without it the card only says the item is not here. */
export function LibraryItemCard({ item, onFetch, fetching = false }: { item: LibraryItem; onFetch?: (id: string) => void; fetching?: boolean }) {
  const open = itemOpenPath(item);
  const isFile = item.kind === 'mwm' || item.kind === 'apk';
  /* What a household needs to know about a file is how big it is and how old it is. The licence is
     the box's own paperwork and belongs on the About page, not on every row of a medical shelf. */
  const meta = `${formatBytes(item.size_bytes)}${item.as_at ? `, copied ${item.as_at}` : ''}.`;
  const canFetch = !item.available && item.fetch === 'download' && Boolean(onFetch);
  return (
    <li className={item.available ? 'item-card' : 'item-card unavailable'} id={`item-${item.id}`}>
      <div className="item-card-head">
        <Icon name={KIND_ICON[item.kind] ?? 'drive'} size={22} />
        <strong className="item-card-title">{item.title}</strong>
      </div>
      {item.description && <p className="muted item-card-desc">{item.description}</p>}
      <div className="item-card-foot">
        <span className="item-card-meta">
          <Badge>{sourceWord(item.kind)}</Badge>
          <Badge tone={item.available ? 'default' : 'warn'}>{item.drive_label}</Badge>
          <span className="muted">{meta}</span>
        </span>
        {open ? (
          isFile ? <a className="btn btn-small" href={open} download>Download</a> : <Link className="btn btn-small btn-primary" to={open}>Open</Link>
        ) : item.available ? (
          <span className="btn btn-small" aria-disabled="true">Used by the box</span>
        ) : canFetch ? (
          <button type="button" className="btn btn-small btn-primary" disabled={fetching} onClick={() => onFetch?.(item.id)}>
            <Icon name="down" size={16} /><span>{fetching ? 'Getting it…' : `Get it (${formatBytes(item.size_bytes)})`}</span>
          </button>
        ) : null}
      </div>
      {!item.available && !fetching && <p className="muted item-card-absent">{absentLine(item)}</p>}
      {fetching && <p className="muted item-card-absent">Downloading. It appears here when it is done; the System screen shows the progress.</p>}
    </li>
  );
}
