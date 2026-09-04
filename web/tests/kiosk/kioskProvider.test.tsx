import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KioskProvider, useKiosk, detectKiosk, KIOSK_KEY } from '../../src/kiosk/KioskProvider';

function Probe() {
  return <span data-testid="k">{String(useKiosk())}</span>;
}

describe('detectKiosk', () => {
  it('is true for ?kiosk=1 and persists to sessionStorage', () => {
    expect(detectKiosk('?kiosk=1', sessionStorage)).toBe(true);
    expect(sessionStorage.getItem(KIOSK_KEY)).toBe('1');
  });
  it('is true on later loads from sessionStorage alone', () => {
    sessionStorage.setItem(KIOSK_KEY, '1');
    expect(detectKiosk('', sessionStorage)).toBe(true);
  });
  it('is false otherwise', () => {
    expect(detectKiosk('?q=x', sessionStorage)).toBe(false);
  });
});

describe('KioskProvider', () => {
  it('exposes the flag and marks <html class="kiosk">', () => {
    sessionStorage.setItem(KIOSK_KEY, '1');
    render(<KioskProvider><Probe /></KioskProvider>);
    expect(screen.getByTestId('k')).toHaveTextContent('true');
    expect(document.documentElement.classList.contains('kiosk')).toBe(true);
  });
  it('force overrides detection', () => {
    render(<KioskProvider force={false}><Probe /></KioskProvider>);
    expect(screen.getByTestId('k')).toHaveTextContent('false');
    expect(document.documentElement.classList.contains('kiosk')).toBe(false);
  });
});
