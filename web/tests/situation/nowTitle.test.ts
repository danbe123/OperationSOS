import { describe, it, expect } from 'vitest';
import { nowTitle, peacetimeTitle } from '../../src/situation/nowTitle';
import { condition, makeView } from '../fixtures/api';
import type { Conditions } from '../../src/api/types';

/** In peacetime the heading is one fact about the services and nothing else. The box no longer
 * scores a household or counts its cupboard, so there is no second half to the sentence. */
describe('the peacetime title', () => {
  it('says everything is working, in one line, with nothing added', () => {
    expect(peacetimeTitle()).toBe('Everything is working');
    expect(nowTitle(makeView())).toBe('Everything is working');
    expect(peacetimeTitle()).not.toContain('\n');
    expect(peacetimeTitle()).not.toMatch(/ready|stored|register/i);
  });
});

describe('nowTitle', () => {
  it('names what is not working', () => {
    const view = makeView({ conditions: { power: condition('power', 'off') } as Conditions });
    expect(nowTitle(view)).toBe('Power off');
  });

  it('has no view to read', () => {
    expect(nowTitle(null)).toBe('Situation unknown');
  });
});
