import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { clockTime, CONDITION_INFO, countdown, secondsUntil, SEVERITY_SYMBOL, SEVERITY_TONE, STATE_LABEL } from './conditions';
import { briefingHref, contentHref } from './links';
import { ReadAloud } from './ReadAloud';
import { useSituation } from './SituationProvider';
import { TaskRow } from './TaskRow';
import { withCondition, withTask } from './apply';

const DAY_S = 86_400;
/** How long a job stays where it was ticked before it moves down the list: the same ten seconds the
 * Undo button is offered for, so nothing ever moves under the finger that ticked it. */
export const SETTLE_MS = 10_000;

/** The front door answers "what do I do now", so a job that was already done before this screen
 * opened belongs under the ones that are not. A job ticked here stays exactly where it was ticked
 * until its Undo has expired. */
export function useSunkTasks(tasks: { id: string; done: boolean }[]): Set<string> {
  const [sunk, setSunk] = useState<Set<string>>(() => new Set(tasks.filter((t) => t.done).map((t) => t.id)));
  const timers = useRef(new Map<string, number>());
  useEffect(() => {
    const pending = timers.current;
    tasks.forEach((t) => {
      if (!t.done || sunk.has(t.id) || pending.has(t.id)) return;
      pending.set(t.id, window.setTimeout(() => {
        pending.delete(t.id);
        setSunk((s) => new Set(s).add(t.id));
      }, SETTLE_MS));
    });
    // A job unticked again comes back up with the rest.
    tasks.forEach((t) => {
      if (t.done) return;
      const timer = pending.get(t.id);
      if (timer !== undefined) { window.clearTimeout(timer); pending.delete(t.id); }
      if (sunk.has(t.id)) setSunk((s) => { const next = new Set(s); next.delete(t.id); return next; });
    });
  }, [tasks, sunk]);
  useEffect(() => {
    const pending = timers.current;
    return () => { pending.forEach((id) => window.clearTimeout(id)); pending.clear(); };
  }, []);
  return sunk;
}

/** Now, while something is happening: what to do, what is coming, what the box is guessing, and what
 * to read. Done jobs stay, struck through, until the engine retires them: a task must not vanish
 * under the finger. */
export function Briefing() {
  const { view, apply } = useSituation();
  const block = useRef<HTMLDivElement>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [showDone, setShowDone] = useState(false);
  const sunk = useSunkTasks((view?.tasks ?? []).filter((t) => t.bucket === 'now' || t.bucket === 'hour'));
  if (!view) return null;
  const now = Date.parse(view.meta.now) || Date.now();
  const inferred = view.inferred.filter((i) => !dismissed.includes(i.rule));
  const soon = view.forecast.filter((f) => secondsUntil(f.due_at, now) < DAY_S);
  const doing = view.tasks.filter((t) => t.bucket === 'now' || t.bucket === 'hour');
  const left = doing.filter((t) => !sunk.has(t.id));
  const done = doing.filter((t) => sunk.has(t.id));
  const bulletin = view.bulletins.next;
  const empty = !inferred.length && !soon.length && !doing.length && !view.briefing.length && !bulletin;

  const accept = async (condition: typeof view.inferred[number]) => {
    setBusy(condition.rule);
    try {
      apply(withCondition(view, await api.acceptInferred(condition.condition, condition.rule)));
    } catch (e) {
      notify(`Could not accept that: ${errorMessage(e)}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    /* Not a landmark of its own: "Briefing" was a region wrapping four regions, named after a word
       that is nowhere on the screen. */
    <div className="stack" ref={block}>
      {!empty && (
        <div className="row no-print"><ReadAloud id="briefing" target={block} label="Read the briefing aloud" /></div>
      )}

      <section className="panel panel-signal briefing-block" aria-label="Right now">
        <div className="panel-head">
          <h2>Right now</h2>
          <Link className="btn btn-small" to="/tasks"><Icon name="plan" size={18} /><span>All of them</span></Link>
        </div>
        {/* The front door opened on two struck-through jobs and their reasons, and the first job the
            household still had to do was 598 px down a 423 px screen. What is left to do comes
            first, with its reason; what is already done is one line at the bottom. */}
        {doing.length === 0 ? (
          <p className="muted">Nothing outstanding right now. The box adds jobs as the situation changes.</p>
        ) : left.length === 0 ? (
          <p className="muted">Everything the box has asked for is done. {done.length === 1 ? 'The one job' : `All ${done.length} jobs`} below can be unticked if you need to.</p>
        ) : (
          <ul className="list">
            {left.map((t, i) => <TaskRow key={t.id} task={t} why={i === 0} onChanged={(saved) => apply(withTask(view, saved))} />)}
          </ul>
        )}
        {done.length > 0 && (
          <>
            <button type="button" className="btn btn-small now-done-toggle" aria-expanded={showDone} onClick={() => setShowDone((v) => !v)}>
              <Icon name={showDone ? 'up' : 'down'} size={18} />
              <span>{done.length} done — {showDone ? 'hide them' : 'show them'}</span>
            </button>
            {showDone && (
              <ul className="list">
                {done.map((t) => <TaskRow key={t.id} task={t} why={false} onChanged={(saved) => apply(withTask(view, saved))} />)}
              </ul>
            )}
          </>
        )}
      </section>

      {soon.length > 0 && (
        <section className="panel briefing-block" aria-label="Coming up">
          <h2>Coming up</h2>
          <ul className="list briefing-list">
            {soon.map((f) => {
              const href = contentHref(f.link);
              return (
                <li key={f.id} className={`forecast forecast-${SEVERITY_TONE[f.severity]}`}>
                  {/* The thing first, then when: "due Fridge food unsafe in 2 h" was not a sentence
                      in any register. */}
                  <p className="briefing-title">
                    {f.title}{' '}
                    <span className={`badge badge-${SEVERITY_TONE[f.severity]}`}>
                      <span aria-hidden="true">{SEVERITY_SYMBOL[f.severity]}</span> {f.passed ? 'passed' : 'due'} {countdown(f.due_at, now)}
                    </span>
                  </p>
                  {f.why && <p className="muted">{f.why}</p>}
                  {href && <Link className="btn btn-small" to={href}>Read more</Link>}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {inferred.length > 0 && (
        <section className="panel panel-warn briefing-block" aria-label="The box thinks">
          <h2>The box thinks</h2>
          <ul className="list briefing-list">
            {inferred.map((i) => (
              <li key={i.rule}>
                {/* Half the condition names are compound ("Landline and 999", "Shops and cash"), so
                    a verb between the name and the state disagreed with the subject on every other
                    row. The dash does the same job and agrees with everything. */}
                <p className="briefing-title">
                  {CONDITION_INFO[i.condition].title} — probably {STATE_LABEL[i.state]}
                  {i.detected && <> <span className="badge badge-warn"><span aria-hidden="true">▲</span> detected by the box</span></>}
                </p>
                <p className="muted">{i.why}</p>
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={busy === i.rule} onClick={() => void accept(i)}>Accept</button>
                  <button type="button" className="btn" onClick={() => setDismissed((d) => [...d, i.rule])}>Not now</button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(view.briefing.length > 0 || bulletin) && (
        <section className="panel briefing-block" aria-label="Read">
          <h2>Read</h2>
          {view.briefing.length > 0 && (
            <ul className="row briefing-reading">
              {view.briefing.map((b) => <li key={`${b.kind}:${b.ref}`}><Link className="btn btn-small" to={briefingHref(b)}>{b.title}</Link></li>)}
            </ul>
          )}
          {bulletin && (
            <p className="muted"><Icon name="radio" size={18} /> Next bulletin: {bulletin.station}, {bulletin.frequency}, at {clockTime(bulletin.at)}.</p>
          )}
        </section>
      )}
    </div>
  );
}
