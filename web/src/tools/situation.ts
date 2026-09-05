// Mirror of sos.situation.PHASES so the clock can advance between polls.
const HOUR = 3600;
export const PHASES: { limit: number | null; id: 'right-now' | 'first-72-hours' | 'first-month' | 'long-term'; title: string }[] = [
  { limit: 12 * HOUR, id: 'right-now', title: 'Right now' },
  { limit: 72 * HOUR, id: 'first-72-hours', title: 'First 72 hours' },
  { limit: 30 * 24 * HOUR, id: 'first-month', title: 'First month' },
  { limit: null, id: 'long-term', title: 'Long term' },
];

export function phaseFor(elapsedSeconds: number) {
  return PHASES.find((p) => p.limit === null || elapsedSeconds < p.limit) ?? PHASES[PHASES.length - 1];
}

export function describeElapsed(seconds: number): string {
  if (seconds < 60) return 'just started';
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min in`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h} h in`;
  return `${Math.floor(h / 24)} days in`;
}

export function elapsedSince(startedAt: string, now: number = Date.now()): number {
  const t = Date.parse(startedAt);
  return Number.isNaN(t) ? 0 : Math.max(0, Math.floor((now - t) / 1000));
}
