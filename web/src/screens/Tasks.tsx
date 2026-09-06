import { useState } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { BUCKET_ORDER, BUCKET_TITLE } from '../situation/conditions';
import { withTask } from '../situation/apply';
import { useSituation } from '../situation/SituationProvider';
import { TaskRow } from '../situation/TaskRow';

/** Every job the box has raised, in buckets, tickable from any phone in the house. One list. */
export function Tasks() {
  const { view, apply, error, loading } = useSituation();
  const household = useQuery(() => api.household(), []);
  const [showDone, setShowDone] = useState(false);
  const tasks = view?.tasks ?? [];
  const outstanding = tasks.filter((t) => !t.done).length;
  const shown = showDone ? tasks : tasks.filter((t) => !t.done);
  const done = tasks.length - outstanding;
  return (
    <Screen title="Things to do" search={false}>
      <Body>
        <div className="row">
          <p className="muted task-count">{outstanding} to do, {done} done.</p>
          {/* A filter is not a job: it wears the chip, not the same square as a task's tick. */}
          <button type="button" className={showDone ? 'chip active' : 'chip'} aria-pressed={showDone} onClick={() => setShowDone(!showDone)}>
            {showDone ? 'Hide done' : 'Show done'}
          </button>
        </div>
        {error && <p className="warning">Tasks unavailable: {error}</p>}
        {loading && !view && <p className="muted">Reading the situation…</p>}
        {view && shown.length === 0 && <p className="muted">Nothing to do. Jobs appear here when a condition changes or a situation starts.</p>}
        {BUCKET_ORDER.map((bucket) => {
          const list = shown.filter((t) => t.bucket === bucket);
          if (!list.length) return null;
          return (
            <section key={bucket} className="panel task-bucket" aria-label={BUCKET_TITLE[bucket]}>
              <h2>{BUCKET_TITLE[bucket]}</h2>
              <ul className="list task-list">
                {list.map((t) => (
                  <TaskRow key={t.id} task={t} people={household.data ?? []} onChanged={(saved) => view && apply(withTask(view, saved))} />
                ))}
              </ul>
            </section>
          );
        })}
      </Body>
    </Screen>
  );
}
