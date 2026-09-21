import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from './client';
import { errorMessage } from './useQuery';
import { onReconnect } from './connection';
import type { Status } from './types';

export const STATUS_POLL_MS = 10_000;
/** Where the box's own default theme is kept for the next boot. The pre-paint script in index.html
 * reads it (after any deliberate choice in `sos.theme`), so a box set to Mono paints black from the
 * first frame instead of flashing paper while the app fetches its own status. */
export const DEFAULT_THEME_KEY = 'sos.default_theme';

function rememberDefaultTheme(theme: Status['default_theme']): void {
  try {
    localStorage.setItem(DEFAULT_THEME_KEY, theme);
  } catch {
    // storage may be unavailable (private mode); the running app still has the status itself
  }
}

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
        rememberDefaultTheme(s.default_theme);
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

  useEffect(() => onReconnect(() => void refresh()), [refresh]);

  // A Status that came back from a POST (the theme was just changed on System, say) is as good an
  // answer as a poll's, and the next boot should paint what it says.
  const update = useCallback((s: Status) => {
    setStatus(s);
    rememberDefaultTheme(s.default_theme);
  }, []);
  const value = useMemo(() => ({ status, error, refresh, update }), [status, error, refresh, update]);
  return <StatusContext.Provider value={value}>{children}</StatusContext.Provider>;
}

export function useStatus(): StatusContextValue {
  const ctx = useContext(StatusContext);
  if (!ctx) throw new Error('useStatus must be used inside StatusProvider');
  return ctx;
}
