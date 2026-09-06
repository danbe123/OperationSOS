import { describe, it, expect, vi } from 'vitest';
import { useState } from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KioskProvider } from '../../src/kiosk/KioskProvider';
import { Keyboard, attachKeyboardTo, typeInto, isEditable, layoutFor, KEYBOARD_HEIGHT } from '../../src/kiosk/Keyboard';

function Form({ onSubmit }: { onSubmit: (v: string) => void }) {
  const [v, setV] = useState('');
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(v); }}>
      <input aria-label="q" value={v} onChange={(e) => setV(e.target.value)} />
      <input aria-label="pin" inputMode="numeric" />
      <output data-testid="val">{v}</output>
    </form>
  );
}

function setup(kiosk = true) {
  const onSubmit = vi.fn();
  const utils = render(<KioskProvider force={kiosk}><Form onSubmit={onSubmit} /><Keyboard /></KioskProvider>);
  return { ...utils, onSubmit, user: userEvent.setup() };
}
const key = (container: HTMLElement, k: string) => container.querySelector<HTMLElement>(`[data-skbtn="${k}"]`)!;

describe('Keyboard', () => {
  it('renders nothing outside kiosk mode', async () => {
    const { user } = setup(false);
    await user.click(screen.getByLabelText('q'));
    expect(screen.queryByTestId('keyboard')).toBeNull();
  });

  it('appears on focus, reserves the layout height it needs, and types through the native setter into a controlled input', async () => {
    const { container, user } = setup();
    await user.click(screen.getByLabelText('q'));
    expect(screen.getByTestId('keyboard')).toBeInTheDocument();
    expect(document.documentElement.style.getPropertyValue('--kb-height')).toBe(`${KEYBOARD_HEIGHT}px`);
    await user.click(key(container, 'q'));
    await user.click(key(container, '{shift}'));
    await user.click(key(container, 'A'));
    await user.click(key(container, '{space}'));
    await user.click(key(container, 'b'));
    expect(screen.getByTestId('val')).toHaveTextContent('qA b');
    await user.click(key(container, '{bksp}'));
    expect(screen.getByTestId('val')).toHaveTextContent('qA');
  });

  it('switches to the numeric pad for inputmode="numeric"', async () => {
    const { container, user } = setup();
    await user.click(screen.getByLabelText('pin'));
    expect(key(container, '7')).not.toBeNull();
    expect(container.querySelector('[data-skbtn="q"]')).toBeNull();
    await user.click(key(container, '7'));
    expect(screen.getByLabelText('pin')).toHaveValue('7');
  });

  it('Enter submits the enclosing form and Done hides the panel', async () => {
    const { container, user, onSubmit } = setup();
    await user.click(screen.getByLabelText('q'));
    await user.click(key(container, 'x'));
    await user.click(key(container, '{enter}'));
    expect(onSubmit).toHaveBeenCalledWith('x');
    await user.click(key(container, '{done}'));
    expect(screen.queryByTestId('keyboard')).toBeNull();
    expect(document.documentElement.style.getPropertyValue('--kb-height')).toBe('0px');
  });

  it('serves inputs inside another document (a reader iframe) via attachKeyboardTo', async () => {
    const { container, user } = setup();
    const iframe = document.createElement('iframe');
    document.body.appendChild(iframe);
    const doc = iframe.contentDocument!;
    doc.body.innerHTML = '<input id="inner" type="search">';
    const detach = attachKeyboardTo(doc);
    const inner = doc.getElementById('inner') as HTMLInputElement;
    await act(async () => { inner.focus(); inner.dispatchEvent(new (doc.defaultView!.FocusEvent)('focusin', { bubbles: true })); });
    expect(screen.getByTestId('keyboard')).toBeInTheDocument();
    await user.click(key(container, 'z'));
    expect(inner.value).toBe('z');
    detach();
    iframe.remove();
  });
});

describe('helpers', () => {
  it('isEditable accepts text-like inputs and textareas, rejects checkboxes, readonly and buttons', () => {
    const input = document.createElement('input');
    expect(isEditable(input)).toBe(true);
    input.type = 'checkbox';
    expect(isEditable(input)).toBe(false);
    input.type = 'text';
    input.readOnly = true;
    expect(isEditable(input)).toBe(false);
    expect(isEditable(document.createElement('textarea'))).toBe(true);
    expect(isEditable(document.createElement('button'))).toBe(false);
    expect(isEditable(null)).toBe(false);
  });
  it('layoutFor picks numeric for numeric, decimal, tel and type=number', () => {
    const i = document.createElement('input');
    expect(layoutFor(i)).toBe('default');
    i.inputMode = 'decimal';
    expect(layoutFor(i)).toBe('numeric');
    i.inputMode = '';
    i.type = 'number';
    expect(layoutFor(i)).toBe('numeric');
  });
  it('typeInto dispatches a bubbling input event', () => {
    const i = document.createElement('input');
    const seen = vi.fn();
    i.addEventListener('input', seen);
    typeInto(i, 'abc');
    expect(i.value).toBe('abc');
    expect(seen).toHaveBeenCalledTimes(1);
  });
});
