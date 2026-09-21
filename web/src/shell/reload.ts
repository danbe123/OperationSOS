/** How long after an automatic reload the next one is refused. */
export const RELOAD_GUARD_MS = 60_000;
const KEY = 'sos.autoReloadAt';

/** Reload the page by itself, at most once a minute: a stale bundle after an update or a fault a fresh page
 * clears is worth one reload, and a fault that a reload does not clear must show its fallback rather than
 * loop. With no way to remember that it reloaded (storage refused) it does not reload at all. */
export function reloadOnce(now: number = Date.now()): boolean {
  try {
    const last = Number(sessionStorage.getItem(KEY) ?? 0);
    if (last && now - last < RELOAD_GUARD_MS) return false;
    sessionStorage.setItem(KEY, String(now));
  } catch {
    return false;
  }
  window.location.reload();
  return true;
}
