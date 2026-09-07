import { useRef, useState } from 'react';
import { Screen, Body } from '../shell/Screen';
import { BUCKET_ORDER, BUCKET_TITLE } from '../situation/conditions';
import { withTask } from '../situation/apply';
import { useSituation } from '../situation/SituationProvider';
import { TaskRow } from '../situation/TaskRow';

/** Every job the box has raised, in buckets, tickable from any phone in the house. One list. */
export function Tasks() {
  const { view, apply, error, loading } = useSituation();
  const [showDone, setShowDone] = useState(false);
  const tasks = view?.tasks ?? [];
  const outstanding = tasks.filter((t) => !t.done).length;
  const done = tasks.length - outstanding;
  /* A tick never makes a row vanish under the finger. "Show done" filters the jobs that were already
     done when this screen was opened (or when the chip was last turned off), so anything ticked here
     stays where it is, struck through, with its Undo — the same behaviour as Now and as a guide. */
  const hidden = useRef<Set<string> | null>(null);
  // Seeded on the render the list first arrives in, not in an effect: an effect would paint the done
  // jobs once and then take them away, which is the disappearing row this replaces.
  if (hidden.current === null && view) hidden.current = new Set(view.tasks.filter((t) => t.done).map((t) => t.id));
  const hideDone = () => { hidden.current = new Set(tasks.filter((t) => t.done).map((t) => t.id)); setShowDone(false); };
  const shown = showDone ? tasks : tasks.filter((t) => !hidden.current?.has(t.id));
  return (
    <Screen title="Things to do" search={false}>
      <Body>
        <div className="row">
          <p className="muted task-count">{outstanding} to do, {done} done.</p>
          {/* A filter is not a job: it wears the chip, not the same square as a task's tick. */}
          <button type="button" className={showDone ? 'chip active' : 'chip'} aria-pressed={showDone} onClick={() => (showDone ? hideDone() : setShowDone(true))}>
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
                  <TaskRow key={t.id} task={t} onChanged={(saved) => view && apply(withTask(view, saved))} />
                ))}
              </ul>
            </section>
          );
        })}
      </Body>
    </Screen>
  );
}
