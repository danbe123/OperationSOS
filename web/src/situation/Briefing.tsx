import { useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Forecast } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { clockTime, CONDITION_INFO, countdown, secondsUntil, SEVERITY_SYMBOL, SEVERITY_TONE, STATE_LABEL } from './conditions';
import { briefingHref, contentHref } from './links';
import { bulletinWords } from '../api/words';
import { useSituation } from './SituationProvider';
import { TaskRow } from './TaskRow';
import { withCondition, withTask } from './apply';

const DAY_S = 86_400;
/** How long a job stays where it was ticked before it moves down the list: the same ten seconds the
 * Undo button is offered for, so nothing ever moves under the finger that ticked it. */
export const SETTLE_MS = 10_000;

/** The briefing answers "what do I do now", so a job that was already done before this screen
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

/** One line of the forecast: what it is, and when — "Fridge food unsafe ▲ due in 2 h", or, once it
 * has gone by, "⚠ passed 1 h ago". `countdown` already says "passed" for anything in the past, so
 * the prefix is only ever added to something still to come; the front door used to print the word
 * twice. */
function ForecastRow({ item, now }: { item: Forecast; now: number }) {
  const href = contentHref(item.link);
  const passed = item.passed || secondsUntil(item.due_at, now) <= 0;
  return (
    <li className={`forecast forecast-${SEVERITY_TONE[item.severity]}`}>
      <p className="briefing-title">
        {item.title}{' '}
        <span className={`badge badge-${SEVERITY_TONE[item.severity]}`}>
          <span aria-hidden="true">{SEVERITY_SYMBOL[item.severity]}</span> {passed ? '' : 'due '}{countdown(item.due_at, now)}
        </span>
      </p>
      {item.why && <p className="muted">{item.why}</p>}
      {href && <Link className="btn btn-small" to={href}>Read more</Link>}
    </li>
  );
}

/** The sheet, while something is happening: what to do, what is coming, what the box is guessing,
 * and what to read. It sits at the top of /situation, above the services it was worked out from —
 * on the front door it replaced the question and the tiles the moment anything went off. Done jobs
 * stay, struck through, until the engine retires them: a task must not vanish under the finger. */
export function Briefing({ blockRef }: { blockRef?: RefObject<HTMLDivElement | null> } = {}) {
  const { view, apply } = useSituation();
  const own = useRef<HTMLDivElement>(null);
  const block = blockRef ?? own;
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [showDone, setShowDone] = useState(false);
  // The same array each render unless the jobs themselves change, so the settling timers below are
  // set once rather than re-examined on every tick of the clock.
  const doingNow = useMemo(() => (view?.tasks ?? []).filter((t) => t.bucket === 'now' || t.bucket === 'hour'), [view]);
  const sunk = useSunkTasks(doingNow);
  if (!view) return null;
  const now = Date.parse(view.meta.now) || Date.now();
  // One guess per service. The engine can raise the same conclusion from a rule and from its own
  // sensors — "Internet — probably off" twice, each with its own Accept and Not now — which is four
  // buttons of data entry for one question.
  const guesses = new Map<string, typeof view.inferred[number]>();
  for (const i of view.inferred) {
    if (dismissed.includes(i.rule)) continue;
    const held = guesses.get(i.condition);
    if (!held || i.confidence > held.confidence) guesses.set(i.condition, held ? { ...i, detected: i.detected || held.detected } : i);
  }
  const inferred = [...guesses.values()];
  const forecast = view.forecast.filter((f) => secondsUntil(f.due_at, now) < DAY_S);
  const soon = forecast.filter((f) => !f.passed && secondsUntil(f.due_at, now) > 0);
  const gone = forecast.filter((f) => f.passed || secondsUntil(f.due_at, now) <= 0);
  const left = doingNow.filter((t) => !sunk.has(t.id));
  const done = doingNow.filter((t) => sunk.has(t.id));
  const bulletin = view.bulletins.next;
  // A page and a module are not siblings: "Power" and "Communications" are the modules the two
  // pages live in, and as buttons of the same size a first-time reader saw four destinations.
  const reading = view.briefing.filter((b) => b.kind !== 'module');
  const inside = view.briefing.filter((b) => b.kind === 'module');
  const empty = !inferred.length && !forecast.length && !doingNow.length && !view.briefing.length && !bulletin;

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
    <div className="stack" ref={block} data-empty={empty ? 'yes' : 'no'}>
      <section className="panel panel-signal briefing-block" aria-label="Right now">
        <div className="panel-head">
          <h2>Right now</h2>
          <Link className="btn btn-small" to="/tasks"><Icon name="plan" size={18} /><span>All of them</span></Link>
        </div>
        {/* The front door opened on two struck-through jobs and their reasons, and the first job the
            household still had to do was 598 px down a 423 px screen. What is left to do comes
            first, with its reason; what is already done is one line at the bottom. */}
        {doingNow.length === 0 ? (
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

      {(soon.length > 0 || gone.length > 0) && (
        <section className="panel briefing-block" aria-label={soon.length > 0 ? 'Coming up' : 'Already happened'}>
          {soon.length > 0 && <h2>Coming up</h2>}
          {soon.length > 0 && <ul className="list briefing-list">{soon.map((f) => <ForecastRow key={f.id} item={f} now={now} />)}</ul>}
          {/* Something that has already happened is not coming up. It keeps its place on the front
              door — the fridge is still warm — under a heading that says what it is. */}
          {gone.length > 0 && <h2>Already happened</h2>}
          {gone.length > 0 && <ul className="list briefing-list">{gone.map((f) => <ForecastRow key={f.id} item={f} now={now} />)}</ul>}
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
                  {/* Where the guess came from is a note about the box, not a caution about the
                      world: it wears the plain badge and no symbol. */}
                  {i.detected && <> <span className="badge">detected by the box</span></>}
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
          {reading.length > 0 && (
            <ul className="row briefing-reading">
              {reading.map((b) => <li key={`${b.kind}:${b.ref}`}><Link className="btn btn-small" to={briefingHref(b)}>{b.title}</Link></li>)}
            </ul>
          )}
          {/* The module a page belongs to is not a fourth place to go: it is where that page lives.
              Four buttons of the same size and style for two things to read is what this replaces. */}
          {inside.length > 0 && (
            <p className="muted briefing-inside">
              More detail in{' '}
              {inside.map((b, i) => (
                <span key={`${b.kind}:${b.ref}`}>
                  {i > 0 && (i === inside.length - 1 ? ' and ' : ', ')}
                  <Link to={briefingHref(b)}>{b.title}</Link>
                </span>
              ))}.
            </p>
          )}
          {bulletin && (
            <p className="muted"><Icon name="radio" size={18} /> Next bulletin: {bulletinWords(bulletin.station)}, {bulletinWords(bulletin.frequency)}, at {clockTime(bulletin.at)}.</p>
          )}
        </section>
      )}
    </div>
  );
}
