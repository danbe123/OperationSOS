// Shared vocabulary for the situation engine: what each condition is called, how a chip looks,
// and the words for a duration or a countdown. Kept free of React so tests can call it directly.
import { CONDITION_IDS, type ConditionId, type ConditionState, type Severity, type TaskBucket } from '../api/types';

export { CONDITION_IDS };
export type { ConditionId, ConditionState };

/** The five the household sees on Home; the sheet shows all ten. */
export const HOME_CONDITION_IDS: ConditionId[] = ['power', 'water', 'mobile', 'landline', 'internet'];

export const CONDITION_INFO: Record<ConditionId, { title: string; short: string; icon: string }> = {
  power: { title: 'Mains power', short: 'Power', icon: 'bolt' },
  water: { title: 'Water supply', short: 'Water', icon: 'drop' },
  mobile: { title: 'Mobile network', short: 'Mobile', icon: 'wifi' },
  landline: { title: 'Landline and 999', short: 'Landline', icon: 'phone' },
  internet: { title: 'Internet', short: 'Internet', icon: 'globe' },
  gas: { title: 'Gas', short: 'Gas', icon: 'fire' },
  heating: { title: 'Heating', short: 'Heating', icon: 'thermometer' },
  roads: { title: 'Roads and transport', short: 'Roads', icon: 'truck' },
  shops: { title: 'Shops and cash', short: 'Shops', icon: 'coins' },
  sewage: { title: 'Sewage and drains', short: 'Sewage', icon: 'wave' },
};

export const STATE_LABEL: Record<ConditionState, string> = { working: 'working', degraded: 'patchy', off: 'off' };

/** The word for a service's state as a household says it: the power is on or off, the roads and the
 * shops are open or closed. `STATE_LABEL` stays for prose that wants "working". */
export function stateWord(id: ConditionId, state: ConditionState): string {
  if (state === 'degraded') return 'patchy';
  const opens = id === 'roads' || id === 'shops';
  if (state === 'working') return opens ? 'open' : 'on';
  return opens ? 'closed' : 'off';
}

/* ── The box's symbols. One meaning each, everywhere, and never the only signal: a colour always has
   a symbol beside it and a symbol always has a word.

     ✓  done, working, in hand
     ▲  patchy, or something to keep an eye on — a caution short of danger
     ✕  off, gone, or nothing found
     ⚠  a warning: something that can hurt you, or that has already gone wrong
     ⚑  a drill, and nothing else
     ℹ  a note the box is adding
     ▸ ▾  a disclosure, and nothing else

   ⚠ used to do eight jobs — danger, the drill chip, the engine-down line, the Timers tile, "AI can be
   wrong", the empty-form hint "Enter the child's age", the OpenStreetMap caveat and the "passed"
   marker in Coming up — which is the same as doing none. */
export const STATE_SYMBOL: Record<ConditionState, string> = { working: '✓', degraded: '▲', off: '✕' };
export const STATE_TONE: Record<ConditionState, 'ok' | 'warn' | 'danger'> = { working: 'ok', degraded: 'warn', off: 'danger' };

/* A forecast that has already fallen due is not "off": the fridge food is unsafe now, which is a
   warning. */
export const SEVERITY_SYMBOL: Record<Severity, string> = { info: 'ℹ', warn: '▲', danger: '⚠', passed: '⚠' };
export const SEVERITY_TONE: Record<Severity, 'default' | 'warn' | 'danger'> = { info: 'default', warn: 'warn', danger: 'danger', passed: 'danger' };

export const BUCKET_TITLE: Record<TaskBucket, string> = { now: 'Right now', hour: 'Within the hour', today: 'Today', week: 'This week' };
export const BUCKET_ORDER: TaskBucket[] = ['now', 'hour', 'today', 'week'];

const MINUTE = 60;
const HOUR = 3600;
const DAY = 86_400;

/** "5 min", "5 h", "2 days" - the same words the clock uses. */
export function describeDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < MINUTE) return 'under a minute';
  if (s < HOUR) return `${Math.floor(s / MINUTE)} min`;
  if (s < 2 * DAY) return `${Math.floor(s / HOUR)} h`;
  const days = Math.floor(s / DAY);
  return `${days} ${days === 1 ? 'day' : 'days'}`;
}

/** The band's short form: "4 h", "just now". The compact chip has no room for the word "for", and
 * the duration is the number the band exists to carry. */
export function shortDuration(state: ConditionState, forSeconds: number): string {
  if (state === 'working') return '';
  return forSeconds < MINUTE ? 'just now' : describeDuration(forSeconds);
}

/** The chip's second line: nothing while a condition works, "for 5 h" once it does not. */
export function chipDuration(state: ConditionState, forSeconds: number): string {
  if (state === 'working') return '';
  return forSeconds < MINUTE ? 'just now' : `for ${describeDuration(forSeconds)}`;
}

/** How long a condition has been as it is, counted from the instant the box stored rather than from
 * a `for_s` the engine worked out when it last answered. The board tile said "off for 5 h" beside a
 * clock reading 06:12 and a log line reading "since 00:00": two statements of one fact an hour
 * apart. Everything on the screen now counts from the same `since`, on the box's own clock. */
export function elapsedFrom(condition: { since: string | null; for_s: number }, now: number = Date.now()): number {
  const at = condition.since ? Date.parse(condition.since) : Number.NaN;
  return Number.isNaN(at) ? condition.for_s : Math.max(0, Math.round((now - at) / 1000));
}

/** The same second line, counted from the stored instant. */
export function sinceDuration(condition: { state: ConditionState; since: string | null; for_s: number }, now: number = Date.now()): string {
  return chipDuration(condition.state, elapsedFrom(condition, now));
}

/** How long until a forecast item falls due, in words. Past items say so. */
export function countdown(dueAt: string, now: number = Date.now()): string {
  const due = Date.parse(dueAt);
  if (Number.isNaN(due)) return '';
  const seconds = Math.round((due - now) / 1000);
  if (seconds <= 0) return `passed ${describeDuration(-seconds)} ago`;
  if (seconds < MINUTE) return 'due in under a minute';
  return `in ${describeDuration(seconds)}`;
}

export function secondsUntil(dueAt: string, now: number = Date.now()): number {
  const due = Date.parse(dueAt);
  return Number.isNaN(due) ? Number.POSITIVE_INFINITY : Math.round((due - now) / 1000);
}

/** A time of day for the "set by" and bulletin lines. */
export function clockTime(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  return new Date(t).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

/** How long ago something was read or written, in words: the age on a sensor row or an event. */
export function ago(iso: string, now: number = Date.now()): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const seconds = Math.round((now - t) / 1000);
  if (seconds < MINUTE) return 'just now';
  return `${describeDuration(seconds)} ago`;
}
