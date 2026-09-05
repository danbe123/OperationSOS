import type { Note, SituationView } from '../api/types';

export type DrillSummary = { elapsed_s: number; done: number; total: number; events: Note[]; scenario: string | null };

/** What the household did in the drill: how far the clock ran, how many jobs were ticked, and the last
 * few things the log recorded. Taken from the View as it stood when the drill ended, so it is exact. */
export function drillSummary(view: SituationView, events: Note[], count = 5): DrillSummary {
  const started = view.scenario ? Date.parse(view.scenario.started_at) : Number.NaN;
  const since = Number.isNaN(started) ? events : events.filter((e) => Date.parse(e.updated_at) >= started);
  return {
    elapsed_s: view.scenario?.elapsed_s ?? 0,
    done: view.tasks.filter((t) => t.done).length,
    total: view.tasks.length,
    events: since.slice(0, count),
    scenario: view.scenario?.title ?? null,
  };
}
