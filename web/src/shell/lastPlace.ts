import { createContext } from 'react';

/** Where somebody was working, kept in the browser so that a kiosk browser that restarts, or a Pi that
 * reboots mid-checklist, can offer to take them back: Now shows one dismissible "Continue where you were"
 * on a cold start and never sends anybody anywhere by itself. Every access to storage is guarded; without
 * it there is simply nothing to offer. */
export const LAST_PLACE_KEY = 'sos.lastPlace';
export const LAST_PLACE_MAX_AGE_MS = 12 * 3600 * 1000;

/** The first path segments of the screens somebody works in. The front door, the board (a display), the
 * settings and the assistant (a conversation that is not resumable) are not among them. */
const WORKING_SCREENS = new Set([
  's', 'm', 'p', 'medical', 'kit', 'library', 'guides', 'map', 'radio', 'notes', 'tools', 'fieldcraft', 'doc', 'read',
  'book', 'books', 'situation', 'tasks', 'search', 'find',
]);

export type LastPlace = { path: string; at: number; title?: string };

/** `path` is a path and query in this app, as `pathname + search`. */
export function isWorthRemembering(path: string): boolean {
  if (!path.startsWith('/') || path.startsWith('//')) return false;
  const [pathname, query = ''] = path.split('?');
  const first = pathname.split('/')[1] ?? '';
  if (!WORKING_SCREENS.has(first)) return false;
  if ((first === 'search' || first === 'find') && !new URLSearchParams(query).get('q')?.trim()) return false;
  return true;
}

export function readPlace(now: number = Date.now()): LastPlace | null {
  try {
    const raw = localStorage.getItem(LAST_PLACE_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<LastPlace>;
    if (typeof p.path !== 'string' || typeof p.at !== 'number') return null;
    if (!isWorthRemembering(p.path)) return null;
    if (now - p.at >= LAST_PLACE_MAX_AGE_MS || p.at > now + 60_000) return null;
    return { path: p.path, at: p.at, title: typeof p.title === 'string' ? p.title : undefined };
  } catch {
    return null;
  }
}

/** Note that somebody is here now. The front door and transient screens leave the last place as it was. */
export function rememberPlace(path: string, now: number = Date.now()): void {
  if (!isWorthRemembering(path)) return;
  try {
    const before = readPlace(now);
    const next: LastPlace = { path, at: now, title: before?.path === path ? before.title : undefined };
    localStorage.setItem(LAST_PLACE_KEY, JSON.stringify(next));
  } catch {
    // no storage: nothing to come back to
  }
}

/** The title of the screen at `path`, so the chip can say where it goes. Only the place on record is named. */
export function noteScreenTitle(path: string, title: string, now: number = Date.now()): void {
  try {
    const before = readPlace(now);
    if (!before || before.path !== path || before.title === title) return;
    localStorage.setItem(LAST_PLACE_KEY, JSON.stringify({ ...before, title }));
  } catch {
    // no storage
  }
}

export function forgetPlace(): void {
  try {
    localStorage.removeItem(LAST_PLACE_KEY);
  } catch {
    // no storage
  }
}

/** Whether this page load has not been navigated yet: true from the first render of the shell until the
 * location changes once. The shell keeps it; Now reads it when it mounts. */
export const ColdStartContext = createContext<{ current: boolean }>({ current: false });
