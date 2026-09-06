import { useState } from 'react';
import { api, ApiError } from '../api/client';
import type { Condition, ConditionState } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { CONDITION_INFO, describeDuration, elapsedFrom, STATE_LABEL, STATE_SYMBOL, STATE_TONE } from './conditions';
import { ukWhen } from '../tools/dates';
import { localInput, SINCE_OPTIONS, sinceChoiceFor, sinceIso, type SinceChoice } from './since';

const STATES: ConditionState[] = ['working', 'degraded', 'off'];
const BUTTON_LABEL: Record<ConditionState, string> = { working: 'Working', degraded: 'Patchy', off: 'Off' };

/** One condition on the sheet. A condition that is working is one line — its name, its state and a
 * way to change it — and only opens into the form when somebody asks. Nine of the ten are working
 * on almost every box, and rendering the full form for each of them made the sheet 3,733 px of
 * scroll in a 423 px column: a household adding "the water has gone too" scrolled past four
 * irrelevant forms to reach it. A condition that is *not* working is the thing the sheet is for and
 * is always open. */
export function ConditionRow({ condition, onSaved, open = false, onOpen }: {
  condition: Condition;
  onSaved: (c: Condition) => void;
  open?: boolean;
  onOpen?: (id: string | null) => void;
}) {
  const info = CONDITION_INFO[condition.id];
  // What the box has stored for this condition, and the answer it would have come from. A condition
  // that is working has no interesting "since" — the time on the row is whenever somebody last said
  // so — and the picker is there for the change about to be made, so it opens on "Just now". A
  // condition that is off or patchy opens on the time the box is already telling everyone about.
  const stored = condition.since ?? condition.updated_at;
  const storedChoice = condition.state === 'working' ? 'now' : sinceChoiceFor(stored);
  const [choice, setChoice] = useState<SinceChoice>(storedChoice);
  const [custom, setCustom] = useState(() => localInput(stored));
  const [note, setNote] = useState(condition.note);
  const [busy, setBusy] = useState(false);
  // Another phone in the house can change this row while it is on the screen. When the stored answer
  // moves under us the picker follows it rather than sitting on the reader's last choice.
  const [stamp, setStamp] = useState(`${condition.state}|${stored}`);
  if (stamp !== `${condition.state}|${stored}`) {
    setStamp(`${condition.state}|${stored}`);
    setChoice(storedChoice);
    setCustom(localInput(stored));
  }

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
  const setAt = condition.set_by && ukWhen(condition.updated_at);
  // Working: one row until somebody asks for the form. Anything else is what the sheet is for.
  const collapsible = condition.state === 'working';
  const shown = !collapsible || open;
  return (
    <li className={`cond-row cond-row-${tone}${shown ? '' : ' cond-row-quiet'}`} id={condition.id}>
      <div className="cond-row-head">
        <h3><Icon name={info.icon} size={22} /> {info.title}</h3>
        <span className={`badge badge-${tone}`}><span aria-hidden="true">{STATE_SYMBOL[condition.state]}</span> {STATE_LABEL[condition.state]}</span>
        {condition.state !== 'working' && <span className="muted">for {describeDuration(elapsedFrom(condition))}</span>}
        {collapsible && (
          <button
            type="button"
            className="btn btn-small cond-change"
            aria-expanded={open}
            onClick={() => onOpen?.(open ? null : condition.id)}
          >
            <Icon name={open ? 'up' : 'down'} size={18} />
            <span>{open ? 'Close' : 'Change'}</span>
          </button>
        )}
      </div>
      {shown && (
        <>
          <div className="row cond-states" role="group" aria-label={info.title}>
            {STATES.map((s) => (
              <button
                key={s}
                type="button"
                /* The chosen state wears its own colour, never the accent: an "off" that reads as the
                   primary action is exactly the misreading this screen cannot afford. */
                className={s === condition.state ? `btn state-btn state-set state-${STATE_TONE[s]}` : 'btn state-btn'}
                aria-pressed={s === condition.state}
                disabled={busy}
                onClick={() => void save(s)}
              >
                {/* The symbol marks the choice, not the option: three ticks and crosses shown at once
                    told the reader nothing about which one the box is holding. The word carries the
                    accessible name either way, so a screen reader hears "Off, pressed" as before. */}
                {s === condition.state && <span className="state-glyph" aria-hidden="true">{STATE_SYMBOL[s]}</span>}
                <span>{BUTTON_LABEL[s]}</span>
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
              /* A text field the box parses itself, in the order this country writes dates in and on
                 a 24-hour clock. The native control took its order from the browser's locale and
                 asked for 6 September as "09/06/2026, 03:12 AM". */
              <label className="field cond-time">
                <span>Time it started (dd/mm/yyyy hh:mm)</span>
                <input
                  type="text"
                  inputMode="numeric"
                  aria-label={`${info.title}: time it started, as day slash month slash year and a 24-hour time`}
                  placeholder="06/09/2026 03:12"
                  value={custom}
                  disabled={busy}
                  onChange={(e) => setCustom(e.target.value)}
                  onBlur={() => { if (custom && condition.state !== 'working') void save(condition.state, 'custom', custom); }}
                />
              </label>
            )}
            <label className="field cond-note">
              <span>Note</span>
              <input type="text" aria-label={`${info.title}: note`} value={note} maxLength={200} disabled={busy} onChange={(e) => setNote(e.target.value)} placeholder="The street is dark as far as the shop" />
            </label>
            <button type="button" className="btn" disabled={busy || note.trim() === condition.note} onClick={() => void save(condition.state)}>Save note</button>
          </div>
          <p className="muted cond-meta">
            {condition.source === 'inferred' && <span className="badge badge-warn">worked out by the box</span>}
            {condition.source === 'detected' && <span className="badge">detected by the box</span>}
            {/* On a box hung on the wall this morning nobody has touched nine of these ten rows, and the
                line read "Set from at ." — a sentence with its two facts missing. Say the plain thing
                instead, and only claim a person and a time when the box has both. */}
            {' '}{setAt ? `Set from ${condition.set_by} at ${setAt}.` : 'Nobody has set this yet.'}
            {condition.note && ` Note: ${condition.note}`}
          </p>
        </>
      )}
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
