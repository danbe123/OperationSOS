import { useEffect, useReducer } from 'react';
import { Link, useLocation } from 'react-router';
import { CONDITION_IDS, type Condition } from '../api/types';
import { Icon } from '../icons';
import { ConditionChip } from '../situation/ConditionChip';
import { EndDrillButton } from '../situation/DrillBanner';
import { useSituation } from '../situation/SituationProvider';
import { describeElapsed } from '../tools/situation';
import { useWide } from './useWide';

/** How many condition chips the band can carry and still be one row. A real grid collapse turns six
 * or seven services off, and the band is the one element the plan calls memorable: it must not be
 * the one that grows without limit. Anything past the last chip collapses into a single control
 * that says how many more there are and opens the sheet.
 *
 * The numbers are what fits beside the rest of the row, measured at 853x480 and at 360 wide: the
 * scenario link and its clock cost about a chip and a half, and the two buttons on the right cost
 * the same again. */
export function chipBudget(wide: boolean, hasScenario: boolean): number {
  // A phone has room for the count, the jobs and the way to the sheet and nothing else: one chip
  // beside those three was cut to "Power" at 390 px. Now's own heading names the services.
  if (!wide) return 0;
  return hasScenario ? 1 : 2;
}

/** The band: the memorable element. It sits at the top of the content column whenever a scenario is
 * running, a drill is on, or anything is not working, and says the same thing on every screen — in
 * one row, at every width. In peacetime it is not rendered at all: Now shows the readiness instead. */
export function SituationBand() {
  const { view } = useSituation();
  const { pathname } = useLocation();
  const wide = useWide();
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (!view) return null;
  const broken = CONDITION_IDS.map((id) => view.conditions[id]).filter((c): c is Condition => Boolean(c) && c.state !== 'working');
  const open = view.tasks.filter((t) => !t.done && (t.bucket === 'now' || t.bucket === 'hour')).length;
  if (!broken.length && !view.scenario && !view.meta.drill) return null;
  // Every screen gets the budget: the sheet lists all ten conditions under the band and the board
  // draws them as tiles, so the band never has to carry more than fits its one row.
  const shown = broken.slice(0, chipBudget(wide, Boolean(view.scenario)));
  const rest = broken.length - shown.length;
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
      <div className="band-chips">
        {shown.map((c) => <ConditionChip key={c.id} condition={c} compact />)}
      </div>
      {rest > 0 && (
        <Link className="btn btn-small band-more" to="/situation">
          <span>{shown.length === 0 ? `${rest} ${rest === 1 ? 'thing' : 'things'} off` : `+${rest} more`}</span>
        </Link>
      )}
      {/* A count of jobs is not an eleventh thing that is wrong: it wears the small button, never a
          condition chip in condition amber. */}
      {open > 0 && pathname !== '/tasks' && (
        <Link className="btn btn-small band-jobs" to="/tasks"><Icon name="plan" size={18} /><span>{open} to do</span></Link>
      )}
      <Link className="btn btn-small band-open" to="/situation"><Icon name="plan" size={18} /><span>Situation</span></Link>
    </div>
  );
}
