import { describe, it, expect } from 'vitest';
import { localInput, sinceChoiceFor, sinceIso } from '../../src/situation/since';

const NOON = Date.parse('2026-09-06T12:00:00.000Z');

describe('reading a stored time back into the since picker', () => {
  it('finds the answer each of the round options would have written', () => {
    for (const choice of ['now', 'hour'] as const) {
      const stored = sinceIso(choice, '', NOON);
      expect(sinceIso(sinceChoiceFor(stored, NOON), '', NOON), choice).toBe(stored);
    }
  });

  it('allows the few minutes between choosing an answer and the box writing it down', () => {
    const fourMinutesAfterTheHour = new Date(NOON - 3_600_000 + 240_000).toISOString();
    expect(sinceChoiceFor(fourMinutesAfterTheHour, NOON)).toBe('hour');
  });

  it('calls anything else a typed-in time rather than dressing it up as a round answer', () => {
    // 08:23, which is neither an hour ago nor this moment.
    expect(sinceChoiceFor(new Date(NOON - 3 * 3_600_000 - 2_220_000).toISOString(), NOON)).toBe('custom');
    // The picker used to offer "This morning" and "Yesterday, this time"; both are now "Earlier",
    // which shows the stored time in the field rather than a round answer nobody chose.
    expect(sinceChoiceFor(new Date(NOON - 5 * 3_600_000).toISOString(), NOON)).toBe('custom');
    expect(sinceChoiceFor(new Date(NOON - 86_400_000).toISOString(), NOON)).toBe('custom');
  });

  it('opens on "just now" when the box has nothing stored', () => {
    expect(sinceChoiceFor(null, NOON)).toBe('now');
    expect(sinceChoiceFor('', NOON)).toBe('now');
    expect(sinceChoiceFor('not a time', NOON)).toBe('now');
  });

  it('writes a stored instant the way this country writes one: dd/mm/yyyy on a 24-hour clock', () => {
    const iso = '2026-09-06T09:30:00.000Z';
    const at = new Date(Date.parse(iso));
    const two = (n: number) => String(n).padStart(2, '0');
    expect(localInput(iso)).toBe(`${two(at.getDate())}/${two(at.getMonth() + 1)}/${at.getFullYear()} ${two(at.getHours())}:${two(at.getMinutes())}`);
    expect(localInput(null)).toBe('');
    expect(localInput('not a time')).toBe('');
    // and the box reads its own field back, in that order and no other
    expect(sinceIso('custom', localInput(iso))).toBe(iso);
  });
});
