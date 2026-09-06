import { useEffect, useState } from 'react';
import { Icon } from '../icons';

type Notice = { id: number; message: string };
type Listener = (n: Notice) => void;
const listeners = new Set<Listener>();
let nextId = 1;

/** Show a transient in-app notice (for example "Not in the library (needs the internet)"). */
export function notify(message: string): void {
  const n = { id: nextId++, message };
  listeners.forEach((l) => l(n));
}

export function Notices({ ttlMs = 6000 }: { ttlMs?: number }) {
  const [items, setItems] = useState<Notice[]>([]);
  useEffect(() => {
    const listener: Listener = (n) => {
      setItems((xs) => [...xs, n]);
      window.setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== n.id)), ttlMs);
    };
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, [ttlMs]);
  if (items.length === 0) return null;
  return (
    <div className="notices" role="status" aria-live="polite">
      {items.map((n) => (
        <div key={n.id} className="notice">
          <span aria-hidden="true">⚠</span>
          <span className="notice-text">{n.message}</span>
          {/* Six seconds is not long enough for everybody, and it was long enough to sit over the
              bottom bar with no way to move it. */}
          <button type="button" className="btn btn-quiet btn-small notice-close" aria-label={`Dismiss: ${n.message}`} onClick={() => setItems((xs) => xs.filter((x) => x.id !== n.id))}>
            <Icon name="close" size={18} />
          </button>
        </div>
      ))}
    </div>
  );
}
