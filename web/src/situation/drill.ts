import { useEffect, useState } from 'react';
import type { Note, SituationView } from '../api/types';

export type DrillSummary = {
  elapsed_s: number;
  done: number;
  total: number;
  events: Note[];
  scenario: string | null;
};

/** The engine writes its own "Drill ended: 0 tasks done in 120 minutes" line into the log. The
 * debrief counts the same thing from the View, so printing both put two disagreeing counts of one
 * fact side by side, in two formats. The debrief says it once and drops the engine's line. */
const OWN_LINE = /^Drill ended\b/i;
/** The engine tags everything that happened inside a drill. A debrief headed "What happened in the
 * drill" that lists a real water supply coming back on is not a debrief, it is a lie about the
 * household's own morning. */
const IN_DRILL = /\(drill\)\s*$/i;
const DRILL_START = /^Drill started\b/i;

/** When this drill actually began, in wall-clock time. It is not `scenario.started_at`: a drill may
 * be started "2 days ago" so the guidance shows the right phase, and counting from that would count
 * two days of the household's real work as practice. The log's own "Drill started" line is the
 * moment somebody pressed the button. */
export function drillStartedAt(events: Note[]): number | null {
  const times = events.filter((e) => DRILL_START.test(e.title)).map((e) => Date.parse(e.updated_at)).filter((n) => !Number.isNaN(n));
  return times.length ? Math.max(...times) : null;
}

/** What the household did in the drill: how far the clock ran, how many jobs were ticked while it
 * was running, and the drill's own log. Anything that was already ticked an hour before the drill
 * started belongs to the real day, and is not counted here. */
export function drillSummary(view: SituationView, events: Note[], count = 5): DrillSummary {
  const started = drillStartedAt(events) ?? Date.parse(view.scenario?.started_at ?? '');
  const inWindow = (at: string | null) => {
    if (Number.isNaN(started) || started === null) return true;
    const t = Date.parse(at ?? '');
    return Number.isNaN(t) ? false : t >= started;
  };
  return {
    elapsed_s: view.scenario?.elapsed_s ?? 0,
    done: view.tasks.filter((t) => t.done && inWindow(t.done_at)).length,
    total: view.tasks.length,
    events: events.filter((e) => (IN_DRILL.test(e.title) || DRILL_START.test(e.title)) && !OWN_LINE.test(e.title) && inWindow(e.updated_at)).slice(0, count),
    scenario: view.scenario?.title ?? null,
  };
}

/** The debrief's own sentence. It counts practice, not the household's day, and it says so when
 * nothing was ticked rather than reporting somebody else's two ticks as the drill's score. */
export function drillCount(summary: DrillSummary): string {
  if (summary.done === 0) return 'Nothing was ticked during the drill.';
  return `${summary.done} of ${summary.total} ${summary.total === 1 ? 'job' : 'jobs'} ticked during it.`;
}

/** Inside the debrief every line is the drill's, so the engine's "(drill)" tag is noise: the list is
 * already headed "What happened in the drill" and round 2's translation of the tag turned it into
 * "Drill started: National grid collapse in the drill". */
export function drillEventTitle(title: string): string {
  return (title ?? '').replace(/\s*\(drill\)\s*$/i, '');
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
