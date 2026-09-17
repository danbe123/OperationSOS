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

/** The forecast items whose time has come and which nobody has been told about yet. With `pending`,
 * only items the screen once saw still counting down qualify: a consequence that is due the moment it
 * appears ("cash only" the instant the shops are tapped off) is a line on the sheet, not an alarm. */
export function dueNow(view: SituationView | null, seen: string[], now: number = Date.now(), pending?: ReadonlySet<string>): Forecast[] {
  if (!view) return [];
  return view.forecast.filter((f) => {
    const due = Date.parse(f.due_at);
    if (Number.isNaN(due) || due > now) return false;
    // Pending is by item, not by key: a countdown the screen watched still counts when its time moved.
    if (pending && !pending.has(f.id)) return false;
    return !seen.includes(reminderKey(f));
  });
}

/** The ids of the countdowns still running in this view: the ones a later view may announce. */
export function pendingIds(view: SituationView | null, now: number = Date.now()): string[] {
  if (!view) return [];
  return view.forecast.filter((f) => Date.parse(f.due_at) > now).map((f) => f.id);
}

/** What the toast says: the item, and why it matters. */
export function reminderText(item: Forecast): string {
  const head = item.severity === 'danger' ? '⚠' : '▲';
  return item.why ? `${head} ${item.title}. ${item.why}` : `${head} ${item.title}.`;
}
