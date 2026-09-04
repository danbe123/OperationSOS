import { useCallback, useEffect, useRef, useState } from 'react';
import SimpleKeyboard from 'simple-keyboard';
import 'simple-keyboard/build/css/index.css';
import { useKiosk } from './KioskProvider';

export const KEYBOARD_HEIGHT = 210;
export type Editable = HTMLInputElement | HTMLTextAreaElement;
type LayoutName = 'default' | 'shift' | 'numbers' | 'numeric';

const TEXT_TYPES = new Set(['text', 'search', 'password', 'email', 'url', 'tel', 'number', '']);

/** Duck-typed so elements from another document (the reader iframe) qualify; `instanceof` fails across realms. */
export function isEditable(el: unknown): el is Editable {
  const node = el as { tagName?: unknown; type?: unknown; readOnly?: unknown; disabled?: unknown } | null;
  if (!node || typeof node.tagName !== 'string') return false;
  if (node.readOnly === true || node.disabled === true) return false;
  if (node.tagName === 'TEXTAREA') return true;
  if (node.tagName === 'INPUT') return TEXT_TYPES.has(String(node.type ?? '').toLowerCase());
  return false;
}

export function layoutFor(el: Editable): 'default' | 'numeric' {
  const mode = (el.inputMode || '').toLowerCase();
  if (mode === 'numeric' || mode === 'decimal' || mode === 'tel') return 'numeric';
  if (el.tagName === 'INPUT' && (el as HTMLInputElement).type === 'number') return 'numeric';
  return 'default';
}

/** Set the value through the element's own realm's native setter, then fire `input` so React controlled inputs update. */
export function typeInto(el: Editable, next: string): void {
  const win = el.ownerDocument.defaultView ?? window;
  const proto = el.tagName === 'TEXTAREA' ? win.HTMLTextAreaElement.prototype : win.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  if (setter) setter.call(el, next);
  else el.value = next;
  el.dispatchEvent(new win.Event('input', { bubbles: true }));
}

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

type FocusListener = (el: Editable | null) => void;
const focusListeners = new Set<FocusListener>();

/** Report focus changes from any same-origin document (the app's own, or a reader iframe's). Returns a detach function. */
export function attachKeyboardTo(doc: Document): () => void {
  const onFocusIn = (e: Event) => {
    const t = e.target;
    const el = isEditable(t) ? t : null;
    focusListeners.forEach((l) => l(el));
  };
  doc.addEventListener('focusin', onFocusIn);
  return () => doc.removeEventListener('focusin', onFocusIn);
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
      target.scrollIntoView?.({ block: 'center' });
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
