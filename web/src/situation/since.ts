import { isoToUkDateTime, ukDateTimeToIso } from '../tools/dates';

/** The since picker: four sensible answers to "when did this start?" plus a typed-in time. */
export type SinceChoice = 'now' | 'hour' | 'morning' | 'yesterday' | 'custom';

export const SINCE_OPTIONS: { value: SinceChoice; label: string }[] = [
  { value: 'now', label: 'Just now' },
  { value: 'hour', label: '1 hour ago' },
  { value: 'morning', label: 'This morning (07:00)' },
  { value: 'yesterday', label: 'Yesterday, this time' },
  { value: 'custom', label: 'Choose a time…' },
];

/** Turn a choice into an instant. `custom` is "dd/mm/yyyy hh:mm", read in the box's own time zone. */
export function sinceIso(choice: SinceChoice, custom = '', now: number = Date.now()): string | undefined {
  const at = new Date(now);
  switch (choice) {
    case 'now':
      return at.toISOString();
    case 'hour':
      return new Date(now - 3_600_000).toISOString();
    case 'morning': {
      const morning = new Date(at.getFullYear(), at.getMonth(), at.getDate(), 7, 0, 0, 0);
      // before 07:00 the morning has not happened yet: mean yesterday morning
      if (morning.getTime() > now) morning.setDate(morning.getDate() - 1);
      return morning.toISOString();
    }
    case 'yesterday':
      return new Date(now - 86_400_000).toISOString();
    case 'custom':
      return ukDateTimeToIso(custom) ?? undefined;
  }
}

/** How far a stored time may sit from one of the four answers and still be read as that answer.
 * Five minutes: a household picks "1 hour ago" and the box writes the instant it was tapped, so the
 * two are never exactly equal, but nothing further out should be dressed up as a round answer. */
const CLOSE_ENOUGH_MS = 300_000;

/** The instant a condition carries, read back as the answer that would have produced it. The picker
 * used to open on "Just now" whatever the box had stored, so a row headed "off for 1 h" sat two
 * lines above a control saying the power went a moment ago — the screen contradicting itself at the
 * one moment nobody can afford to wonder which half is true. Anything that fits none of the four
 * answers is the typed-in time, and the field beside it shows what the box has. */
export function sinceChoiceFor(stored: string | null | undefined, now: number = Date.now()): SinceChoice {
  const at = stored ? Date.parse(stored) : Number.NaN;
  if (Number.isNaN(at)) return 'now';
  let best: SinceChoice = 'custom';
  let closest = CLOSE_ENOUGH_MS;
  for (const option of ['now', 'hour', 'morning', 'yesterday'] as const) {
    const iso = sinceIso(option, '', now);
    const away = iso ? Math.abs(Date.parse(iso) - at) : Number.POSITIVE_INFINITY;
    // Ties go to the earlier answer in the list, so 07:00 exactly is "just now" at 07:00.
    if (away < closest) {
      closest = away;
      best = option;
    }
  }
  return best;
}

/** An instant as the box asks for it and shows it: "06/09/2026 03:12", British order, 24-hour, in
 * the box's own time zone. */
export function localInput(iso: string | null | undefined): string {
  return isoToUkDateTime(iso);
}
