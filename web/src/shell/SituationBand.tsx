import { useEffect, useReducer } from 'react';
import { Link, useLocation } from 'react-router';
import { CONDITION_IDS, type Condition } from '../api/types';
import { Icon } from '../icons';
import { EndDrillButton } from '../situation/DrillBanner';
import { useSituation } from '../situation/SituationProvider';
import { describeElapsed } from '../tools/situation';

/** The band: the memorable element. It sits at the top of the content column whenever a scenario is
 * running, a drill is on, or anything is not working, and says the same thing on every screen — in
 * one row, at every width. In peacetime it is not rendered at all: Now shows the readiness instead. */
export function SituationBand() {
  const { view } = useSituation();
  const { pathname } = useLocation();
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (!view) return null;
  const broken = CONDITION_IDS.map((id) => view.conditions[id]).filter((c): c is Condition => Boolean(c) && c.state !== 'working');
  const open = view.tasks.filter((t) => !t.done && (t.bucket === 'now' || t.bucket === 'hour')).length;
  if (!broken.length && !view.scenario && !view.meta.drill) return null;
  return (
    <div className="band no-print" role="group" aria-label="Situation now">
      {/* A drill costs one row: the chip that says so and the way out of it, in the band that is on
          every screen anyway. */}
      {view.meta.drill && <span className="badge badge-warn">⚑ Drill</span>}
      {view.meta.drill && <EndDrillButton />}
      {view.scenario && (
        <Link className="band-scenario" to={`/s/${view.scenario.slug}`}>
          <Icon name="alert" size={20} />
          {view.scenario.title} <span className="muted">{describeElapsed(view.scenario.elapsed_s)}</span>
        </Link>
      )}
      {/* What's wrong is a count, never a chip per service: the sheet at /situation lists all ten
          conditions, so the band never has to carry more than one number. */}
      {broken.length > 0 && (
        <Link className="btn btn-small band-off" to="/situation">{broken.length} off</Link>
      )}
      {/* A count of jobs is not an eleventh thing that is wrong: it wears the small button, never a
          condition chip in condition amber. */}
      {open > 0 && pathname !== '/tasks' && (
        <Link className="btn btn-small band-jobs" to="/tasks"><Icon name="plan" size={18} /><span>{open} to do</span></Link>
      )}
    </div>
  );
}
