import { useEffect, useState } from 'react';
import type { Note, SituationView } from '../api/types';

export type DrillSummary = { elapsed_s: number; done: number; total: number; events: Note[]; scenario: string | null };

/** The engine writes its own "Drill ended: 0 tasks done in 120 minutes" line into the log. The
 * debrief counts the same thing from the View, so printing both put two disagreeing counts of one
 * fact side by side, in two formats. The debrief says it once and drops the engine's line. */
const OWN_LINE = /^Drill ended\b/i;

/** What the household did in the drill: how far the clock ran, how many jobs were ticked, and the last
 * few things the log recorded. Taken from the View as it stood when the drill ended, so it is exact. */
export function drillSummary(view: SituationView, events: Note[], count = 5): DrillSummary {
  const started = view.scenario ? Date.parse(view.scenario.started_at) : Number.NaN;
  const since = Number.isNaN(started) ? events : events.filter((e) => Date.parse(e.updated_at) >= started);
  return {
    elapsed_s: view.scenario?.elapsed_s ?? 0,
    done: view.tasks.filter((t) => t.done).length,
    total: view.tasks.length,
    events: since.filter((e) => !OWN_LINE.test(e.title)).slice(0, count),
    scenario: view.scenario?.title ?? null,
  };
}

type Listener = (s: DrillSummary) => void;
const listeners = new Set<Listener>();

/** The drill is ended from the band, and the debrief is a panel under it: the two are in different
 * parts of the shell, so the summary travels the same way a notice does. */
export function publishDrillSummary(summary: DrillSummary): void {
  listeners.forEach((l) => l(summary));
}

export function useDrillSummary(): [DrillSummary | null, () => void] {
  const [summary, setSummary] = useState<DrillSummary | null>(null);
  useEffect(() => {
    const listener: Listener = (s) => setSummary(s);
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, []);
  return [summary, () => setSummary(null)];
}
