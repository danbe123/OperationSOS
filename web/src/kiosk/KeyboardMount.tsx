import { lazy, Suspense, useEffect, useState } from 'react';
import { attachKeyboardTo, focusedEditable, focusListeners, isEditable, type FocusListener } from './editable';
import { useKiosk } from './KioskProvider';

/* `simple-keyboard` and its stylesheet are a third of a second of parsing on a Pi 5, and a box
 * sitting on Now never needs them. The shell mounts this instead: it listens for the first field
 * anybody focuses, and only then fetches the panel. The panel attaches its own listener when it
 * arrives and reads `document.activeElement`, so the field that opened it is still the target. */
const Keyboard = lazy(() => import('./Keyboard'));

export function KeyboardMount() {
  const kiosk = useKiosk();
  const [wanted, setWanted] = useState(false);

  useEffect(() => {
    if (!kiosk || wanted) return;
    // A field focused before this mounted — Find's own field autofocuses, and the PIN pad does the
    // same — fires no `focusin` anybody can hear, and tapping a field that already has focus fires
    // none either. So the current focus counts as the first focus.
    if (isEditable(document.activeElement) || focusedEditable()) { setWanted(true); return; }
    const listener: FocusListener = (el) => { if (el) setWanted(true); };
    focusListeners.add(listener);
    const detach = attachKeyboardTo(document);
    return () => {
      focusListeners.delete(listener);
      detach();
    };
  }, [kiosk, wanted]);

  if (!kiosk || !wanted) return null;
  return <Suspense fallback={null}><Keyboard /></Suspense>;
}
