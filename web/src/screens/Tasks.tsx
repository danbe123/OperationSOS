import { useState } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { BUCKET_ORDER, BUCKET_TITLE } from '../situation/conditions';
import { withTask } from '../situation/apply';
import { useSituation } from '../situation/SituationProvider';
import { TaskRow } from '../situation/TaskRow';

/** Every job the engine has raised, in buckets, tickable from any phone in the house. */
export function Tasks() {
  const { view, apply, error, loading } = useSituation();
  const household = useQuery(() => api.household(), []);
  const [showDone, setShowDone] = useState(false);
  const tasks = view?.tasks ?? [];
  const outstanding = tasks.filter((t) => !t.done).length;
  const shown = showDone ? tasks : tasks.filter((t) => !t.done);
  const done = tasks.length - outstanding;
  return (
    <div className="screen tasks-screen">
      <AppBar title="Tasks" search={false} actions={<span className="badge task-count">{outstanding} to do</span>} />
      <div className="pad row tasks-filter">
        <p className="muted">{outstanding} to do, {done} done.</p>
        <label className="check-row">
          <input type="checkbox" checked={showDone} onChange={(e) => setShowDone(e.target.checked)} />
          <span>Show done</span>
        </label>
      </div>
      {error && <p className="pad warning">Tasks unavailable: {error}</p>}
      {loading && !view && <p className="pad muted">Reading the situation…</p>}
      {view && shown.length === 0 && <p className="pad muted">Nothing to do. Tasks appear when a condition changes or a situation starts.</p>}
      {BUCKET_ORDER.map((bucket) => {
        const list = shown.filter((t) => t.bucket === bucket);
        if (!list.length) return null;
        return (
          <section key={bucket} className="task-bucket" aria-label={BUCKET_TITLE[bucket]}>
            <h2 className="pad">{BUCKET_TITLE[bucket]}</h2>
            <ul className="list task-list">
              {list.map((t) => (
                <TaskRow key={t.id} task={t} people={household.data ?? []} onChanged={(saved) => view && apply(withTask(view, saved))} />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
