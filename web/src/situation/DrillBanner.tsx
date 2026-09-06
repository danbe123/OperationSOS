import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { errorMessage } from '../api/useQuery';
import { eventTitle } from '../api/words';
import { notify } from '../components/Notice';
import { describeElapsed } from '../tools/situation';
import { clockTime } from './conditions';
import { drillCount, drillEventTitle, drillSummary, publishDrillSummary, useDrillSummary } from './drill';
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

/** The debrief, once the drill is over. It is a dialog, and it behaves like one: it used to be a
 * 326 px panel in the flow above the rail, which squeezed the five destinations off a 480 px kiosk
 * and left "Close" as the only control in reach. It also counted the household's real ticks as
 * practice, and listed real condition changes under "What happened in the drill". */
export function DrillBanner() {
  const [summary, clear] = useDrillSummary();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (summary) heading.current?.focus();
  }, [summary]);
  if (!summary) return null;
  const close = () => {
    clear();
    // The button that opened this went with the drill, so focus goes back to the screen itself
    // rather than nowhere.
    document.getElementById('main')?.focus();
  };
  return (
    <div className="modal-backdrop no-print" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="modal drill-summary" role="dialog" aria-modal="true" aria-labelledby="drill-debrief-title">
        <h2 id="drill-debrief-title" tabIndex={-1} ref={heading}>How the drill went</h2>
        <p>
          {summary.scenario ? `${summary.scenario}, ` : ''}
          {describeElapsed(summary.elapsed_s)}. {drillCount(summary)}
        </p>
        {summary.events.length > 0 ? (
          <ul className="list drill-events" aria-label="What happened in the drill">
            {summary.events.map((e) => <li key={e.id}><strong>{clockTime(e.updated_at)}</strong> {eventTitle(drillEventTitle(e.title))}</li>)}
          </ul>
        ) : (
          <p className="muted">The box recorded nothing else while the drill ran.</p>
        )}
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={close}>Close</button>
        </div>
      </div>
    </div>
  );
}
