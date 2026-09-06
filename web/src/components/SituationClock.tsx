import { useEffect, useReducer, useState } from 'react';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { Situation } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from './Notice';
import { describeElapsed, elapsedSince, phaseFor } from '../tools/situation';

export function situationLine(s: Situation, now = Date.now()): string {
  if (!s.slug) return '';
  const elapsed = elapsedSince(s.started_at, now);
  return `${describeElapsed(elapsed)}, ${phaseFor(elapsed).title.toLowerCase()}`;
}

/** The "this has started" control on a guide. It lives in the screen head beside Map and Print: a
 * box-wide state change is not what someone opening a guide to read came for, so it is an outline
 * button with its consequence written on it, and the guidance is the first thing under the title.
 * The parent owns the situation (it polls it) and receives changes. */
export function SituationClock({ slug, situation, onChange }: { slug: string; situation: Situation | null; onChange: (s: Situation) => void }) {
  const [confirm, setConfirm] = useState<'start' | 'end' | null>(null);
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
      void refresh();
    } catch (e) {
      notify(`Could not end the situation: ${errorMessage(e)}`);
    }
  };
  if (active && situation.slug) {
    return (
      <div className="situation-clock" role="status">
        <span className="badge badge-warn">Active</span>
        <strong>Started {new Date(situation.started_at).toLocaleString('en-GB', { weekday: 'short', hour: '2-digit', minute: '2-digit' })}</strong>
        <span>{situationLine(situation)}</span>
        {confirm === 'end' ? (
          <span className="row"><button type="button" className="btn btn-small btn-danger" onClick={() => void end()}>Confirm end</button><button type="button" className="btn btn-small" onClick={() => setConfirm(null)}>Cancel</button></span>
        ) : (
          <button type="button" className="btn btn-small" onClick={() => setConfirm('end')}>End situation</button>
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
        <button type="button" className="btn btn-small clock-start" onClick={() => (other ? setConfirm('start') : void start())}>
          <span className="clock-start-text">This has started{' '}<small>starts a clock so the tabs follow the time</small></span>
        </button>
      )}
    </div>
  );
}
