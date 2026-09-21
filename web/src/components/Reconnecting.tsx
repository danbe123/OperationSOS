import { useEffect, useState } from 'react';
import { useBoxDown } from '../api/connection';
import { Icon } from '../icons';

/** How long the box must have been silent before the screen says so: sos-api restarts in about three
 * seconds and most outages end before anybody would want to read a notice about them. */
export const RECONNECTING_AFTER_MS = 2000;

/** The one cue for "the box is not answering": a small pill in the corner, not a dialog, not in the way of
 * a tap, and gone by itself the moment the box answers. The screens keep what they have and say nothing
 * more; `api/connection.ts` looks for the box and tells every query to read again. */
export function Reconnecting() {
  const down = useBoxDown();
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!down) {
      setShown(false);
      return;
    }
    const timer = window.setTimeout(() => setShown(true), RECONNECTING_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [down]);
  if (!shown) return null;
  return (
    <div className="reconnecting no-print" role="status" aria-live="polite" data-testid="reconnecting">
      <Icon name="refresh" size={18} />
      <span>Reconnecting to the box…</span>
    </div>
  );
}
