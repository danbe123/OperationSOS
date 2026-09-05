import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { clockTime, CONDITION_INFO, countdown, secondsUntil, SEVERITY_SYMBOL, SEVERITY_TONE, STATE_LABEL } from './conditions';
import { briefingHref, contentHref } from './links';
import { useSituation } from './SituationProvider';
import { TaskRow } from './TaskRow';
import { withCondition, withTask } from './apply';

const DAY_S = 86_400;

/** Home's second block: what the box is guessing, what is about to happen, what to do now, and what to read. */
export function Briefing() {
  const { view, apply } = useSituation();
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  if (!view) return null;
  const now = Date.parse(view.meta.now) || Date.now();
  const inferred = view.inferred.filter((i) => !dismissed.includes(i.rule));
  const soon = view.forecast.filter((f) => secondsUntil(f.due_at, now) < DAY_S);
  // done ones stay, struck through, until the engine retires them: a task must not vanish under the finger
  const doing = view.tasks.filter((t) => t.bucket === 'now' || t.bucket === 'hour');
  const bulletin = view.bulletins.next;
  if (!inferred.length && !soon.length && !doing.length && !view.briefing.length && !bulletin) return null;

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
    <section className="briefing" aria-label="Briefing">
      {inferred.length > 0 && (
        <section className="briefing-block" aria-label="The box thinks">
          <h2>The box thinks</h2>
          <ul className="list briefing-list">
            {inferred.map((i) => (
              <li key={i.rule}>
                <p className="briefing-title">{CONDITION_INFO[i.condition].title} is probably {STATE_LABEL[i.state]}</p>
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

      {soon.length > 0 && (
        <section className="briefing-block" aria-label="Coming up">
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
                  {href && <Link className="btn" to={href}>Read more</Link>}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {doing.length > 0 && (
        <section className="briefing-block" aria-label="Do this now">
          <h2>Do this now</h2>
          <ul className="list task-list">
            {doing.map((t) => <TaskRow key={t.id} task={t} onChanged={(saved) => apply(withTask(view, saved))} />)}
          </ul>
          <p className="pad"><Link className="btn" to="/tasks"><Icon name="plan" /><span>All tasks</span></Link></p>
        </section>
      )}

      {view.briefing.length > 0 && (
        <section className="briefing-block" aria-label="Read this">
          <h2>Read this</h2>
          <ul className="row briefing-reading">
            {view.briefing.map((b) => <li key={`${b.kind}:${b.ref}`}><Link className="btn" to={briefingHref(b)}>{b.title}</Link></li>)}
          </ul>
        </section>
      )}

      {bulletin && (
        <p className="pad muted briefing-bulletin"><Icon name="radio" size={18} /> Next bulletin: {bulletin.station}, {bulletin.frequency}, at {clockTime(bulletin.at)}.</p>
      )}
    </section>
  );
}
