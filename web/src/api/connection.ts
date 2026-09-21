import { useSyncExternalStore } from 'react';

/** Whether the box is answering, and what to do when it is not.
 *
 * sos-api restarts by itself (systemd, about three seconds), Caddy stays up in front of it and answers
 * 502 while it does, and the kiosk browser keeps its page. So an outage is usually short and the screen the
 * household is on must simply carry on and catch up: every request reports here, a failed one starts a slow,
 * growing probe of /api/status, and the first answer tells every mounted query to read again. The probe is
 * the only retry loop there is; it backs off to one ask every fifteen seconds, so a box that is really gone
 * costs nothing. Nothing on this page throws the screen away. */

/** Pauses between probes while the box is not answering; the last one repeats. */
export const PROBE_DELAYS_MS = [1000, 2000, 4000, 8000, 15_000];
const JITTER = 0.2;

/** A network failure (status 0) or a gateway error from Caddy: the box did not answer. The API saying no
 * (a 404, a 409, a 500, or its own JSON 503) is an answer. */
export function isConnectionError(e: unknown): boolean {
  if (typeof e !== 'object' || e === null || !('status' in e)) return false;
  return (e as { status: unknown }).status === 0 || (e as { gateway?: unknown }).gateway === true;
}

let down = false;
let downSince = 0;
let probeTimer: number | undefined;
let probeCount = 0;
const changed = new Set<() => void>();
const back = new Set<() => void>();
let listening = false;

function emit(): void {
  changed.forEach((l) => l());
}

export function isDown(): boolean {
  return down;
}

/** When the current outage began (ms since the epoch), or null while the box is answering. */
export function downSinceMs(): number | null {
  return down ? downSince : null;
}

function schedule(): void {
  window.clearTimeout(probeTimer);
  const base = PROBE_DELAYS_MS[Math.min(probeCount, PROBE_DELAYS_MS.length - 1)];
  probeCount += 1;
  const delay = Math.round(base * (1 + (Math.random() * 2 - 1) * JITTER));
  probeTimer = window.setTimeout(() => void probe(), delay);
}

async function probe(): Promise<void> {
  if (!down) return;
  try {
    const res = await fetch('/api/status', { cache: 'no-store', headers: { Accept: 'application/json' } });
    if (res.ok) {
      reportSuccess();
      return;
    }
  } catch {
    // still not answering
  }
  if (down) schedule();
}

function onWindowBack(): void {
  if (!down) return;
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
  window.clearTimeout(probeTimer);
  void probe();
}

function listen(): void {
  if (listening || typeof window === 'undefined') return;
  listening = true;
  window.addEventListener('focus', onWindowBack);
  document.addEventListener('visibilitychange', onWindowBack);
  window.addEventListener('online', onWindowBack);
}

/** A request failed: if that was the box not answering, note it and start looking for it. */
export function reportFailure(e: unknown): void {
  if (!isConnectionError(e) || down) return;
  down = true;
  downSince = Date.now();
  probeCount = 0;
  listen();
  emit();
  schedule();
}

/** The box answered. If it had not been, everybody who asked to hear of it is told, once. */
export function reportSuccess(): void {
  if (!down) return;
  down = false;
  window.clearTimeout(probeTimer);
  probeTimer = undefined;
  emit();
  [...back].forEach((cb) => cb());
}

/** Run `cb` whenever the box comes back after not answering. Returns the way to stop listening. */
export function onReconnect(cb: () => void): () => void {
  back.add(cb);
  return () => { back.delete(cb); };
}

function subscribe(cb: () => void): () => void {
  changed.add(cb);
  return () => { changed.delete(cb); };
}

/** True while the box is not answering. */
export function useBoxDown(): boolean {
  return useSyncExternalStore(subscribe, isDown, () => false);
}

export function resetConnectionForTests(): void {
  window.clearTimeout(probeTimer);
  probeTimer = undefined;
  down = false;
  downSince = 0;
  probeCount = 0;
  back.clear();
  changed.clear();
}
