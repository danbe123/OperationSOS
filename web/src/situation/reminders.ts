// Forecast reminders: the box says so when a countdown runs out while somebody is looking at it,
// once per item, whichever screen is open.
import type { Forecast, SituationView } from '../api/types';

export const SEEN_KEY = 'sos.forecastSeen';
const KEEP = 40;

/** An item is the one it is at the time it was due: a rescheduled countdown is announced again. */
export function reminderKey(item: Forecast): string {
  return `${item.id}@${item.due_at}`;
}

export function readSeen(storage: Storage): string[] {
  try {
    const raw = storage.getItem(SEEN_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

export function writeSeen(storage: Storage, keys: string[]): void {
  try {
    storage.setItem(SEEN_KEY, JSON.stringify(keys.slice(-KEEP)));
  } catch {
    // storage is optional; the reminder simply repeats after a reload
  }
}

/** The forecast items whose time has come and which nobody has been told about yet. */
export function dueNow(view: SituationView | null, seen: string[], now: number = Date.now()): Forecast[] {
  if (!view) return [];
  return view.forecast.filter((f) => {
    const due = Date.parse(f.due_at);
    if (Number.isNaN(due) || due > now) return false;
    return !seen.includes(reminderKey(f));
  });
}

/** What the toast says: the item, and why it matters. */
export function reminderText(item: Forecast): string {
  const head = item.severity === 'danger' ? '⚠' : '▲';
  return item.why ? `${head} ${item.title}. ${item.why}` : `${head} ${item.title}.`;
}
