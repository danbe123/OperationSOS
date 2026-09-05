import { useEffect, useReducer } from 'react';
import { Link, useLocation } from 'react-router';
import { CONDITION_IDS } from '../api/types';
import { describeElapsed } from '../tools/situation';
import { ConditionChip } from './ConditionChip';
import { useSituation } from './SituationProvider';

/** Under the app bar on every screen: what is off or patchy, the clock, and the way back to the sheet.
 * Home and the sheet itself say all this already, so it stays out of their way. */
export function ChipStrip() {
  const { view } = useSituation();
  const { pathname } = useLocation();
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (!view || pathname === '/' || pathname === '/situation') return null;
  const broken = CONDITION_IDS.map((id) => view.conditions[id]).filter((c) => c && c.state !== 'working');
  const open = view.tasks.filter((t) => !t.done && (t.bucket === 'now' || t.bucket === 'hour')).length;
  if (!broken.length && !view.scenario && !view.meta.drill) return null;
  return (
    <div className="chip-strip chrome no-print" role="group" aria-label="Situation now">
      {view.meta.drill && <span className="badge badge-warn">⚑ DRILL</span>}
      {view.scenario && (
        <Link className="chip-strip-clock" to={`/s/${view.scenario.slug}`}>
          <strong>{view.scenario.title}</strong> <span className="muted">{describeElapsed(view.scenario.elapsed_s)}</span>
        </Link>
      )}
      {broken.map((c) => <ConditionChip key={c.id} condition={c} compact />)}
      {open > 0 && pathname !== '/tasks' && <Link className="cond-chip cond-warn cond-chip-compact" to="/tasks">{open} to do</Link>}
      <Link className="btn btn-chrome chip-strip-open" to="/situation">Situation</Link>
    </div>
  );
}
