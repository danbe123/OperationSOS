import { useEffect, useReducer, useState } from 'react';
import { api } from '../api/client';
import type { ChecklistItem } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from './Notice';

export function relativeTime(iso: string | null, now: number = Date.now()): string {
  if (!iso) return '';
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const s = Math.max(0, Math.round((now - t) / 1000));
  if (s < 60) return 'just now';
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} h ago`;
  return `${Math.round(h / 24)} days ago`;
}

export function checklistSummary(items: ChecklistItem[], now: number = Date.now()): string {
  const done = items.filter((i) => i.checked).length;
  const latest = items.map((i) => i.updated_at).filter((x): x is string => Boolean(x)).sort().at(-1) ?? null;
  return `${done} of ${items.length} done${latest ? `, last change ${relativeTime(latest, now)}` : ''}`;
}

/** The guide's shared checklist, drawn as the same task row as everything else the box asks for.
 * The parent owns the items (it refetches them); this applies optimistic ticks through `onItems`. */
export function Checklist({ slug, items, onItems }: { slug: string; items: ChecklistItem[]; onItems: (items: ChecklistItem[]) => void }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, 30_000); // keep "n min ago" fresh
    return () => window.clearInterval(id);
  }, []);

  const toggle = async (item: ChecklistItem) => {
    const before = items;
    const next = !item.checked;
    onItems(items.map((i) => (i.id === item.id ? { ...i, checked: next, updated_at: new Date().toISOString() } : i)));
    setBusy(item.id);
    try {
      onItems(await api.setChecklist(slug, item.id, next));
    } catch (e) {
      onItems(before);
      notify(`Could not save the tick: ${errorMessage(e)}`);
    } finally {
      setBusy(null);
    }
  };

  const reset = async () => {
    try {
      onItems(await api.resetChecklist(slug));
    } catch (e) {
      notify(`Could not reset the list: ${errorMessage(e)}`);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <section className="checklist" aria-label="Checklist">
      <p className="muted checklist-summary" data-testid="checklist-summary">{checklistSummary(items)}</p>
      <ul className="list task-list">
        {items.map((item) => (
          <li className={item.checked ? 'task-row task-done' : 'task-row'} key={item.id}>
            <label className="task-tick" htmlFor={`chk-${item.id}`}>
              <input type="checkbox" id={`chk-${item.id}`} checked={item.checked} disabled={busy === item.id} onChange={() => void toggle(item)} />
              <span className="task-title">
                {item.text}
                {item.checked && item.updated_at && <span className="task-time"> · ticked {relativeTime(item.updated_at)}</span>}
              </span>
            </label>
          </li>
        ))}
      </ul>
      {confirming ? (
        <div className="row no-print">
          <span>Clear all ticks on this list?</span>
          <button type="button" className="btn btn-danger" onClick={() => void reset()}>Yes, reset</button>
          <button type="button" className="btn" onClick={() => setConfirming(false)}>Cancel</button>
        </div>
      ) : (
        <button type="button" className="btn btn-small no-print" onClick={() => setConfirming(true)}>Reset list</button>
      )}
    </section>
  );
}
