import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api, ApiError } from '../api/client';
import { errorMessage } from '../api/useQuery';
import type { SituationView } from '../api/types';

export const SITUATION_POLL_MS = 30_000;

type SituationContextValue = {
  view: SituationView | null;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  /** Apply a View (or a locally patched one) at once, so a tick or a state button does not wait for the poll. */
  apply: (view: SituationView) => void;
};

const SituationContext = createContext<SituationContextValue | null>(null);

/** Polls the engine's View every 30 s and whenever the window comes back. Every screen reads it from here. */
export function SituationProvider({ children, intervalMs = SITUATION_POLL_MS }: { children: ReactNode; intervalMs?: number }) {
  const [view, setView] = useState<SituationView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const v = await api.situationView();
      if (!alive.current) return;
      setView(v);
      setError(null);
    } catch (e) {
      if (!alive.current) return;
      // A box whose engine is not built yet answers 404: stay quiet rather than shout on every screen.
      setError(e instanceof ApiError && e.status === 404 ? null : errorMessage(e));
    } finally {
      if (alive.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void refresh();
    const id = window.setInterval(() => void refresh(), intervalMs);
    const onFocus = () => void refresh();
    const onVisible = () => { if (document.visibilityState === 'visible') void refresh(); };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      alive.current = false;
      window.clearInterval(id);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [refresh, intervalMs]);

  const apply = useCallback((v: SituationView) => setView(v), []);
  const value = useMemo(() => ({ view, error, loading, refresh, apply }), [view, error, loading, refresh, apply]);
  return <SituationContext.Provider value={value}>{children}</SituationContext.Provider>;
}

export function useSituation(): SituationContextValue {
  const ctx = useContext(SituationContext);
  if (!ctx) throw new Error('useSituation must be used inside SituationProvider');
  return ctx;
}

/** True when the box has something to say: a scenario is running or a condition is not working. */
export function isEventful(view: SituationView | null): boolean {
  if (!view) return false;
  if (view.scenario || view.meta.drill) return true;
  return Object.values(view.conditions).some((c) => c.state !== 'working');
}
