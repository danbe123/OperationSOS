import { Link } from 'react-router';
import { Icon } from '../icons';
import { useSituation } from './SituationProvider';

/** Peacetime on Now: nothing is wrong, so the box says so and turns the readiness gaps into the
 * to-do list, with the drill as the way to find the next gap. */
export function Readiness() {
  const { view } = useSituation();
  if (!view) return null;
  const gaps = view.readiness.gaps.slice(0, 5);
  return (
    <section className="panel panel-signal" aria-label="Situation">
      <div className="panel-head">
        <h2><Icon name="check" size={20} /> Everything is working</h2>
        <Link className="btn btn-small" to="/situation">Situation sheet</Link>
      </div>
      <p className="readiness-score" aria-label="Readiness">
        <strong>{view.readiness.score}</strong><span className="muted">out of 100 ready</span>
      </p>
      {gaps.length > 0 ? (
        <>
          <h3>Close these gaps</h3>
          <ul className="now-gaps" aria-label="Gaps to close">
            {gaps.map((gap) => (
              <li key={gap.link + gap.title}>
                <Link to={gap.link}>{gap.title}</Link>
                <span className="muted">worth {gap.points} points</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="muted">No gaps recorded. Practise a drill to find the next one.</p>
      )}
      <p className="row">
        <Link className="btn btn-primary" to="/situation#drill"><Icon name="alert" size={18} /><span>Practise a drill</span></Link>
        <Link className="btn" to="/guides"><Icon name="book" size={18} /><span>Read the guides</span></Link>
      </p>
    </section>
  );
}
