import { isoToUkDateTime, ukDateTimeToIso } from '../tools/dates';

/** The since picker: the two answers a household gives nine times out of ten, and a typed-in time
 * for everything else. It used to offer five, and "This morning (07:00)" and "Yesterday, this time"
 * were a menu of guesses in front of the one question worth asking — a household that knows the
 * power went at half three types half three. */
export type SinceChoice = 'now' | 'hour' | 'custom';

export const SINCE_OPTIONS: { value: SinceChoice; label: string }[] = [
  { value: 'now', label: 'Just now' },
  { value: 'hour', label: 'About an hour ago' },
  { value: 'custom', label: 'Earlier' },
];

/** Turn a choice into an instant. `custom` is "dd/mm/yyyy hh:mm", read in the box's own time zone. */
export function sinceIso(choice: SinceChoice, custom = '', now: number = Date.now()): string | undefined {
  switch (choice) {
    case 'now':
      return new Date(now).toISOString();
    case 'hour':
      return new Date(now - 3_600_000).toISOString();
    case 'custom':
      return ukDateTimeToIso(custom) ?? undefined;
  }
}

/** How far a stored time may sit from one of the round answers and still be read as that answer.
 * Five minutes: a household picks "About an hour ago" and the box writes the instant it was tapped,
 * so the two are never exactly equal, but nothing further out should be dressed up as round. */
const CLOSE_ENOUGH_MS = 300_000;

/** The instant a condition carries, read back as the answer that would have produced it. The picker
 * used to open on "Just now" whatever the box had stored, so a row headed "off for 1 h" sat two
 * lines above a control saying the power went a moment ago — the screen contradicting itself at the
 * one moment nobody can afford to wonder which half is true. Anything that fits neither round answer
 * is "Earlier", and the field beside it shows the time the box has. */
export function sinceChoiceFor(stored: string | null | undefined, now: number = Date.now()): SinceChoice {
  const at = stored ? Date.parse(stored) : Number.NaN;
  if (Number.isNaN(at)) return 'now';
  let best: SinceChoice = 'custom';
  let closest = CLOSE_ENOUGH_MS;
  for (const option of ['now', 'hour'] as const) {
    const iso = sinceIso(option, '', now);
    const away = iso ? Math.abs(Date.parse(iso) - at) : Number.POSITIVE_INFINITY;
    // Ties go to the earlier answer in the list.
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
