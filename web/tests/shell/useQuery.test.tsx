import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { useQuery, errorMessage } from '../../src/api/useQuery';
import { ApiError } from '../../src/api/client';

function Probe({ fn, intervalMs, refetchOnFocus }: { fn: () => Promise<string>; intervalMs?: number; refetchOnFocus?: boolean }) {
  const q = useQuery(fn, [], { intervalMs, refetchOnFocus });
  return <div>{q.loading ? 'loading' : q.error ? `error:${q.error}` : `data:${q.data}`}</div>;
}

afterEach(() => vi.useRealTimers());

describe('useQuery', () => {
  it('loads, then exposes data', async () => {
    render(<Probe fn={async () => 'hello'} />);
    expect(screen.getByText('loading')).toBeInTheDocument();
    expect(await screen.findByText('data:hello')).toBeInTheDocument();
  });

  it('exposes the ApiError detail as the error string', async () => {
    render(<Probe fn={async () => { throw new ApiError(503, 'kiwix down'); }} />);
    expect(await screen.findByText('error:kiwix down')).toBeInTheDocument();
    expect(errorMessage(new Error('x'))).toBe('x');
    expect(errorMessage('y')).toBe('y');
  });

  it('refetches on the interval and on window focus', async () => {
    vi.useFakeTimers();
    const fn = vi.fn(async () => 'v');
    render(<Probe fn={fn} intervalMs={15_000} refetchOnFocus />);
    await act(async () => {});
    expect(fn).toHaveBeenCalledTimes(1);
    await act(async () => { vi.advanceTimersByTime(15_000); });
    expect(fn).toHaveBeenCalledTimes(2);
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    expect(fn).toHaveBeenCalledTimes(3);
  });
});
