import { useEffect, useReducer } from 'react';
import { Link } from 'react-router';
import { Icon } from '../icons';
import { describeElapsed, phaseFor } from '../tools/situation';
import { ConditionChip } from './ConditionChip';
import { HOME_CONDITION_IDS } from './conditions';
import { isEventful, useSituation } from './SituationProvider';

/** Home's first line: what is happening, how long it has been happening, and what is working.
 * In peacetime it shows how ready the household is instead. */
export function SituationStrip() {
  const { view } = useSituation();
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (!view) return null;
  const eventful = isEventful(view);
  const scenario = view.scenario;
  const gap = view.readiness.gaps[0];
  return (
    <section className={eventful ? 'situation-strip situation-strip-live' : 'situation-strip'} aria-label="Situation">
      <div className="strip-head">
        {view.meta.drill && <span className="badge badge-warn strip-drill">⚑ DRILL</span>}
        {scenario ? (
          <p className="strip-title">
            <Icon name="alert" size={20} />
            <Link to={`/s/${scenario.slug}`}>{scenario.title}</Link>
            <span className="muted">{describeElapsed(scenario.elapsed_s)}, {phaseFor(scenario.elapsed_s).title.toLowerCase()}</span>
          </p>
        ) : (
          <p className="strip-title">
            <Icon name={eventful ? 'alert' : 'check'} size={20} />
            <span>{eventful ? 'Something is off' : 'Everything is working'}</span>
          </p>
        )}
        <Link className="btn strip-open" to="/situation"><Icon name="plan" /><span>Situation sheet</span></Link>
      </div>
      {eventful ? (
        <div className="cond-chips" role="group" aria-label="What is working">
          {HOME_CONDITION_IDS.map((id) => view.conditions[id] && <ConditionChip key={id} condition={view.conditions[id]} />)}
        </div>
      ) : (
        <div className="readiness" aria-label="Readiness">
          <p className="readiness-score"><strong>{view.readiness.score}</strong><span className="muted"> / 100 ready</span></p>
          {gap ? (
            <p className="readiness-gap">Biggest gap: <Link to={gap.link}>{gap.title}</Link> <span className="muted">(worth {gap.points} points)</span></p>
          ) : (
            <p className="muted">No gaps recorded. Tap the sheet to run a drill.</p>
          )}
        </div>
      )}
    </section>
  );
}
