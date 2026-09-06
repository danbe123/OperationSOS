import { useCallback, useEffect, useRef, useState } from 'react';
import SimpleKeyboard from 'simple-keyboard';
import 'simple-keyboard/build/css/index.css';
import { useKiosk } from './KioskProvider';
import { attachKeyboardTo, focusedEditable, focusListeners, isEditable, KEYBOARD_HEIGHT, layoutFor, typeInto, type Editable, type FocusListener } from './editable';

/* The panel and the vendor library only. Everything the rest of the app needs to know about a text
 * field — what one is, how to type into it, who to tell when one takes focus — lives in
 * `editable.ts`, so a box that never touches a field never parses `simple-keyboard`. The names are
 * re-exported here because the reader, the shell and the tests have always asked this module for
 * them. */
export { attachKeyboardTo, isEditable, layoutFor, typeInto, KEYBOARD_HEIGHT } from './editable';
export type { Editable } from './editable';

type LayoutName = 'default' | 'shift' | 'numbers' | 'numeric';

function editAtCaret(el: Editable, insert: string, deleteBack: number): void {
  let start = el.value.length;
  let end = start;
  try {
    if (el.selectionStart !== null && el.selectionEnd !== null) {
      start = el.selectionStart;
      end = el.selectionEnd;
    }
  } catch {
    // type=number inputs throw on selection access
  }
  if (start === end && deleteBack > 0) start = Math.max(0, start - deleteBack);
  typeInto(el, el.value.slice(0, start) + insert + el.value.slice(end));
  const caret = start + insert.length;
  try {
    el.setSelectionRange(caret, caret);
  } catch {
    // unsupported for this input type
  }
}

const LAYOUTS: Record<LayoutName, string[]> = {
  default: ['q w e r t y u i o p {bksp}', 'a s d f g h j k l {enter}', '{shift} z x c v b n m , . {shift}', '{numbers} {space} {done}'],
  shift: ['Q W E R T Y U I O P {bksp}', 'A S D F G H J K L {enter}', '{shift} Z X C V B N M ! ? {shift}', '{numbers} {space} {done}'],
  numbers: ['1 2 3 4 5 6 7 8 9 0 {bksp}', "- / : ; ( ) £ & @ {enter}", "{abc} . , ? ! ' \" {abc}", '{abc} {space} {done}'],
  numeric: ['1 2 3 {bksp}', '4 5 6 {enter}', '7 8 9 {done}', '. 0 -'],
};
const DISPLAY: Record<string, string> = {
  '{bksp}': '⌫ delete', '{enter}': '↵ enter', '{shift}': '⇧ shift', '{space}': 'space',
  '{numbers}': '123', '{abc}': 'abc', '{done}': 'done ▾',
};

export function Keyboard() {
  const kiosk = useKiosk();
  const hostRef = useRef<HTMLDivElement>(null);
  const kbRef = useRef<SimpleKeyboard | null>(null);
  const [target, setTarget] = useState<Editable | null>(null);
  const [layoutName, setLayoutName] = useState<LayoutName>('default');
  const targetRef = useRef<Editable | null>(null);
  targetRef.current = target;
  const layoutRef = useRef<LayoutName>(layoutName);
  layoutRef.current = layoutName;
  const visible = kiosk && target !== null;

  useEffect(() => {
    if (!kiosk) return;
    const listener: FocusListener = (el) => setTarget(el);
    focusListeners.add(listener);
    const detach = attachKeyboardTo(document);
    // A field focused before the listener attached (Find's autoFocus, the PIN pad) never fires a
    // focusin we can hear, and the keyboard would wait for a second tap that nobody knows to make.
    // The focus that fetched this panel counts too, and it may be in the reader's own frame, where
    // this document's `activeElement` is only the iframe.
    const active = document.activeElement;
    if (isEditable(active)) setTarget(active);
    else if (focusedEditable()) setTarget(focusedEditable());
    return () => {
      focusListeners.delete(listener);
      detach();
    };
  }, [kiosk]);

  useEffect(() => {
    if (target) setLayoutName(layoutFor(target));
  }, [target]);

  useEffect(() => {
    const root = document.documentElement;
    if (visible && target) {
      root.style.setProperty('--kb-height', `${KEYBOARD_HEIGHT}px`);
      // The pad opens over whatever the field was asked to work out. A field can name what has to
      // stay in sight (`data-kb-reveal`), and that is brought up instead of the field itself.
      const selector = target.getAttribute?.('data-kb-reveal');
      const answer = selector ? target.ownerDocument.querySelector(selector) : null;
      if (answer) {
        answer.scrollIntoView({ block: 'end' });
        // …but never at the cost of the field the pad was opened for. Bringing the children's-doses
        // answer up scrolled the age box clean off the top of the screen, leaving "Enter the child's
        // age" over a pad with nowhere to type it. If the field has gone above the fold, it comes
        // back and the answer takes whatever room is left under it.
        const box = target.getBoundingClientRect?.();
        if (box && box.top < 0) target.scrollIntoView?.({ block: 'start' });
      } else {
        // 'nearest' leaves a field that is already above the pad exactly where it is, so opening the
        // keyboard never scrolls the screen's own title out of sight.
        target.scrollIntoView?.({ block: 'nearest' });
      }
    } else {
      root.style.setProperty('--kb-height', '0px');
    }
    return () => root.style.setProperty('--kb-height', '0px');
  }, [visible, target]);

  const submit = useCallback((el: Editable) => {
    if (el.tagName === 'TEXTAREA') {
      editAtCaret(el, '\n', 0);
      return;
    }
    const form = (el as HTMLInputElement).form;
    if (form) {
      form.requestSubmit();
      return;
    }
    const win = el.ownerDocument.defaultView ?? window;
    el.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  }, []);

  const handleKey = useCallback(
    (button: string) => {
      const el = targetRef.current;
      if (!el) return;
      switch (button) {
        case '{shift}': setLayoutName((l) => (l === 'shift' ? 'default' : 'shift')); return;
        case '{numbers}': setLayoutName('numbers'); return;
        case '{abc}': setLayoutName('default'); return;
        case '{done}': el.blur(); setTarget(null); return;
        case '{enter}': submit(el); return;
        case '{bksp}': editAtCaret(el, '', 1); return;
        case '{space}': editAtCaret(el, ' ', 0); return;
        default:
          editAtCaret(el, button, 0);
          if (layoutRef.current === 'shift') setLayoutName('default');
      }
    },
    [submit],
  );

  useEffect(() => {
    if (!visible || !hostRef.current) return;
    const kb = new SimpleKeyboard(hostRef.current, {
      layout: LAYOUTS,
      layoutName: layoutRef.current,
      display: DISPLAY,
      mergeDisplay: true,
      preventMouseDownDefault: true,
      theme: 'hg-theme-default sos-kb',
      onKeyPress: handleKey,
    });
    kbRef.current = kb;
    return () => {
      kb.destroy();
      kbRef.current = null;
    };
  }, [visible, handleKey]);

  useEffect(() => {
    kbRef.current?.setOptions({ layoutName });
  }, [layoutName]);

  if (!visible) return null;
  return (
    <div className="kb-panel" data-testid="keyboard" onMouseDown={(e) => e.preventDefault()}>
      <div ref={hostRef} className="sos-kb-host" />
    </div>
  );
}

/* The shell loads this module the first time a field takes focus, so the default export is the
 * panel itself. */
export default Keyboard;
