import { useCallback, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { api, ApiError, setToken } from '../api/client';
import { errorMessage } from '../api/useQuery';

export function PinModal({ error, busy, onSubmit, onClose }: { error: string | null; busy: boolean; onSubmit: (pin: string) => void; onClose: () => void }) {
  const [pin, setPin] = useState('');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (pin.length > 0) onSubmit(pin);
  };
  return (
    <div className="modal-backdrop">
      <form className="modal stack" role="dialog" aria-modal="true" aria-label="Admin PIN" onSubmit={submit}>
        <h2>Admin PIN</h2>
        <p className="muted">This action is protected by the admin PIN set at install.</p>
        <input type="password" inputMode="numeric" pattern="[0-9]*" autoComplete="off" aria-label="PIN" maxLength={8} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} autoFocus disabled={busy} />
        {error && <p className="warning">{error}</p>}
        <div className="row">
          <button type="submit" className="btn btn-primary" disabled={busy || pin.length === 0}>Unlock</button>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

/**
 * Run a PIN-gated call. On 401 the PIN pad opens; a correct PIN stores the bearer token in memory (never on disk)
 * and the call is retried. Cancel resolves to undefined.
 */
export function usePinGate(): { run: <T>(fn: () => Promise<T>) => Promise<T | undefined>; dialog: ReactNode } {
  const [pendingFn, setPendingFn] = useState<(() => Promise<unknown>) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const resolver = useRef<((v: unknown) => void) | null>(null);

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    try {
      return await fn();
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401) throw e;
      setToken(null);
    }
    return new Promise<T | undefined>((resolve) => {
      resolver.current = resolve as (v: unknown) => void;
      setError(null);
      setPendingFn(() => fn);
    });
  }, []);

  const submit = async (pin: string) => {
    if (!pendingFn) return;
    setBusy(true);
    try {
      const { token } = await api.pin(pin);
      setToken(token);
      const result = await pendingFn();
      resolver.current?.(result);
      resolver.current = null;
      setPendingFn(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setError('Wrong PIN');
      else if (e instanceof ApiError && e.status === 429) setError('Too many attempts; wait a minute');
      else setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const cancel = () => {
    resolver.current?.(undefined);
    resolver.current = null;
    setPendingFn(null);
  };

  const dialog = pendingFn ? <PinModal error={error} busy={busy} onSubmit={(pin) => void submit(pin)} onClose={cancel} /> : null;
  return { run, dialog };
}
