import { useState } from 'react';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { errorMessage } from '../api/useQuery';
import { eventTitle } from '../api/words';
import { notify } from '../components/Notice';
import { describeElapsed } from '../tools/situation';
import { clockTime } from './conditions';
import { drillSummary, publishDrillSummary, useDrillSummary } from './drill';
import { useSituation } from './SituationProvider';

/** The way out of a drill. It lives in the band beside the Drill chip, so a drill costs the phone one
 * row of chrome rather than a banner, a band, a theme row and a heading that all say the word. */
export function EndDrillButton() {
  const { view, apply } = useSituation();
  const { refresh: refreshStatus } = useStatus();
  const [busy, setBusy] = useState(false);
  if (!view?.meta.drill) return null;
  const end = async () => {
    setBusy(true);
    const before = view;
    try {
      apply(await api.endDrill());
      const events = await api.notes('event').catch(() => []);
      publishDrillSummary(drillSummary(before, events));
      void refreshStatus();
    } catch (e) {
      notify(`Could not end the drill: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" className="btn btn-small btn-danger band-drill-end" disabled={busy} onClick={() => void end()}>End drill</button>
  );
}

/** The debrief, once the drill is over: one count of the jobs, one phrasing of the clock, and the log
 * in the household's own words. */
export function DrillBanner() {
  const [summary, clear] = useDrillSummary();
  if (!summary) return null;
  return (
    <div className="drill-summary no-print" role="status">
      <p>
        <strong>Drill ended{summary.scenario ? `: ${summary.scenario}` : ''}.</strong>{' '}
        {describeElapsed(summary.elapsed_s)}, {summary.done} of {summary.total} {summary.total === 1 ? 'job' : 'jobs'} ticked.
      </p>
      {summary.events.length > 0 && (
        <ul className="list drill-events" aria-label="What happened in the drill">
          {summary.events.map((e) => <li key={e.id}><strong>{clockTime(e.updated_at)}</strong> {eventTitle(e.title)}</li>)}
        </ul>
      )}
      <button type="button" className="btn btn-small" onClick={clear}>Close</button>
    </div>
  );
}
