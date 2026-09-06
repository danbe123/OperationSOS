import { useEffect, useReducer, useState } from 'react';
import { api } from '../api/client';
import type { ChecklistItem } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { TickedLine, UndoTick, useTickUndo } from '../situation/Tick';
import { relativeTime } from '../tools/dates';
import { notify } from './Notice';

export { relativeTime };

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
  const [undoing, setUndoing] = useState<string | null>(null);
  const { armed, arm, disarm } = useTickUndo();
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
      if (next) { setUndoing(item.id); arm(); } else { setUndoing(null); disarm(); }
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
              <span className="task-title">{item.text}</span>
            </label>
            {/* The same tick everywhere: the row stays put, only the title is struck through, and the
                who-and-when line sits under it with an Undo for ten seconds. */}
            {item.checked && (
              <div className="row task-meta">
                <TickedLine at={item.updated_at} />
                {armed && undoing === item.id && <UndoTick label={item.text} busy={busy === item.id} onUndo={() => void toggle(item)} />}
              </div>
            )}
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
