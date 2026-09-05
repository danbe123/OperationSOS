import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Person, Task } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { contentHref } from './links';

/** A job with a tick box, the reason it is here, where to read more, and who has it. */
export function TaskRow({ task, people, onChanged }: { task: Task; people?: Person[]; onChanged: (t: Task) => void }) {
  const [busy, setBusy] = useState(false);
  const href = contentHref(task.link);
  const save = async (patch: { done?: boolean; person?: string }) => {
    setBusy(true);
    try {
      onChanged(await api.setTask(task.id, patch));
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
      {task.why && <p className="task-why muted">{task.why}</p>}
      <div className="row task-meta">
        {href && <Link className="btn task-link" to={href} aria-label={`Read more: ${task.title}`}>Read more</Link>}
        {people && (
          <label className="field task-person">
            <span className="muted">Who</span>
            <select aria-label={`Who is doing: ${task.title}`} value={task.person ?? ''} disabled={busy} onChange={(e) => void save({ person: e.target.value })}>
              <option value="">Nobody yet</option>
              {people.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
          </label>
        )}
        {!people && task.person && <span className="muted">{task.person}</span>}
      </div>
    </li>
  );
}
