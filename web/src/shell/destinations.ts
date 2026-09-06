import type { IconName } from '../icons';

export type Destination = { to: string; icon: IconName; label: string; match: (pathname: string) => boolean };

const starts = (...prefixes: string[]) => (pathname: string) => prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`));

/** The six places the box goes. The order never changes, on the rail or on the bar. */
export const DESTINATIONS: Destination[] = [
  { to: '/', icon: 'home', label: 'Now', match: (p) => p === '/' || p === '/now' || starts('/situation', '/tasks', '/board', '/plan')(p) },
  { to: '/guides', icon: 'book', label: 'Guides', match: starts('/guides', '/s', '/m', '/p', '/fieldcraft', '/radio', '/tools') },
  { to: '/kit', icon: 'boot', label: 'Kit', match: starts('/kit') },
  { to: '/medical', icon: 'medical', label: 'Medical', match: starts('/medical') },
  { to: '/map', icon: 'map', label: 'Map', match: starts('/map') },
  /* The assistant is not Find. It has its own row in the rail's footer, which lights itself, and
     with `/ai` in this list both Find and AI wore the lit style at once. */
  { to: '/search', icon: 'search', label: 'Find', match: starts('/search', '/find', '/library', '/read', '/doc') },
];

/** Which destination is lit for a path, or null when the screen belongs to none of them (System). */
export function activeDestination(pathname: string): Destination | null {
  return DESTINATIONS.find((d) => d.match(pathname)) ?? null;
}
