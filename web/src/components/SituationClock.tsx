import { useEffect, useReducer, useState } from 'react';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { Situation } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { Icon } from '../icons';
import { notify } from './Notice';
import { describeElapsed, elapsedSince, phaseFor } from '../tools/situation';

export function situationLine(s: Situation, now = Date.now()): string {
  if (!s.slug) return '';
  const elapsed = elapsedSince(s.started_at, now);
  return `${describeElapsed(elapsed)}, ${phaseFor(elapsed).title.toLowerCase()}`;
}

/** The clock control on a guide, in the screen head beside Map and Print. One slot, one size, before
 * and after: "Start the clock" until it is started, then a quiet chip that says how long it has been
 * running and which phase that is. Ending is behind the chip, with its confirm, not a headline button
 * beside the title. The parent owns the situation (it polls it) and receives changes. */
export function SituationClock({ slug, situation, onChange }: { slug: string; situation: Situation | null; onChange: (s: Situation) => void }) {
  const [confirm, setConfirm] = useState<'start' | 'end' | null>(null);
  const [open, setOpen] = useState(false);
  const { refresh } = useStatus();          // Home reads the situation from /status
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (situation === null) return null;
  const active = situation.slug === slug;
  const other = situation.slug !== null && !active ? situation : null;
  const start = async () => {
    try {
      onChange(await api.startSituation(slug));
      setConfirm(null);
      void refresh();
    } catch (e) {
      notify(`Could not start the clock: ${errorMessage(e)}`);
    }
  };
  const end = async () => {
    try {
      onChange(await api.endSituation());
      setConfirm(null);
      setOpen(false);
      void refresh();
    } catch (e) {
      notify(`Could not end the situation: ${errorMessage(e)}`);
    }
  };
  if (active && situation.slug) {
    const started = new Date(situation.started_at);
    const startedText = Number.isNaN(started.getTime()) ? '' : started.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    return (
      <div className="situation-clock" role="status">
        {/* The chip shows the elapsed time alone, so it is no wider than Start was and the head keeps
            one line on the kiosk; the phase is the dot on its tab, and the full line is the name. */}
        <button type="button" className={open ? 'btn btn-small clock-chip active' : 'btn btn-small clock-chip'} aria-expanded={open}
                aria-label={situationLine(situation)} title="The clock on this situation. Tap for when it started, and to end it."
                onClick={() => { setOpen((v) => !v); setConfirm(null); }}>
          <Icon name="clock" size={18} /><span>{describeElapsed(elapsedSince(situation.started_at))}</span>
        </button>
        {open && (
          <div className="clock-panel">
            {startedText && <span className="muted">Started {startedText}</span>}
            {confirm === 'end' ? (
              <span className="row"><button type="button" className="btn btn-small btn-danger" onClick={() => void end()}>Confirm end</button><button type="button" className="btn btn-small" onClick={() => setConfirm(null)}>Cancel</button></span>
            ) : (
              <button type="button" className="btn btn-small" onClick={() => setConfirm('end')}>End situation</button>
            )}
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="situation-clock">
      {confirm === 'start' ? (
        <span className="row">
          {other && <span className="muted">This replaces the situation that is running ({other.title ?? other.slug}).</span>}
          <button type="button" className="btn btn-small btn-primary" onClick={() => void start()}>Confirm start</button>
          <button type="button" className="btn btn-small" onClick={() => setConfirm(null)}>Cancel</button>
        </span>
      ) : (
        <button type="button" className="btn btn-small btn-primary clock-start" title="Starts a clock: the tabs, the jobs and the forecasts follow the time."
                onClick={() => (other ? setConfirm('start') : void start())}>
          <Icon name="clock" size={18} /><span>Start the clock</span>
        </button>
      )}
    </div>
  );
}
