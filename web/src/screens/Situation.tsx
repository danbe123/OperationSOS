import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { Condition, ConditionId, ConditionState } from '../api/types';
import { CONDITION_IDS } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { SituationExport } from '../situation/SituationExport';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { Briefing } from '../situation/Briefing';
import { ConditionRow } from '../situation/ConditionRow';
import { EventLog } from './plan/EventLog';
import { SensorsPanel } from '../situation/SensorsPanel';
import { CONDITION_INFO, describeDuration, HOME_CONDITION_IDS, STATE_LABEL, STATE_SYMBOL } from '../situation/conditions';
import { ukWhen } from '../tools/dates';
import { withCondition } from '../situation/apply';
import { nowTitle } from '../situation/nowTitle';
import { ReadAloud } from '../situation/ReadAloud';
import { isEventful, useSituation } from '../situation/SituationProvider';
import { describeElapsed, phaseFor } from '../tools/situation';
import './situation.css';

/** The service a `/situation#<id>` link names, if it names one. */
function conditionInHash(hash: string): string | null {
  const id = hash.replace(/^#/, '');
  return (CONDITION_IDS as readonly string[]).includes(id) ? id : null;
}

/** The situation sheet: everything the engine reads, in one place, editable from any phone. */
export function Situation() {
  const { view, apply, refresh, error, loading } = useSituation();
  const { refresh: refreshStatus } = useStatus();
  const playbooksQ = useQuery(() => api.playbooks(), []);
  const [slug, setSlug] = useState('');
  const [busy, setBusy] = useState(false);
  const [drillHours, setDrillHours] = useState('2');
  const [drillOff, setDrillOff] = useState<ConditionId[]>(['power']);
  // Never a disabled primary with nothing on the screen saying why: Start stays live and says what
  // is missing when it is tapped.
  const drillSelect = useRef<HTMLSelectElement>(null);
  const [drillWhy, setDrillWhy] = useState<string | null>(null);

  const saved = (c: Condition) => {
    if (view) apply(withCondition(view, c));
    void refresh();
    void refreshStatus();
  };

  const run = async (what: string, fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      notify(`Could not ${what}: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const scenario = view?.scenario ?? null;
  const playbooks = playbooksQ.data ?? [];
  // One row's details open at a time: the sheet is a list of ten services, not ten forms. A chip
  // elsewhere in the box links to /situation#water, and lands with that service's details out.
  const { hash } = useLocation();
  const [open, setOpen] = useState<string | null>(() => conditionInHash(hash));
  const [lastHash, setLastHash] = useState(hash);
  if (lastHash !== hash) {
    setLastHash(hash);
    setOpen(conditionInHash(hash));
  }
  const conditions = view ? CONDITION_IDS.map((id) => view.conditions[id]).filter(Boolean) : [];
  const broken = conditions.filter((c) => c.state !== 'working');

  // While something is off, the sheet leads with what the box makes of it: what to do now, what is
  // coming up, what it thinks and what to read. The front door used to turn into this the moment a
  // service was tapped off; here it sits above the ten services it was worked out from. What is
  // read aloud is the briefing itself, so the speaker button belongs in the screen's own actions.
  const eventful = isEventful(view);
  const briefing = useRef<HTMLDivElement>(null);

  // A `/situation#log` link lands on a screen whose ten services are still empty, so the browser's
  // own anchor scroll puts the log where the log is about to stop being: by the time the view
  // arrives, ten rows have grown above it and the reader is looking at the drill form. The screen
  // scrolls the log into place itself, once, when there is something above it to push it down.
  const logRef = useRef<HTMLElement>(null);
  const scrolledTo = useRef<string | null>(null);
  useEffect(() => {
    if (hash.toLowerCase() !== '#log') {
      scrolledTo.current = null;
      return;
    }
    if (!view || scrolledTo.current === hash) return;
    scrolledTo.current = hash;
    logRef.current?.scrollIntoView();
  }, [view, hash]);

  return (
    <Screen
      title={eventful ? nowTitle(view) : 'Situation'}
      search={false}
      className="situation-screen"
      actions={
        <>
          {eventful && <ReadAloud id="briefing" target={briefing} label="Read aloud" />}
          <Link className="btn btn-small" to="/board"><Icon name="plan" size={18} /><span>Board</span></Link>
          <a className="btn btn-small" href="/api/situation/report" target="_blank" rel="noreferrer"><Icon name="print" size={18} /><span>Print report</span></a>
        </>
      }
    >
      <Body>
      {error && <p className="warning">The situation is unavailable: {error}</p>}
      {loading && !view && <p className="muted">Reading the situation…</p>}

      {eventful && <Briefing blockRef={briefing} />}

      <section className="panel no-print" aria-label="What is working">
        <div className="panel-head"><h2>What is working</h2></div>
        <p className="muted">
          {broken.length === 0
            ? 'Everything is working.'
            : `${broken.length} of ${conditions.length} not working.`}
        </p>
        <ul className="list cond-rows">
          {conditions.map((c) => (
            <ConditionRow key={c.id} condition={c} onSaved={saved} open={open === c.id} onOpen={setOpen} />
          ))}
        </ul>
      </section>

      {/* On paper a form is a row of dead controls. The sheet prints as a sheet: one line per
          service, what it is, since when, and whatever note somebody wrote on it. */}
      {view && (
        <table className="print-only situation-print">
          <caption>What is working</caption>
          <thead><tr><th>Service</th><th>State</th><th>Since</th><th>Note</th></tr></thead>
          <tbody>
            {conditions.map((c) => (
              <tr key={c.id}>
                <td>{CONDITION_INFO[c.id].title}</td>
                <td>{STATE_SYMBOL[c.state]} {STATE_LABEL[c.state]}</td>
                <td>{c.state === 'working' ? '—' : `${ukWhen(c.since)} (${describeDuration(c.for_s)})`}</td>
                <td>{c.note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* What happened sits under what is working: one screen for the situation, read in the order
          a household reads it. It used to be a tool screen two taps away under Tools. */}
      <section className="panel" id="log" ref={logRef} aria-label="What happened">
        <h2>What happened</h2>
        <EventLog />
      </section>

      <div className="no-print"><SensorsPanel /></div>

      <section className="panel no-print" aria-label="Clock" id="clock">
        <div className="stack">
          <h2>Clock</h2>
          {scenario ? (
            <>
              <p><strong>{scenario.title}</strong> — {describeElapsed(scenario.elapsed_s)}, {phaseFor(scenario.elapsed_s).title.toLowerCase()}.</p>
              <button type="button" className="btn btn-danger" disabled={busy} onClick={() => void run('end the situation', async () => { await api.endSituation(); await refresh(); await refreshStatus(); })}>End situation</button>
            </>
          ) : (
            <div className="row">
              <label className="field">
                <span>Start a situation</span>
                <select aria-label="Situation to start" value={slug} onChange={(e) => setSlug(e.target.value)}>
                  <option value="">Choose a situation…</option>
                  {playbooks.map((p) => <option key={p.slug} value={p.slug}>{p.title}</option>)}
                </select>
              </label>
              <button type="button" className="btn btn-primary" disabled={busy || !slug} onClick={() => void run('start the clock', async () => { await api.startSituation(slug); await refresh(); await refreshStatus(); })}>Start the clock</button>
            </div>
          )}
        </div>
      </section>

      <div className="no-print"><SituationExport /></div>

      {!view?.meta.drill && (
        <section className="panel no-print" aria-label="Practise a drill" id="drill">
          <div className="stack">
            <h2>Practise a drill</h2>
            <p className="muted">Pretend a situation is running, without touching the real conditions. Everything says DRILL.</p>
            <div className="row">
              <label className="field">
                <span>Situation</span>
                <select ref={drillSelect} aria-label="Drill scenario" value={slug} onChange={(e) => { setSlug(e.target.value); setDrillWhy(null); }}>
                  <option value="">Choose a situation…</option>
                  {playbooks.map((p) => <option key={p.slug} value={p.slug}>{p.title}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Started</span>
                <select aria-label="Drill started" value={drillHours} onChange={(e) => setDrillHours(e.target.value)}>
                  <option value="0">Just now</option>
                  <option value="2">2 hours ago</option>
                  <option value="12">12 hours ago</option>
                  <option value="48">2 days ago</option>
                </select>
              </label>
            </div>
            <fieldset className="row drill-conditions">
              <legend>What is off in the drill</legend>
              {HOME_CONDITION_IDS.map((id) => (
                <label key={id} className="check-row">
                  <input
                    type="checkbox"
                    checked={drillOff.includes(id)}
                    onChange={(e) => setDrillOff((xs) => (e.target.checked ? [...xs, id] : xs.filter((x) => x !== id)))}
                  />
                  <span>{CONDITION_INFO[id].short}</span>
                </label>
              ))}
            </fieldset>
            <div className="row">
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={() => {
                  if (!slug) { setDrillWhy('Choose a situation first.'); drillSelect.current?.focus(); return; }
                  if (drillOff.length === 0) { setDrillWhy('Choose at least one thing that is off in the drill.'); return; }
                  setDrillWhy(null);
                  void run('start the drill', async () => {
                    const conditions = Object.fromEntries(drillOff.map((id) => [id, 'off' as ConditionState]));
                    apply(await api.startDrill({ scenario: slug, conditions, hours_ago: Number(drillHours) }));
                    await refreshStatus();
                  });
                }}
              >Start drill</button>
              {drillWhy && <span className="warning" role="alert">{drillWhy}</span>}
            </div>
          </div>
        </section>
      )}
      </Body>
    </Screen>
  );
}
