import { describe, it, expect } from 'vitest';
import {
  chipDuration, countdown, describeDuration, HOME_CONDITION_IDS, secondsUntil, SEVERITY_SYMBOL,
  STATE_LABEL, STATE_SYMBOL, STATE_TONE,
} from '../../src/situation/conditions';
import { briefingHref, contentHref } from '../../src/situation/links';
import { sinceIso } from '../../src/situation/since';
import { withCondition, withTask } from '../../src/situation/apply';
import { condition, makeView, powerOffView } from '../fixtures/api';

describe('condition chips', () => {
  it('gives each state a colour and a symbol, never colour alone', () => {
    expect(STATE_TONE).toEqual({ working: 'ok', degraded: 'warn', off: 'danger' });
    expect(STATE_SYMBOL.working).toBe('✓');
    expect(STATE_SYMBOL.degraded).toBe('▲');
    expect(STATE_SYMBOL.off).toBe('✕');
    expect(new Set(Object.values(STATE_SYMBOL)).size).toBe(3);
    expect(STATE_LABEL.degraded).toBe('patchy');
    expect(SEVERITY_SYMBOL.danger).toBe('⚠');
  });

  it('says how long only while something is wrong', () => {
    expect(chipDuration('working', 7200)).toBe('');
    expect(chipDuration('off', 7200)).toBe('for 2 h');
    expect(chipDuration('degraded', 300)).toBe('for 5 min');
    expect(chipDuration('off', 20)).toBe('just now');
  });

  it('shows the five household conditions on Home', () => {
    expect(HOME_CONDITION_IDS).toEqual(['power', 'water', 'mobile', 'landline', 'internet']);
  });
});

describe('durations and countdowns', () => {
  it('words a duration the way the clock does', () => {
    expect(describeDuration(30)).toBe('under a minute');
    expect(describeDuration(300)).toBe('5 min');
    expect(describeDuration(3600)).toBe('1 h');
    expect(describeDuration(47 * 3600)).toBe('47 h');
    expect(describeDuration(50 * 3600)).toBe('2 days');
    expect(describeDuration(24 * 3600 * 8)).toBe('8 days');
  });

  it('counts down to a due time and says when one has passed', () => {
    const now = Date.parse('2026-09-06T14:00:00Z');
    expect(countdown('2026-09-06T18:00:00Z', now)).toBe('in 4 h');
    expect(countdown('2026-09-06T14:20:00Z', now)).toBe('in 20 min');
    expect(countdown('2026-09-06T14:00:30Z', now)).toBe('due in under a minute');
    expect(countdown('2026-09-06T12:30:00Z', now)).toBe('passed 1 h ago');
    expect(secondsUntil('2026-09-06T15:00:00Z', now)).toBe(3600);
  });
});

describe('links', () => {
  it('resolves the content link scheme the rules use', () => {
    expect(contentHref('module:water')).toBe('/m/water');
    expect(contentHref('page:no-phones')).toBe('/p/no-phones');
    expect(contentHref('card:cpr-adult')).toBe('/medical/card/cpr-adult');
    expect(contentHref('/plan#stock')).toBe('/plan#stock');
    expect(contentHref('')).toBeNull();
  });

  it('opens a briefing entry at the right place', () => {
    expect(briefingHref({ title: 'Right now', kind: 'playbook-section', ref: 'grid-collapse#right-now' })).toBe('/s/grid-collapse#right-now');
    expect(briefingHref({ title: 'Power', kind: 'module', ref: 'power' })).toBe('/m/power');
    expect(briefingHref({ title: 'NRR', kind: 'doc', ref: 'nrr-2025' })).toBe('/doc/nrr-2025');
    expect(briefingHref({ title: 'Grid collapse', kind: 'playbook', ref: 'grid-collapse' })).toBe('/s/grid-collapse');
    expect(briefingHref({ title: 'The map', kind: 'map', ref: '' })).toBe('/map');
  });
});

describe('the since picker', () => {
  const now = Date.parse('2026-09-06T14:00:00Z');
  it('turns a choice into an instant', () => {
    expect(sinceIso('now', '', now)).toBe('2026-09-06T14:00:00.000Z');
    expect(sinceIso('hour', '', now)).toBe('2026-09-06T13:00:00.000Z');
    expect(sinceIso('custom', 'not a time', now)).toBeUndefined();
    expect(sinceIso('custom', '06/09/2026 09:30', now)).toBe(new Date('2026-09-06T09:30').toISOString());
  });
});

describe('optimistic updates', () => {
  it('puts a saved task back in the View', () => {
    const done = { ...powerOffView.tasks[0], done: true };
    expect(withTask(powerOffView, done).tasks[0].done).toBe(true);
    expect(withTask(powerOffView, done).tasks).toHaveLength(powerOffView.tasks.length);
  });

  it('takes the answered proposal away when its condition is set', () => {
    const view = makeView({ inferred: powerOffView.inferred });
    const next = withCondition(view, condition('mobile', 'off'));
    expect(next.conditions.mobile.state).toBe('off');
    expect(next.inferred).toEqual([]);
  });
});
