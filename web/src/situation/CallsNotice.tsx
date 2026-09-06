import { Link } from 'react-router';
import { useSituation } from './SituationProvider';

/** While both phone networks are down the numbers inside a guide will not connect. The content
 * itself carries the alternatives; this is the one-line reminder, and it draws its warning symbol
 * once. Screens that render the 999 line render that instead of this. */
export function CallsNotice() {
  const { view } = useSituation();
  if (!view || view.modes.calls !== 'hidden') return null;
  return (
    <p className="notice calls-notice" role="status">
      <span aria-hidden="true">⚠</span> Phone numbers on this page will not connect while the phones are down.
      {' '}<Link to="/p/no-phones">Getting help without phones</Link>
    </p>
  );
}
