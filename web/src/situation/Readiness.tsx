import { useMemo } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { stockDays } from './board';
import { useSituation } from './SituationProvider';

const COUNT_WORDS = ['no', 'one', 'two', 'three', 'four', 'five'];

function countWord(n: number): string {
  return COUNT_WORDS[n] ?? String(n);
}

/** Peacetime on Now: nothing is wrong, so the box says how long the household would last and which
 * few things would help most. No score out of a hundred and no points: a number nobody was given the
 * meaning of is not an answer. */
export function Readiness() {
  const { view } = useSituation();
  const stock = useQuery(() => api.stock(), []);
  const household = useQuery(() => api.household(), [], { refetchOnFocus: true });
  const days = useMemo(() => stockDays(stock.data?.items ?? []), [stock.data]);
  if (!view) return null;
  const gaps = view.readiness.gaps.slice(0, 5);
  const water = days.find((d) => d.category === 'water');
  const firstRun = (household.data?.length ?? 0) === 0;
  return (
    <section className="panel panel-signal" aria-label="Situation">
      <div className="panel-head">
        <h2>How ready you are</h2>
        <Link className="btn btn-small" to="/situation">Situation sheet</Link>
      </div>
      <p className="lead">
        {water ? `You have water for ${water.days} ${water.days === 1 ? 'day' : 'days'}.` : 'No water is recorded yet.'}
        {' '}
        {gaps.length > 0
          ? `${countWord(gaps.length)[0].toUpperCase()}${countWord(gaps.length).slice(1)} ${gaps.length === 1 ? 'thing' : 'things'} would help most.`
          : 'Nothing is outstanding.'}
      </p>
      {firstRun && (
        <p className="muted">New box? <Link to="/plan#household">Add who lives here</Link>, then your water and food.</p>
      )}
      {gaps.length > 0 && (
        <ul className="list now-gaps" aria-label="Gaps to close">
          {gaps.map((gap) => (
            <li key={gap.link + gap.title}>
              <Link className="task-tick gap-row" to={gap.link}>
                <Icon name="forward" size={22} />
                <span className="task-title">{gap.title}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="row">
        <Link className="btn btn-primary" to="/situation#drill"><Icon name="alert" size={18} /><span>Practise a drill</span></Link>
        <Link className="btn" to="/guides"><Icon name="book" size={18} /><span>Read the guides</span></Link>
      </p>
    </section>
  );
}
