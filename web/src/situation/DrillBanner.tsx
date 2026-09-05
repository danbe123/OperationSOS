import { useState } from 'react';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { describeElapsed } from '../tools/situation';
import { clockTime } from './conditions';
import { drillSummary, type DrillSummary } from './drill';
import { useSituation } from './SituationProvider';

/** DRILL says so on every screen, with the way out of it, and the debrief when it ends:
 * a practice must never be mistaken for the real thing, on any phone in the house. */
export function DrillBanner() {
  const { view, apply } = useSituation();
  const { refresh: refreshStatus } = useStatus();
  const [summary, setSummary] = useState<DrillSummary | null>(null);
  const [busy, setBusy] = useState(false);

  const end = async () => {
    if (!view) return;
    setBusy(true);
    const before = view;
    try {
      apply(await api.endDrill());
      const events = await api.notes('event').catch(() => []);
      setSummary(drillSummary(before, events));
      void refreshStatus();
    } catch (e) {
      notify(`Could not end the drill: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };

  if (view?.meta.drill) {
    return (
      <div className="drill-bar no-print" role="status">
        <span className="badge badge-warn">⚑ DRILL</span>
        <span>DRILL in progress{view.scenario ? `: ${view.scenario.title}` : ''}. Nothing here is real; tasks still tick and the log says drill.</span>
        <button type="button" className="btn btn-danger" disabled={busy} onClick={() => void end()}>End drill</button>
      </div>
    );
  }
  if (!summary) return null;
  return (
    <div className="drill-summary no-print" role="status">
      <p>
        <strong>Drill ended{summary.scenario ? `: ${summary.scenario}` : ''}.</strong>{' '}
        {describeElapsed(summary.elapsed_s)} on the clock, {summary.done} of {summary.total} {summary.total === 1 ? 'job' : 'jobs'} ticked.
      </p>
      {summary.events.length > 0 && (
        <ul className="list drill-events" aria-label="What happened in the drill">
          {summary.events.map((e) => <li key={e.id}><strong>{clockTime(e.updated_at)}</strong> {e.title}</li>)}
        </ul>
      )}
      <button type="button" className="btn" onClick={() => setSummary(null)}>Close</button>
    </div>
  );
}
