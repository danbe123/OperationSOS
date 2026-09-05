import { describe, it, expect } from 'vitest';
import { describeElapsed, elapsedSince, phaseFor } from '../../src/tools/situation';
import { beatsSince, falloutMarks, formatCountdown, remainingSeconds } from '../../src/tools/timers';

describe('situation clock', () => {
  it('mirrors the API phases', () => {
    expect(phaseFor(0).id).toBe('right-now');
    expect(phaseFor(12 * 3600).id).toBe('first-72-hours');
    expect(phaseFor(72 * 3600).id).toBe('first-month');
    expect(phaseFor(31 * 86400).id).toBe('long-term');
  });
  it('describes elapsed time and reads a start stamp', () => {
    expect(describeElapsed(30)).toBe('just started');
    expect(describeElapsed(5 * 60)).toBe('5 min in');
    expect(describeElapsed(5 * 3600 + 10)).toBe('5 h in');
    expect(describeElapsed(3 * 86400)).toBe('3 days in');
    expect(elapsedSince('2026-09-05T10:00:00+00:00', Date.UTC(2026, 8, 5, 12))).toBe(7200);
    expect(elapsedSince('garbage', 0)).toBe(0);
  });
});

describe('timers', () => {
  it('counts down and formats', () => {
    const t = { id: 'boil', label: 'Boil', seconds: 60, endsAt: 100_000 };
    expect(remainingSeconds(t, 40_000)).toBe(60);
    expect(remainingSeconds(t, 99_100)).toBe(1);
    expect(remainingSeconds(t, 200_000)).toBe(0);
    expect(formatCountdown(59)).toBe('0:59');
    expect(formatCountdown(3661)).toBe('1:01:01');
  });
  it('counts CPR compressions at 110 a minute', () => {
    expect(beatsSince(0, 60_000)).toBe(110);
    expect(beatsSince(0, 30_000)).toBe(55);
  });
  it('lays out the fallout 7:10 marks', () => {
    const det = Date.UTC(2026, 0, 1, 12);
    const marks = falloutMarks(det, det + 8 * 3_600_000);
    expect(marks.map((m) => m.reached)).toEqual([true, false, false]);
    expect(marks[1].remainingSeconds).toBe(41 * 3600);
    expect(marks[2].factor).toBe('1/1,000');
  });
});
