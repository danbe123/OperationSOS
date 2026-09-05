// Timer arithmetic kept apart from the screen and the audio so it can be tested with a fake clock.

export type TimerPreset = { id: string; label: string; seconds: number; note?: string };

export const PRESETS: TimerPreset[] = [
  { id: 'boil', label: 'Boil water', seconds: 60, note: 'A rolling boil for one minute makes water safe to drink.' },
  { id: 'med-4h', label: 'Next dose in 4 hours', seconds: 4 * 3600 },
  { id: 'med-6h', label: 'Next dose in 6 hours', seconds: 6 * 3600 },
];

export type RunningTimer = { id: string; label: string; endsAt: number; seconds: number };

export function remainingSeconds(timer: RunningTimer, now: number): number {
  return Math.max(0, Math.ceil((timer.endsAt - now) / 1000));
}

export function formatCountdown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const mm = m.toString().padStart(2, '0');
  const ss = s.toString().padStart(2, '0');
  return h ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

export const CPR_BPM = 110;

/** The number of beats that have elapsed since the metronome started, so a display can count compressions. */
export function beatsSince(startedAt: number, now: number, bpm = CPR_BPM): number {
  return Math.max(0, Math.floor(((now - startedAt) / 60_000) * bpm));
}

/** The fallout 7:10 rule: for every sevenfold increase in time since detonation the dose rate falls tenfold. */
export const FALLOUT_MARKS = [
  { label: '7 hours', hours: 7, factor: '1/10' },
  { label: '49 hours (2 days)', hours: 49, factor: '1/100' },
  { label: '2 weeks', hours: 343, factor: '1/1,000' },
] as const;

export function falloutMarks(detonationAt: number, now: number) {
  return FALLOUT_MARKS.map((m) => {
    const at = detonationAt + m.hours * 3_600_000;
    return { ...m, at, reached: now >= at, remainingSeconds: Math.max(0, Math.ceil((at - now) / 1000)) };
  });
}
