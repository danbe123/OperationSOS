import { useEffect, useState } from 'react';

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
        <div key={n.id} className="notice">⚠ {n.message}</div>
      ))}
    </div>
  );
}
