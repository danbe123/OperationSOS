import { describe, it, expect } from 'vitest';
import { boardSunset, nextTasks, wantsBoard } from '../../src/situation/board';
import { condition, makeView, powerOffView, VIEW_NOW, view } from '../fixtures/api';

const NOW = Date.parse(VIEW_NOW);

describe('the board', () => {
  it('is wanted when the engine asks for it or anything is not working', () => {
    expect(wantsBoard(null)).toBe(false);
    expect(wantsBoard(view)).toBe(false);
    expect(wantsBoard(powerOffView)).toBe(true);
    expect(wantsBoard(makeView({ modes: { ...view.modes, board: true } }))).toBe(true);
    expect(wantsBoard(makeView({ conditions: { water: condition('water', 'degraded') } as never }))).toBe(true);
  });

  it('shows the next three jobs still outstanding, in the engine order', () => {
    const jobs = nextTasks(powerOffView.tasks);
    expect(jobs.map((t) => t.id)).toEqual(['fill-bath', 'freezer-shut', 'cash']);
    expect(nextTasks(powerOffView.tasks, 1).map((t) => t.id)).toEqual(['fill-bath']);
    expect(nextTasks(powerOffView.tasks.map((t) => ({ ...t, done: true })))).toEqual([]);
  });

  it('takes the sunset from the engine, and works one out when it is missing', () => {
    expect(boardSunset(view, NOW)?.toISOString()).toBe('2026-09-06T18:41:00.000Z');
    const noSun = makeView({ meta: { ...view.meta, sunset: null } });
    const computed = boardSunset(noSun, NOW);
    // the UK centre on 6 September: sunset a little before 19:00 UTC
    expect(computed).not.toBeNull();
    expect(computed!.getUTCHours()).toBe(18);
    const home = makeView({ meta: { ...view.meta, sunset: null, home: { lat: 50.93, lon: -1.43, label: 'Home', flood_zone: '3' } } });
    expect(boardSunset(home, NOW)!.getTime()).toBeLessThan(computed!.getTime());
  });
});
