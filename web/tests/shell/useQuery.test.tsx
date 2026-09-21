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

describe('useQuery when the box goes away and comes back', () => {
  it('keeps what it has on screen through an outage, quietly, and refetches when the box answers', async () => {
    const { reportFailure, reportSuccess, resetConnectionForTests } = await import('../../src/api/connection');
    resetConnectionForTests();
    let calls = 0;
    const fn = vi.fn(async () => {
      calls += 1;
      if (calls === 2) throw new ApiError(0, 'The box is not answering');
      return `v${calls}`;
    });
    function Both() {
      const q = useQuery(fn, [], { intervalMs: 1000 });
      return <div>{q.data ? `data:${q.data}` : 'nodata'}|{q.error ?? 'noerror'}</div>;
    }
    vi.useFakeTimers();
    render(<Both />);
    await act(async () => {});
    expect(screen.getByText('data:v1|noerror')).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(1000); });   // the poll fails: the outage
    expect(screen.getByText('data:v1|noerror')).toBeInTheDocument();
    reportFailure(new ApiError(0, 'x'));
    reportSuccess();   // the box is back: every mounted query reads again at once
    await act(async () => {});
    expect(screen.getByText('data:v3|noerror')).toBeInTheDocument();
    resetConnectionForTests();
  });

  it('still says so when there is nothing to show, and when the failure is not the connection', async () => {
    function Bare({ fn }: { fn: () => Promise<string> }) {
      const q = useQuery(fn, []);
      return <div>{q.error ? `error:${q.error}` : q.loading ? 'loading' : `data:${q.data}`}</div>;
    }
    const { unmount } = render(<Bare fn={async () => { throw new ApiError(0, 'The box is not answering'); }} />);
    expect(await screen.findByText('error:The box is not answering')).toBeInTheDocument();
    unmount();
    let n = 0;
    function Stale() {
      const q = useQuery(async () => { n += 1; if (n === 2) throw new ApiError(500, 'Internal error'); return 'ok'; }, [], { intervalMs: 500 });
      return <div>{q.data ?? 'nodata'}|{q.error ?? 'noerror'}</div>;
    }
    vi.useFakeTimers();
    render(<Stale />);
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(500); });
    expect(screen.getByText('ok|Internal error')).toBeInTheDocument();   // a real fault is not hidden behind old data
  });
});
