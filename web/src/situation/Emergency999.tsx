import { Link } from 'react-router';
import { Icon } from '../icons';
import { useCallsHidden } from './SituationProvider';

/** The one 999 line in the box. It has two states and no others: a phone will connect, or nothing
 * will. Every screen that mentions 999 renders this and nothing else, so the same red panel never
 * carries two opposite meanings and the same fact never has two wordings.
 *
 * It is one line everywhere. The full-height panel cost a 480 px screen 88 to 96 pixels — a quarter
 * of the kiosk — on Now, on Medical, on a guide and on the doses screen, and every one of those
 * pixels is a pixel of the thing to do. The card had the compact form from round 3; the rest of the
 * box has it now.
 *
 * `onlyWhenHidden` is the second state on its own: a guide, a page, Now and the timers have no
 * business carrying a 999 line while the phones work, but the moment they do not, the warning is
 * the most important thing on the screen. */
export function Emergency999({ onlyWhenHidden = false }: { onlyWhenHidden?: boolean } = {}) {
  const hidden = useCallsHidden();
  if (hidden) {
    return (
      <p className="panel emergency-999 emergency-999-off" role="status">
        <span className="emergency-999-mark" aria-hidden="true">⚠</span>
        <span><strong>999 will not connect</strong> while both networks are down.{' '}
          <Link to="/p/no-phones">Getting help without phones</Link></span>
      </p>
    );
  }
  if (onlyWhenHidden) return null;
  return (
    <p className="panel panel-danger emergency-999">
      <Icon name="phone" size={20} />
      <span>Life-threatening emergency: call <strong>999</strong>. Urgent advice: <strong>111</strong>.</span>
    </p>
  );
}
