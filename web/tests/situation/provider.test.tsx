import { describe, it, expect, vi } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { api, ApiError } from '../../src/api/client';
import { SituationProvider, isEventful, useSituation } from '../../src/situation/SituationProvider';
import { condition, makeView, powerOffView, view } from '../fixtures/api';

function Probe() {
  const { view: v, error, loading } = useSituation();
  return <span data-testid="probe">{loading ? 'loading' : `${v?.conditions.power.state ?? 'none'}/${error ?? 'no error'}`}</span>;
}

describe('SituationProvider', () => {
  it('reads the View, polls, and refetches when the window comes back', async () => {
    const situationView = vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      render(<SituationProvider intervalMs={1000}><Probe /></SituationProvider>);
      await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('working/no error'));
      situationView.mockResolvedValue(powerOffView);
      await act(async () => { vi.advanceTimersByTime(1000); });
      await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('off/'));
      situationView.mockResolvedValue(view);
      await act(async () => { window.dispatchEvent(new Event('focus')); });
      await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('working/'));
    } finally {
      vi.useRealTimers();
    }
  });

  it('stays quiet on a box whose engine is not built yet, and speaks up otherwise', async () => {
    const situationView = vi.spyOn(api, 'situationView').mockRejectedValue(new ApiError(404, 'Not Found'));
    const { unmount } = render(<SituationProvider intervalMs={60_000}><Probe /></SituationProvider>);
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('none/no error'));
    unmount();
    situationView.mockRejectedValue(new ApiError(500, 'engine broke'));
    render(<SituationProvider intervalMs={60_000}><Probe /></SituationProvider>);
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('none/engine broke'));
  });
});

describe('isEventful', () => {
  it('is true when a scenario runs, a drill runs, or anything is not working', () => {
    expect(isEventful(null)).toBe(false);
    expect(isEventful(view)).toBe(false);
    expect(isEventful(powerOffView)).toBe(true);
    expect(isEventful(makeView({ meta: { ...view.meta, drill: true } }))).toBe(true);
    expect(isEventful(makeView({ conditions: { sewage: condition('sewage', 'degraded') } as never }))).toBe(true);
  });
});
