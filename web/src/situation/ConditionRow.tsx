import { useState } from 'react';
import { api, ApiError } from '../api/client';
import type { Condition, ConditionState } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { clockTime, CONDITION_INFO, describeDuration, STATE_LABEL, STATE_SYMBOL, STATE_TONE } from './conditions';
import { SINCE_OPTIONS, sinceIso, type SinceChoice } from './since';

const STATES: ConditionState[] = ['working', 'degraded', 'off'];
const BUTTON_LABEL: Record<ConditionState, string> = { working: 'Working', degraded: 'Patchy', off: 'Off' };

/** One condition on the sheet: three state buttons, when it started, a note, and who said so. */
export function ConditionRow({ condition, onSaved }: { condition: Condition; onSaved: (c: Condition) => void }) {
  const info = CONDITION_INFO[condition.id];
  const [choice, setChoice] = useState<SinceChoice>('now');
  const [custom, setCustom] = useState('');
  const [note, setNote] = useState(condition.note);
  const [busy, setBusy] = useState(false);

  const save = async (state: ConditionState, sinceChoice: SinceChoice = choice, customValue = custom) => {
    setBusy(true);
    try {
      onSaved(await api.setCondition(condition.id, {
        state,
        since: sinceIso(sinceChoice, customValue),
        note: note.trim(),
        expected_updated_at: condition.updated_at,
      }));
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) notify(`${info.title} was changed on another device; showing the latest.`);
      else notify(`Could not save ${info.title}: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      onSaved(await api.confirmCondition(condition.id));
    } catch (e) {
      notify(`Could not confirm ${info.title}: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const tone = STATE_TONE[condition.state];
  return (
    <li className={`cond-row cond-row-${tone}`} id={condition.id}>
      <div className="cond-row-head">
        <h3><Icon name={info.icon} size={22} /> {info.title}</h3>
        <span className={`badge badge-${tone}`}><span aria-hidden="true">{STATE_SYMBOL[condition.state]}</span> {STATE_LABEL[condition.state]}</span>
        {condition.state !== 'working' && <span className="muted">for {describeDuration(condition.for_s)}</span>}
      </div>
      <div className="row cond-states" role="group" aria-label={info.title}>
        {STATES.map((s) => (
          <button
            key={s}
            type="button"
            className={s === condition.state ? 'btn btn-primary' : 'btn'}
            aria-pressed={s === condition.state}
            disabled={busy}
            onClick={() => void save(s)}
          >
            <span aria-hidden="true">{STATE_SYMBOL[s]}</span> {BUTTON_LABEL[s]}
          </button>
        ))}
      </div>
      <div className="row cond-since">
        <label className="field">
          <span>Since</span>
          <select
            aria-label={`${info.title}: since`}
            value={choice}
            disabled={busy}
            onChange={(e) => {
              const next = e.target.value as SinceChoice;
              setChoice(next);
              if (next !== 'custom' && condition.state !== 'working') void save(condition.state, next);
            }}
          >
            {SINCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        {choice === 'custom' && (
          <label className="field">
            <span>Time</span>
            <input
              type="datetime-local"
              aria-label={`${info.title}: time it started`}
              value={custom}
              disabled={busy}
              onChange={(e) => setCustom(e.target.value)}
              onBlur={() => { if (custom && condition.state !== 'working') void save(condition.state, 'custom', custom); }}
            />
          </label>
        )}
        <label className="field cond-note">
          <span>Note</span>
          <input type="text" aria-label={`${info.title}: note`} value={note} maxLength={200} disabled={busy} onChange={(e) => setNote(e.target.value)} placeholder="street is dark as far as the shop" />
        </label>
        <button type="button" className="btn" disabled={busy || note.trim() === condition.note} onClick={() => void save(condition.state)}>Save note</button>
      </div>
      <p className="muted cond-meta">
        {condition.source === 'inferred' && <span className="badge badge-warn">worked out by the box</span>}
        {condition.source === 'detected' && <span className="badge">detected by the box</span>}
        {' '}Set from {condition.set_by} at {clockTime(condition.updated_at)}.
        {condition.note && ` Note: ${condition.note}`}
      </p>
      {condition.stale && (
        <p className="cond-stale row" role="status">
          <span className="warning">Still {STATE_LABEL[condition.state]}?</span>
          <span className="muted">Nobody has confirmed this for a day.</span>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void confirm()}>Confirm, still {STATE_LABEL[condition.state]}</button>
        </p>
      )}
    </li>
  );
}
