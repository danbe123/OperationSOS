import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { Place } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { parseGridRef } from './grid';

export function PlaceSearch({ onPick, onGrid }: { onPick: (p: Place) => void; onGrid: (point: { lat: number; lon: number }, text: string) => void }) {
  const [q, setQ] = useState('');
  const [items, setItems] = useState<Place[]>([]);
  const [error, setError] = useState<string | null>(null);
  const grid = useMemo(() => parseGridRef(q), [q]);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 3 || grid) {
      setItems([]);
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        setItems(await api.places(term, 10));
        setError(null);
      } catch (e) {
        setError(errorMessage(e));
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [q, grid]);

  return (
    <div className="place-search">
      <input type="search" aria-label="Place, postcode or grid reference" placeholder="Place, postcode or grid reference" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off" />
      {grid && <button type="button" className="btn btn-primary" onClick={() => onGrid(grid, q.trim().toUpperCase())}>Go to grid reference {q.trim().toUpperCase()}</button>}
      {error && <p className="warning">{error}</p>}
      <ul className="list">
        {items.map((p) => (
          <li key={`${p.name}-${p.lat}-${p.lon}`}>
            <button type="button" className="btn" onClick={() => onPick(p)}>
              {p.name} <span className="muted">{p.kind}, {p.region}{p.postcode ? ` · ${p.postcode}` : ''}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
