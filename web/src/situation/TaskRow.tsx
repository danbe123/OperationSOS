import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Person, Task } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { contentHref } from './links';
import { TickedLine, UndoTick, useTickUndo } from './Tick';

/** A job with a tick box, the reason it is here, where to read more, and who has it. A ticked job
 * stays where it is, struck through, with an Undo for ten seconds: the same behaviour on Now, on
 * Things to do and on a guide.
 *
 * `why` is three lines of explanation, and four of them are most of a 480 px screen. The front door
 * shows it for the job at the top and turns it off for the rest, where "Read more" and Things to do
 * still carry it; every other list shows it as before. */
export function TaskRow({ task, people, why = true, onChanged }: { task: Task; people?: Person[]; why?: boolean; onChanged: (t: Task) => void }) {
  const [busy, setBusy] = useState(false);
  const { armed, arm, disarm } = useTickUndo();
  const href = contentHref(task.link);
  const save = async (patch: { done?: boolean; person?: string }) => {
    setBusy(true);
    try {
      onChanged(await api.setTask(task.id, patch));
      if (patch.done === true) arm();
      if (patch.done === false) disarm();
    } catch (e) {
      notify(`Could not save "${task.title}": ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className={task.done ? 'task-row task-done' : 'task-row'}>
      <label className="task-tick">
        <input type="checkbox" checked={task.done} disabled={busy} onChange={(e) => void save({ done: e.target.checked })} />
        <span className="task-title">{task.title}</span>
      </label>
      {why && task.why && <p className="task-why muted">{task.why}</p>}
      <div className="row task-meta">
        {/* The "who and when" line is never struck through; only the title is. */}
        {task.done && <TickedLine at={task.done_at} person={people ? null : task.person} />}
        {task.done && armed && <UndoTick label={task.title} busy={busy} onUndo={() => void save({ done: false })} />}
        {href && <Link className="btn btn-small task-link" to={href} aria-label={`Read more: ${task.title}`}>Read more</Link>}
        {people && (
          <label className="field task-person">
            <span className="muted">Who</span>
            <select aria-label={`Who is doing: ${task.title}`} value={task.person ?? ''} disabled={busy} onChange={(e) => void save({ person: e.target.value })}>
              <option value="">Nobody yet</option>
              {people.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
          </label>
        )}
        {!people && task.person && !task.done && <span className="muted">{task.person}</span>}
      </div>
    </li>
  );
}
