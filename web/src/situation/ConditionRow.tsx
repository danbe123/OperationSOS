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

/** One service on the sheet: its name, its state, and the three states to move it to, on the row.
 *
 * The row used to hide its three buttons behind a "Change" button, which put a door in front of the
 * door — a household saying "the water has gone too" tapped Change, then Off, and the sheet was ten
 * rows of a control that did nothing but reveal another control. The states are on the row now, and
 * the one question the box cannot work out — when it started — is asked once, on the row somebody
 * touched, after they say what changed. Everything else the box knows about the service (who set
 * it, the note, the day-old prompt) is behind Details, where it stays out of the way of the answer. */
export function ConditionRow({ condition, onSaved, open = false, onOpen }: {
  condition: Condition;
  onSaved: (c: Condition) => void;
  open?: boolean;
  onOpen?: (id: string | null) => void;
}) {
  const info = CONDITION_INFO[condition.id];
  // The instant the box is holding, and the answer that reproduces it. Anything saved from this row
  // that is not itself a change of state — a note, most of all — must send this back untouched: a
  // household that types "the street is dark" into an outage that began at three in the morning has
  // said nothing about when it began, and the box must not quietly rewrite it to now.
  const stored = condition.since ?? condition.updated_at;
  const storedChoice = condition.state === 'working' ? 'now' : sinceChoiceFor(stored);
  const storedInput = localInput(stored);
  const [choice, setChoice] = useState<SinceChoice>(storedChoice);
  const [custom, setCustom] = useState(storedInput);
  const [note, setNote] = useState(condition.note);
  const [busy, setBusy] = useState(false);
  // The state somebody has tapped and not yet answered "since when?" for. Null until they do.
  const [pending, setPending] = useState<ConditionState | null>(null);
  // Another phone in the house can change this row while it is on the screen. When the stored answer
  // moves under us the picker follows it rather than sitting on the reader's last choice.
  const [stamp, setStamp] = useState(`${condition.state}|${stored}`);
  if (stamp !== `${condition.state}|${stored}`) {
    setStamp(`${condition.state}|${stored}`);
    setChoice(storedChoice);
    setCustom(storedInput);
    setPending(null);
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

  /** Put the question away and the picker back on what the box is holding. A half-answered question
   * that is backed out of must leave nothing behind: the answer lived on in `choice` and the next
   * "Save note" sent it, moving a start time nobody had touched. */
  const forget = () => {
    setPending(null);
    setChoice(storedChoice);
    setCustom(storedInput);
  };

  /** Tapping the state the box already holds asks nothing; tapping any other one asks when it began.
   * When, for the state about to be set — so the question opens on "Just now", not on the time the
   * state being replaced started. */
  const ask = (state: ConditionState) => {
    if (state === condition.state) {
      forget();
      return;
    }
    setChoice('now');
    setCustom(localInput(new Date().toISOString()));
    setPending(state);
  };

  const tone = STATE_TONE[condition.state];
  const setAt = condition.set_by && ukWhen(condition.updated_at);
  return (
    <li className={`cond-row cond-row-${tone}`} id={condition.id}>
      {/* Two lines and no more: the title (with how long, when it is not working), then the buttons.
          The state used to be said twice on the first line — a badge reading "✓ working" beside a
          pressed button reading "✓ Working" — and Details sat between them, which on a 390 px phone
          wrapped onto a line of its own and made every one of the ten rows three lines tall. */}
      <div className="cond-row-head">
        <h3><Icon name={info.icon} size={22} /> {info.title}</h3>
        {condition.state !== 'working' && <span className="muted">for {describeDuration(elapsedFrom(condition))}</span>}
      </div>
      <div className="row cond-states">
        <div className="row cond-state-btns" role="group" aria-label={info.title}>
          {STATES.map((s) => (
            <button
              key={s}
              type="button"
              /* The chosen state wears its own colour, never the accent: an "off" that reads as the
                 primary action is exactly the misreading this screen cannot afford. */
              className={s === condition.state ? `btn state-btn state-set state-${STATE_TONE[s]}` : 'btn state-btn'}
              aria-pressed={s === condition.state}
              disabled={busy}
              onClick={() => ask(s)}
            >
              {/* The symbol marks the choice, not the option: three ticks and crosses shown at once
                  told the reader nothing about which one the box is holding. The word carries the
                  accessible name either way, so a screen reader hears "Off, pressed" as before. */}
              {s === condition.state && <span className="state-glyph" aria-hidden="true">{STATE_SYMBOL[s]}</span>}
              <span>{BUTTON_LABEL[s]}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="btn btn-small cond-details-toggle no-print"
          /* Ten rows carry this button; without the service's name a screen reader hears "Details"
             ten times over and cannot tell which service it is about to open. It rides the end of
             the buttons line, outside the group, so the group is the three states and nothing else. */
          aria-label={`Details: ${info.title}`}
          aria-expanded={open}
          onClick={() => onOpen?.(open ? null : condition.id)}
        >
          <Icon name={open ? 'up' : 'down'} size={18} />
          <span>Details</span>
        </button>
      </div>
      {pending && (
        <div className="row cond-since" role="group" aria-label={`${info.title}: since when?`}>
          <span className="cond-since-ask">Since when?</span>
          {SINCE_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              className={`btn since-btn${choice === o.value ? ' since-set' : ''}`}
              aria-pressed={choice === o.value}
              disabled={busy}
              onClick={() => setChoice(o.value)}
            >{o.label}</button>
          ))}
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
              />
            </label>
          )}
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={() => { const state = pending; forget(); void save(state, choice, custom); }}
          >Save</button>
          <button type="button" className="btn" disabled={busy} onClick={forget}>Cancel</button>
        </div>
      )}
      {open && (
        <>
          <div className="row cond-details">
            <label className="field cond-note">
              <span>Note</span>
              <input type="text" aria-label={`${info.title}: note`} value={note} maxLength={200} disabled={busy} onChange={(e) => setNote(e.target.value)} placeholder="The street is dark as far as the shop" />
            </label>
            {/* The state and the instant the box already holds, said out loud: a note is a note. */}
            <button type="button" className="btn" disabled={busy || note.trim() === condition.note} onClick={() => void save(condition.state, storedChoice, storedInput)}>Save note</button>
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
          {condition.stale && (
            <p className="cond-stale row" role="status">
              <span className="warning">Still {STATE_LABEL[condition.state]}?</span>
              <span className="muted">Nobody has confirmed this for a day.</span>
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void confirm()}>Confirm, still {STATE_LABEL[condition.state]}</button>
            </p>
          )}
        </>
      )}
    </li>
  );
}
