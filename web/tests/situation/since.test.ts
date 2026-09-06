import { describe, it, expect } from 'vitest';
import { localInput, sinceChoiceFor, sinceIso } from '../../src/situation/since';

const NOON = Date.parse('2026-09-06T12:00:00.000Z');

describe('reading a stored time back into the since picker', () => {
  it('finds the answer each of the four options would have written', () => {
    // Compared as instants rather than by name: in a time zone where 07:00 falls on the hour under
    // test two answers name the same moment, and either of them is a true reading of what is stored.
    for (const choice of ['now', 'hour', 'morning', 'yesterday'] as const) {
      const stored = sinceIso(choice, '', NOON);
      expect(sinceIso(sinceChoiceFor(stored, NOON), '', NOON), choice).toBe(stored);
    }
  });

  it('allows the few minutes between choosing an answer and the box writing it down', () => {
    const fourMinutesAfterTheHour = new Date(NOON - 3_600_000 + 240_000).toISOString();
    expect(sinceChoiceFor(fourMinutesAfterTheHour, NOON)).toBe('hour');
  });

  it('calls anything else a typed-in time rather than dressing it up as a round answer', () => {
    // 08:23, which is neither an hour ago, nor 07:00 in any time zone, nor this time yesterday.
    expect(sinceChoiceFor(new Date(NOON - 3 * 3_600_000 - 2_220_000).toISOString(), NOON)).toBe('custom');
  });

  it('opens on "just now" when the box has nothing stored', () => {
    expect(sinceChoiceFor(null, NOON)).toBe('now');
    expect(sinceChoiceFor('', NOON)).toBe('now');
    expect(sinceChoiceFor('not a time', NOON)).toBe('now');
  });

  it('writes a stored instant into a datetime field in the box’s own time zone', () => {
    const iso = '2026-09-06T09:30:00.000Z';
    const at = new Date(Date.parse(iso));
    const two = (n: number) => String(n).padStart(2, '0');
    expect(localInput(iso)).toBe(`${at.getFullYear()}-${two(at.getMonth() + 1)}-${two(at.getDate())}T${two(at.getHours())}:${two(at.getMinutes())}`);
    expect(localInput(null)).toBe('');
    expect(localInput('not a time')).toBe('');
  });
});
