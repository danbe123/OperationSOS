import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { Condition, ConditionId, ConditionState } from '../api/types';
import { CONDITION_IDS } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { ConditionRow } from '../situation/ConditionRow';
import { CONDITION_INFO, HOME_CONDITION_IDS } from '../situation/conditions';
import { withCondition } from '../situation/apply';
import { useSituation } from '../situation/SituationProvider';
import { describeElapsed, phaseFor } from '../tools/situation';

/** The situation sheet: everything the engine reads, in one place, editable from any phone. */
export function Situation() {
  const { view, apply, refresh, error, loading } = useSituation();
  const { refresh: refreshStatus } = useStatus();
  const playbooksQ = useQuery(() => api.playbooks(), []);
  const [slug, setSlug] = useState('');
  const [busy, setBusy] = useState(false);
  const [drillHours, setDrillHours] = useState('2');
  const [drillOff, setDrillOff] = useState<ConditionId[]>(['power']);

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

  return (
    <div className="screen situation-screen">
      <AppBar
        title="Situation"
        search={false}
        actions={
          <>
            <Link className="btn btn-chrome" to="/board"><Icon name="plan" /><span>Board</span></Link>
            <a className="btn btn-chrome" href="/api/situation/report" target="_blank" rel="noreferrer"><Icon name="print" /><span>Print report</span></a>
          </>
        }
      />
      {error && <p className="pad warning">The situation is unavailable: {error}</p>}
      {loading && !view && <p className="pad muted">Reading the situation…</p>}

      <section aria-label="Conditions">
        <div className="pad">
          <h2>What is working</h2>
          <p className="muted">Tap a state. Everyone on the box sees the change, and the advice follows it.</p>
        </div>
        <ul className="list cond-rows">
          {view && CONDITION_IDS.map((id) => view.conditions[id] && <ConditionRow key={id} condition={view.conditions[id]} onSaved={saved} />)}
        </ul>
      </section>

      <section aria-label="Situation clock" id="clock">
        <div className="pad">
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
                  <option value="">Choose a playbook…</option>
                  {playbooks.map((p) => <option key={p.slug} value={p.slug}>{p.title}</option>)}
                </select>
              </label>
              <button type="button" className="btn btn-primary" disabled={busy || !slug} onClick={() => void run('start the clock', async () => { await api.startSituation(slug); await refresh(); await refreshStatus(); })}>Start the clock</button>
            </div>
          )}
        </div>
      </section>

      {!view?.meta.drill && (
        <section aria-label="Drill" id="drill">
          <div className="pad stack">
            <h2>Practice a drill</h2>
            <p className="muted">Pretend a situation is running, without touching the real conditions. Everything says DRILL.</p>
            <div className="row">
              <label className="field">
                <span>Scenario</span>
                <select aria-label="Drill scenario" value={slug} onChange={(e) => setSlug(e.target.value)}>
                  <option value="">Choose a playbook…</option>
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
                disabled={busy || !slug || drillOff.length === 0}
                onClick={() => void run('start the drill', async () => {
                  const conditions = Object.fromEntries(drillOff.map((id) => [id, 'off' as ConditionState]));
                  apply(await api.startDrill({ scenario: slug, conditions, hours_ago: Number(drillHours) }));
                  await refreshStatus();
                })}
              >Start drill</button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
