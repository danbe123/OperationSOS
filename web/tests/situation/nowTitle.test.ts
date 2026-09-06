import { describe, it, expect } from 'vitest';
import { nowTitle, peacetimeTitle } from '../../src/situation/nowTitle';
import { condition, makeView } from '../fixtures/api';
import type { Conditions } from '../../src/api/types';

/** The readiness gaps say what would help most; only the cupboard says whether it is empty. */
describe('the peacetime title', () => {
  it('says everything is working when there is nothing outstanding', () => {
    const view = makeView({ readiness: { score: 100, gaps: [] } });
    expect(peacetimeTitle(view, true)).toBe('Everything is working');
    expect(nowTitle(view, true)).toBe('Everything is working');
  });

  it('says nothing is stored only when the cupboard is actually empty', () => {
    // The fixture carries the gap every household under target carries: "/plan#stock".
    expect(peacetimeTitle(makeView(), true)).toBe('Everything is working. Nothing stored yet.');
    expect(peacetimeTitle(makeView(), false)).toBe('Everything is working. Not ready yet.');
  });

  it('does not call a cupboard it has not read yet empty', () => {
    expect(peacetimeTitle(makeView(), null)).toBe('Everything is working. Not ready yet.');
    expect(peacetimeTitle(makeView())).toBe('Everything is working. Not ready yet.');
  });

  it('stays one line, whatever the cupboard says', () => {
    for (const empty of [true, false, null] as const) {
      const line = peacetimeTitle(makeView(), empty);
      expect(line).not.toContain('\n');
      expect(line.split('.').filter((part) => part.trim()).length).toBeLessThanOrEqual(2);
    }
  });
});

describe('nowTitle', () => {
  it('names what is not working before it says anything about the cupboard', () => {
    const view = makeView({ conditions: { power: condition('power', 'off') } as Conditions });
    expect(nowTitle(view, true)).toBe('Power off');
  });

  it('has no view to read', () => {
    expect(nowTitle(null, true)).toBe('Situation unknown');
  });
});
