import { useState, type FormEvent } from 'react';
import { api } from '../../api/client';
import type { Note } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';
import { relativeTime } from '../../components/Checklist';

function NoteRow({ note, onChanged }: { note: Note; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(note.title);
  const [body, setBody] = useState(note.body);
  const [confirm, setConfirm] = useState(false);
  const save = async () => {
    try {
      await api.updateNote(note.id, { title: title.trim(), body: body.trim() });
      setEditing(false);
      await onChanged();
    } catch (e) {
      notify(`Could not save the note: ${errorMessage(e)}`);
    }
  };
  const remove = async () => {
    try {
      await api.deleteNote(note.id);
      await onChanged();
    } catch (e) {
      notify(`Could not delete the note: ${errorMessage(e)}`);
    }
  };
  if (editing) {
    return (
      <li className="stack">
        <input type="text" aria-label="Edit title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea aria-label="Edit note" rows={3} value={body} onChange={(e) => setBody(e.target.value)} />
        <div className="row"><button type="button" className="btn btn-primary" onClick={() => void save()}>Save</button><button type="button" className="btn" onClick={() => setEditing(false)}>Cancel</button></div>
      </li>
    );
  }
  return (
    <li className="stack">
      <div className="row"><strong>{note.title}</strong><span className="muted">{relativeTime(note.updated_at)}</span></div>
      <p className="note-body">{note.body}</p>
      <div className="row no-print">
        <button type="button" className="btn" onClick={() => setEditing(true)} aria-label={`Edit ${note.title}`}>Edit</button>
        {confirm ? (
          <>
            <button type="button" className="btn btn-danger" onClick={() => void remove()}>Confirm delete</button>
            <button type="button" className="btn" onClick={() => setConfirm(false)}>Cancel</button>
          </>
        ) : (
          <button type="button" className="btn btn-danger" onClick={() => setConfirm(true)} aria-label={`Delete ${note.title}`}>Delete</button>
        )}
      </div>
    </li>
  );
}

export function Notes() {
  const notesQ = useQuery(() => api.notes('note'), [], { refetchOnFocus: true });
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() && !body.trim()) return;
    try {
      await api.createNote({ kind: 'note', title: title.trim(), body: body.trim() });
      setTitle('');
      setBody('');
      await notesQ.refetch();
    } catch (err) {
      notify(`Could not add the note: ${errorMessage(err)}`);
    }
  };
  return (
    <section className="panel" id="notes">
      <h2>Shared notes</h2>
      <p className="muted">Everyone on the hotspot sees these notes.</p>
      <form className="stack no-print" onSubmit={(e) => void add(e)}>
        <label className="field"><span>Title</span><input type="text" aria-label="Title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} /></label>
        <label className="field"><span>Note</span><textarea aria-label="Note" rows={3} value={body} onChange={(e) => setBody(e.target.value)} /></label>
        <button type="submit" className="btn btn-primary">Add note</button>
      </form>
      {notesQ.error && <p className="warning">Notes unavailable: {notesQ.error}</p>}
      <ul className="list" aria-label="Notes">
        {(notesQ.data ?? []).map((n) => (
          <NoteRow key={n.id} note={n} onChanged={notesQ.refetch} />
        ))}
      </ul>
    </section>
  );
}
