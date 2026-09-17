import type { IconName } from '../icons';

export type Destination = { to: string; icon: IconName; label: string; match: (pathname: string) => boolean };

const starts = (...prefixes: string[]) => (pathname: string) => prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`));

/** The five places the box goes. The order never changes, on the rail or on the bar. The Library is the
 * box's whole bookshelf: the medical shelf (999, the quick cards, the NHS), the guides it wrote itself,
 * the books being read, and the sources it searches. Medical had a row of its own on the rail; the owner:
 * "medical should live in library". */
export const DESTINATIONS: Destination[] = [
  /* `starts` matches a path and everything under it, so the screens Now leads to — the situation,
     the jobs, the board and what has been written down — light Now rather than nothing. */
  { to: '/', icon: 'home', label: 'Now', match: (p) => p === '/' || p === '/now' || starts('/situation', '/tasks', '/board', '/notes')(p) },
  { to: '/library', icon: 'library', label: 'Library', match: starts('/library', '/guides', '/s', '/m', '/p', '/fieldcraft', '/radio', '/tools', '/read', '/doc', '/books', '/book', '/medical') },
  { to: '/kit', icon: 'boot', label: 'Kit', match: starts('/kit') },
  { to: '/map', icon: 'map', label: 'Map', match: starts('/map') },
  /* The assistant is not Find. It has its own row in the rail's footer, which lights itself, and
     with `/ai` in this list both Find and AI wore the lit style at once. */
  { to: '/search', icon: 'search', label: 'Find', match: starts('/search', '/find') },
];

/** Which destination is lit for a path, or null when the screen belongs to none of them (System). */
export function activeDestination(pathname: string): Destination | null {
  return DESTINATIONS.find((d) => d.match(pathname)) ?? null;
}
