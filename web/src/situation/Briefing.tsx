import { useRef, useState } from 'react';
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

/** Now, while something is happening: what to do, what is coming, what the box is guessing, and what
 * to read. Done jobs stay, struck through, until the engine retires them: a task must not vanish
 * under the finger. */
export function Briefing() {
  const { view, apply } = useSituation();
  const block = useRef<HTMLElement>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  if (!view) return null;
  const now = Date.parse(view.meta.now) || Date.now();
  const inferred = view.inferred.filter((i) => !dismissed.includes(i.rule));
  const soon = view.forecast.filter((f) => secondsUntil(f.due_at, now) < DAY_S);
  const doing = view.tasks.filter((t) => t.bucket === 'now' || t.bucket === 'hour');
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
    <section className="stack" aria-label="Briefing" ref={block}>
      {!empty && (
        <div className="row no-print"><ReadAloud id="briefing" target={block} label="Read the briefing aloud" /></div>
      )}

      <section className="panel panel-signal briefing-block" aria-label="Do this now">
        <div className="panel-head">
          <h2>Do now</h2>
          <Link className="btn btn-small" to="/tasks"><Icon name="plan" size={18} /><span>All tasks</span></Link>
        </div>
        {doing.length === 0 ? (
          <p className="muted">Nothing outstanding right now. The box adds jobs as the situation changes.</p>
        ) : (
          <ul className="list">
            {doing.map((t) => <TaskRow key={t.id} task={t} onChanged={(saved) => apply(withTask(view, saved))} />)}
          </ul>
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
                  <p className="briefing-title">
                    <span className={`badge badge-${SEVERITY_TONE[f.severity]}`}><span aria-hidden="true">{SEVERITY_SYMBOL[f.severity]}</span> {f.passed ? 'passed' : 'due'}</span>
                    {' '}{f.title} <span className="forecast-when">{countdown(f.due_at, now)}</span>
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
                <p className="briefing-title">
                  {CONDITION_INFO[i.condition].title} is probably {STATE_LABEL[i.state]}
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
        <section className="panel briefing-block" aria-label="Read this">
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
    </section>
  );
}
