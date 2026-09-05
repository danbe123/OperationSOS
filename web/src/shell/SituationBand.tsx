import { useEffect, useReducer } from 'react';
import { Link, useLocation } from 'react-router';
import { CONDITION_IDS } from '../api/types';
import { Icon } from '../icons';
import { ConditionChip } from '../situation/ConditionChip';
import { useSituation } from '../situation/SituationProvider';
import { describeElapsed } from '../tools/situation';

/** The band: the memorable element. It sits at the top of the content column whenever a scenario is
 * running, a drill is on, or anything is not working, and says the same thing on every screen. In
 * peacetime it is not rendered at all — Now shows the readiness instead. */
export function SituationBand() {
  const { view } = useSituation();
  const { pathname } = useLocation();
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (!view) return null;
  const broken = CONDITION_IDS.map((id) => view.conditions[id]).filter((c) => c && c.state !== 'working');
  const open = view.tasks.filter((t) => !t.done && (t.bucket === 'now' || t.bucket === 'hour')).length;
  if (!broken.length && !view.scenario && !view.meta.drill) return null;
  return (
    <div className="band no-print" role="group" aria-label="Situation now">
      {view.meta.drill && <span className="badge badge-warn">⚑ Drill</span>}
      {view.scenario ? (
        <Link className="band-scenario" to={`/s/${view.scenario.slug}`}>
          <Icon name="alert" size={20} />
          {view.scenario.title} <span className="muted">{describeElapsed(view.scenario.elapsed_s)}</span>
        </Link>
      ) : (
        <span className="band-label">Situation</span>
      )}
      <div className="band-chips">
        {broken.map((c) => <ConditionChip key={c.id} condition={c} compact />)}
      </div>
      {open > 0 && pathname !== '/tasks' && (
        <Link className="cond-chip cond-warn cond-chip-compact" to="/tasks">▲ {open} to do</Link>
      )}
      <Link className="btn btn-small band-open" to="/situation"><Icon name="plan" size={18} /><span>Situation</span></Link>
    </div>
  );
}
