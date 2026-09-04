import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, fireEvent } from '@testing-library/react';
import { useLocation } from 'react-router';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { Layout } from '../../src/router';
import { isProtectedRoute, IDLE_LEVEL, ACTIVE_LEVEL } from '../../src/kiosk/IdleOverlay';

function Where() {
  const loc = useLocation();
  return <div><span data-testid="where">{loc.pathname}{loc.search}</span><button onClick={() => underlying()}>Underlying</button></div>;
}
const underlying = vi.fn();
const routes = [{ path: '/', element: <Layout />, children: [{ index: true, element: <Where /> }, { path: '*', element: <Where /> }] }];
const MIN = 60_000;

afterEach(() => { vi.useRealTimers(); underlying.mockReset(); });

describe('isProtectedRoute', () => {
  it('protects quick cards and the Right now tab only', () => {
    expect(isProtectedRoute('/medical/card/cpr-adult', '')).toBe(true);
    expect(isProtectedRoute('/s/grid-collapse', '')).toBe(true);
    expect(isProtectedRoute('/s/grid-collapse', '?tab=right-now')).toBe(true);
    expect(isProtectedRoute('/s/grid-collapse', '?tab=first-72-hours')).toBe(false);
    expect(isProtectedRoute('/search', '?q=x')).toBe(false);
    expect(isProtectedRoute('/', '')).toBe(false);
  });
});

describe('IdleOverlay', () => {
  it('dims after idle_minutes without pointer events, consumes the first touch, restores the backlight', async () => {
    vi.useFakeTimers();
    const backlight = vi.spyOn(api, 'kioskBacklight').mockResolvedValue({ level: 10 });
    const idle = vi.spyOn(api, 'kioskIdle').mockResolvedValue({ ok: true });
    renderRoute('/search?q=x', { routes, kiosk: true });
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(4 * MIN); });
    await act(async () => { fireEvent.pointerDown(document.body); });
    await act(async () => { vi.advanceTimersByTime(4 * MIN); });
    expect(screen.queryByText('Touch to wake')).toBeNull();
    await act(async () => { vi.advanceTimersByTime(1 * MIN + 1); });
    expect(screen.getByText('Touch to wake')).toBeInTheDocument();
    expect(backlight).toHaveBeenCalledWith(IDLE_LEVEL);
    expect(idle).toHaveBeenCalledWith('idle');
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Touch to wake' })); });
    expect(screen.queryByText('Touch to wake')).toBeNull();
    expect(backlight).toHaveBeenLastCalledWith(ACTIVE_LEVEL);
    expect(idle).toHaveBeenLastCalledWith('active');
    expect(underlying).not.toHaveBeenCalled();
  });

  it('uses a darker overlay when the backlight endpoint answers 501', async () => {
    vi.useFakeTimers();
    vi.spyOn(api, 'kioskBacklight').mockRejectedValue(new ApiError(501, 'no backlight'));
    vi.spyOn(api, 'kioskIdle').mockResolvedValue({ ok: true });
    renderRoute('/search', { routes, kiosk: true });
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(5 * MIN + 1); });
    expect(screen.getByRole('button', { name: 'Touch to wake' })).toHaveClass('idle-overlay-dark');
  });

  it('returns Home after home_minutes, except on a card or the Right now tab', async () => {
    vi.useFakeTimers();
    vi.spyOn(api, 'kioskBacklight').mockResolvedValue({ level: 10 });
    vi.spyOn(api, 'kioskIdle').mockResolvedValue({ ok: true });
    const first = renderRoute('/search?q=x', { routes, kiosk: true });
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(30 * MIN + 1); });
    expect(screen.getByTestId('where')).toHaveTextContent('/');
    first.unmount();

    renderRoute('/s/grid-collapse', { routes, kiosk: true });
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(30 * MIN + 1); });
    expect(screen.getByTestId('where')).toHaveTextContent('/s/grid-collapse');
  });

  it('does nothing outside kiosk mode', async () => {
    vi.useFakeTimers();
    const backlight = vi.spyOn(api, 'kioskBacklight').mockResolvedValue({ level: 10 });
    renderRoute('/search', { routes, kiosk: false });
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(40 * MIN); });
    expect(backlight).not.toHaveBeenCalled();
    expect(screen.queryByText('Touch to wake')).toBeNull();
  });
});
