/** What a text field is, and how the box types into one. This is the half of the on-screen keyboard
 * that has no keyboard in it: the reader iframe and the shell both need to know when a field takes
 * focus, and neither should pay for `simple-keyboard` to find out. The panel itself
 * (`kiosk/Keyboard.tsx`) is loaded the first time anybody focuses a field. */

export const KEYBOARD_HEIGHT = 224;
export type Editable = HTMLInputElement | HTMLTextAreaElement;

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

export type FocusListener = (el: Editable | null) => void;
export const focusListeners = new Set<FocusListener>();

/* The field that has focus now, if it is a field. The pad is fetched by the first focus and so it
 * arrives after the event that called for it — and that event may have happened in the reader's
 * frame, where `document.activeElement` cannot see it. This is how the pad finds out what it was
 * opened for. */
let focused: Editable | null = null;

export function focusedEditable(): Editable | null {
  return focused;
}

/** Report focus changes from any same-origin document (the app's own, or a reader iframe's). Returns a detach function. */
export function attachKeyboardTo(doc: Document): () => void {
  const onFocusIn = (e: Event) => {
    const t = e.target;
    const el = isEditable(t) ? t : null;
    focused = el;
    focusListeners.forEach((l) => l(el));
  };
  doc.addEventListener('focusin', onFocusIn);
  return () => doc.removeEventListener('focusin', onFocusIn);
}
