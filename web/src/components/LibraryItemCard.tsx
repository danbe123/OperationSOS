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

export function LibraryItemCard({ item }: { item: LibraryItem }) {
  const open = itemOpenPath(item);
  const isFile = item.kind === 'mwm' || item.kind === 'apk';
  const meta = `${formatBytes(item.size_bytes)}${item.as_at ? `, copied ${item.as_at}` : ''}.${item.licence ? ` Licence: ${item.licence}.` : ''}`;
  return (
    <li className={item.available ? 'item-card' : 'item-card unavailable'} id={`item-${item.id}`}>
      <div className="row">
        <Icon name={KIND_ICON[item.kind] ?? 'drive'} />
        <strong>{item.title}</strong>
        <Badge>{sourceWord(item.kind)}</Badge>
        <Badge tone={item.available ? 'default' : 'warn'}>{item.drive_label}</Badge>
      </div>
      {item.description && <p className="muted">{item.description}</p>}
      <p className="muted">{meta}</p>
      {open ? (
        isFile ? <a className="btn" href={open} download>Download</a> : <Link className="btn btn-primary" to={open}>Open</Link>
      ) : (
        <span className="btn" aria-disabled="true">{item.available ? 'Used by the box' : 'Not available'}</span>
      )}
    </li>
  );
}
