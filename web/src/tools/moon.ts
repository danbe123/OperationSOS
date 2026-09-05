// Moon phase from the mean synodic month. Good to a few hours, which is all a phase name needs.
const SYNODIC_DAYS = 29.530588853;
const REFERENCE_NEW_MOON = Date.UTC(2000, 0, 6, 18, 14);   // 6 January 2000 18:14 UTC

export type MoonPhase = { ageDays: number; illumination: number; name: string; waxing: boolean };

export const PHASE_NAMES = ['New moon', 'Waxing crescent', 'First quarter', 'Waxing gibbous', 'Full moon', 'Waning gibbous', 'Last quarter', 'Waning crescent'] as const;

export function moonPhase(date: Date): MoonPhase {
  const days = (date.getTime() - REFERENCE_NEW_MOON) / 86_400_000;
  const age = ((days % SYNODIC_DAYS) + SYNODIC_DAYS) % SYNODIC_DAYS;
  const fraction = age / SYNODIC_DAYS;
  const illumination = (1 - Math.cos(2 * Math.PI * fraction)) / 2;
  // eight named phases centred on the principal points; each principal phase spans about 1.85 days either side
  const index = Math.round(fraction * 8) % 8;
  return { ageDays: Math.round(age * 10) / 10, illumination: Math.round(illumination * 100) / 100, name: PHASE_NAMES[index], waxing: fraction < 0.5 };
}
