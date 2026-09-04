import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from './client';
import { errorMessage } from './useQuery';
import type { Status } from './types';

export const STATUS_POLL_MS = 10_000;

type StatusContextValue = {
  status: Status | null;
  error: string | null;
  refresh: () => Promise<void>;
  /** Apply a Status returned by a POST (power mode, settings, ...) without waiting for the next poll. */
  update: (s: Status) => void;
};
const StatusContext = createContext<StatusContextValue | null>(null);

export function StatusProvider({ children, intervalMs = STATUS_POLL_MS }: { children: ReactNode; intervalMs?: number }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const s = await api.status();
      if (alive.current) {
        setStatus(s);
        setError(null);
      }
    } catch (e) {
      if (alive.current) setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void refresh();
    const id = window.setInterval(() => void refresh(), intervalMs);
    return () => {
      alive.current = false;
      window.clearInterval(id);
    };
  }, [refresh, intervalMs]);

  const update = useCallback((s: Status) => setStatus(s), []);
  const value = useMemo(() => ({ status, error, refresh, update }), [status, error, refresh, update]);
  return <StatusContext.Provider value={value}>{children}</StatusContext.Provider>;
}

export function useStatus(): StatusContextValue {
  const ctx = useContext(StatusContext);
  if (!ctx) throw new Error('useStatus must be used inside StatusProvider');
  return ctx;
}
