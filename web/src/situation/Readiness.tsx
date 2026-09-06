import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { useSituation } from './SituationProvider';

const COUNT_WORDS = ['no', 'one', 'two', 'three', 'four', 'five'];

function countWord(n: number): string {
  return COUNT_WORDS[n] ?? String(n);
}

function sentenceCase(word: string): string {
  return word[0].toUpperCase() + word.slice(1);
}

/** Peacetime on Now: nothing is wrong, so the box says which few things would help most and how to
 * start. Every number on this panel comes from the engine's readiness and is said once — the screen
 * used to make four statements about the same water, from two sources, with three different counts
 * of the household. No score out of a hundred and no points: a number nobody was given the meaning
 * of is not an answer. */
export function Readiness() {
  const { view } = useSituation();
  const household = useQuery(() => api.household(), [], { refetchOnFocus: true });
  if (!view) return null;
  const gaps = view.readiness.gaps.slice(0, 5);
  const firstRun = (household.data?.length ?? 0) === 0;
  return (
    <section className="panel panel-signal" aria-label="Situation">
      <div className="panel-head">
        <h2>How ready you are</h2>
        <Link className="btn btn-small" to="/situation">Situation sheet</Link>
      </div>
      <p className="lead">
        {gaps.length > 0
          ? `${sentenceCase(countWord(gaps.length))} ${gaps.length === 1 ? 'thing' : 'things'} would help most.`
          : 'Nothing is outstanding. Everything the box counts is in date and in stock.'}
      </p>
      {firstRun && (
        <>
          <p className="muted">New box? Start with who lives here, then your water and food.</p>
          {/* A first-run call to action is not a 20 px underline: it is a button, on its own row. */}
          <p className="row">
            <Link className="btn" to="/plan#household"><Icon name="plan" size={18} /><span>Add who lives here</span></Link>
            <Link className="btn" to="/plan#stock"><Icon name="drop" size={18} /><span>Add water, food and fuel</span></Link>
          </p>
        </>
      )}
      {gaps.length > 0 && (
        <ul className="list now-gaps" aria-label="Gaps to close">
          {gaps.map((gap) => (
            <li key={gap.link + gap.title}>
              {/* A link that navigates does not wear the shape of a job you can tick. */}
              <Link className="gap-row" to={gap.link}>
                <span className="task-title">{gap.title}</span>
                <Icon name="forward" size={22} />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="row">
        <Link className="btn btn-primary" to="/situation#drill"><Icon name="plan" size={18} /><span>Practise a drill</span></Link>
        <Link className="btn" to="/guides"><Icon name="book" size={18} /><span>Read the guides</span></Link>
      </p>
    </section>
  );
}
