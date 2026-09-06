import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from './client';

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.detail;
  if (e instanceof Error) return e.message;
  return String(e);
}

export type QueryState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refetch: () => Promise<void>;
  setData: (t: T) => void;
};

/** What a list hands the section around it, so an add re-reads the list rather than remounting it:
 * a remount throws away every open editor and scroll position on the way past. */
export type Refetchable = { refetch: () => Promise<void> };

/** Fetch on mount and whenever `deps` change; optionally poll and refetch when the window regains focus. */
export function useQuery<T>(
  fn: () => Promise<T>,
  deps: readonly unknown[],
  opts: { intervalMs?: number; refetchOnFocus?: boolean } = {},
): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const seq = useRef(0);

  const refetch = useCallback(async () => {
    const mine = ++seq.current;
    try {
      const d = await fnRef.current();
      if (mine === seq.current) {
        setData(d);
        setError(null);
      }
    } catch (e) {
      if (mine === seq.current) setError(errorMessage(e));
    } finally {
      if (mine === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    void refetch();
    return () => {
      seq.current++; // drop in-flight results from the previous deps
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!opts.intervalMs) return;
    const id = window.setInterval(() => void refetch(), opts.intervalMs);
    return () => window.clearInterval(id);
  }, [opts.intervalMs, refetch]);

  useEffect(() => {
    if (!opts.refetchOnFocus) return;
    const onFocus = () => void refetch();
    const onVisible = () => {
      if (document.visibilityState === 'visible') void refetch();
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [opts.refetchOnFocus, refetch]);

  return { data, error, loading, refetch, setData };
}
