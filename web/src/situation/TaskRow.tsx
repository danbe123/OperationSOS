import { useState, type KeyboardEvent } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Task } from '../api/types';
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
 * still carry it; every other list shows it as before.
 *
 * Who is doing it is a name somebody types, not a pick from a register: the box is not told who
 * lives here, and a job handed to "Alex" reads the same whether the box has ever heard of Alex.
 *
 * `assign` is off everywhere but Things to do. A briefing of five jobs with five name fields in it
 * is a form, and the front door in a power cut is not the place to fill one in; the name is typed on
 * the one screen that is about handing jobs out, and every list shows who has one already. */
export function TaskRow({ task, why = true, assign = false, onChanged }:
  { task: Task; why?: boolean; assign?: boolean; onChanged: (t: Task) => void }) {
  const [busy, setBusy] = useState(false);
  const [who, setWho] = useState('');
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
  /* Saved when the field is left or Enter is pressed, and never for an empty one: tabbing past a
     box nobody typed in must not hand the job to nobody. */
  const saveWho = () => {
    const name = who.trim();
    if (!name) return;
    void save({ person: name });
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveWho();
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
        {task.done && <TickedLine at={task.done_at} person={task.person} />}
        {task.done && armed && <UndoTick label={task.title} busy={busy} onUndo={() => void save({ done: false })} />}
        {href && <Link className="btn btn-small task-link" to={href} aria-label={`Read more: ${task.title}`}>Read more</Link>}
        {assign && !task.done && !task.person && (
          <label className="field task-person">
            <span className="muted">Who is doing this</span>
            <input
              type="text" maxLength={40} autoComplete="off" placeholder="a name"
              aria-label={`Who is doing this: ${task.title}`}
              value={who} disabled={busy}
              onChange={(e) => setWho(e.target.value)}
              onBlur={saveWho}
              onKeyDown={onKey}
            />
          </label>
        )}
        {!task.done && task.person && <span className="muted">{task.person}</span>}
      </div>
    </li>
  );
}
