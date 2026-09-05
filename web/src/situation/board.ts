// What the board shows, worked out without React so it can be tested with a fixed clock.
import type { SituationView, StockItem, Task } from '../api/types';
import { sunTimes } from '../tools/sun';

/** The kiosk falls back to the board rather than a dim screen when the engine asks for it,
 * or whenever a service is not working: a dark screen is no use to a household mid-outage. */
export function wantsBoard(view: SituationView | null): boolean {
  if (!view) return false;
  if (view.modes.board) return true;
  return Object.values(view.conditions).some((c) => c.state !== 'working');
}

/** The next few jobs, in the engine's order, skipping anything already ticked. */
export function nextTasks(tasks: Task[], count = 3): Task[] {
  return tasks.filter((t) => !t.done).slice(0, count);
}

/** The centre of Great Britain: what the sun line falls back to when no home is set. */
export const UK_CENTRE = { lat: 54.5, lon: -3.5 };

/** Tonight's sunset: the engine's if it sent one, otherwise worked out here for the home or the UK centre. */
export function boardSunset(view: SituationView | null, now: number = Date.now()): Date | null {
  if (view?.meta.sunset) {
    const t = Date.parse(view.meta.sunset);
    if (!Number.isNaN(t)) return new Date(t);
  }
  const home = view?.meta.home;
  const lat = home?.lat ?? UK_CENTRE.lat;
  const lon = home?.lon ?? UK_CENTRE.lon;
  const times = sunTimes(lat, lon, new Date(now));
  return times.polar === null ? times.sunset : null;
}

/** The shortest run of each stock category, the way the plan screen counts it. */
export function stockDays(items: StockItem[]): { category: string; days: number }[] {
  const out = new Map<string, number>();
  for (const i of items) {
    if (i.days_left === null) continue;
    const current = out.get(i.category);
    if (current === undefined || i.days_left < current) out.set(i.category, i.days_left);
  }
  const order = ['water', 'food', 'medicine', 'fuel', 'other'];
  return [...out.entries()]
    .map(([category, days]) => ({ category, days }))
    .sort((a, b) => order.indexOf(a.category) - order.indexOf(b.category));
}
