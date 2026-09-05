import { Link } from 'react-router';
import { Icon } from '../icons';
import { useSituation } from './SituationProvider';

/** While both phone networks are down the numbers in the content will not connect.
 * The content itself carries the alternatives (directives); this is the one-line reminder. */
export function CallsNotice() {
  const { view } = useSituation();
  if (!view || view.modes.calls !== 'hidden') return null;
  return (
    <p className="pad notice calls-notice" role="status">
      <Icon name="alert" size={18} /> <span aria-hidden="true">⚠</span> Phone numbers on this page will not connect while the phones are down.
      {' '}<Link to="/p/no-phones">Getting help without phones</Link>
    </p>
  );
}
