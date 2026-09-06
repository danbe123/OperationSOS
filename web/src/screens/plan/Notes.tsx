import { useImperativeHandle, useRef, useState, type FormEvent, type Ref } from 'react';
import { api } from '../../api/client';
import type { Note } from '../../api/types';
import { errorMessage, useQuery, type Refetchable } from '../../api/useQuery';
import { notify } from '../../components/Notice';
import { relativeTime } from '../../components/Checklist';
import { PinRow } from './Pins';

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
      <li className="stack no-print">
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

/** Notes newest first, and on a screen that asks for them the pins alongside: both are somebody
 * writing something down, and reading them in two lists means reading the same day twice.
 *
 * Two requests for the two kinds this list shows, rather than one for every note in the box and a
 * client-side sieve: the event log on a busy day is hundreds of rows, and none of them belong here. */
export function NotesList({ pins = false, ref }: { pins?: boolean; ref?: Ref<Refetchable> } = {}) {
  const notesQ = useQuery(() => api.notes('note'), [], { refetchOnFocus: true });
  const pinsQ = useQuery(() => (pins ? api.notes('pin') : Promise.resolve<Note[]>([])), [pins], { refetchOnFocus: true });
  const refetch = async () => {
    await Promise.all([notesQ.refetch(), pinsQ.refetch()]);
  };
  useImperativeHandle(ref, () => ({ refetch }));
  const error = notesQ.error ?? pinsQ.error;
  const loaded = notesQ.data !== null && pinsQ.data !== null;
  const rows = [...(notesQ.data ?? []), ...(pinsQ.data ?? [])]
    .filter((n) => n.kind === 'note' || (n.kind === 'pin' && n.lat !== null && n.lon !== null))
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  return (
    <>
      {error && <p className="warning">Notes unavailable: {error}</p>}
      <ul className="list" aria-label={pins ? 'Notes and pins' : 'Notes'}>
        {rows.map((n) => (n.kind === 'pin'
          ? <PinRow key={`pin-${n.id}`} pin={n} />
          : <NoteRow key={n.id} note={n} onChanged={refetch} />))}
        {loaded && rows.length === 0 && <li className="muted">Nothing written down yet.</li>}
      </ul>
    </>
  );
}

/** A title and a few lines, behind a button. Pins are not written here: one is dropped on the map,
 * where the spot being pinned is the thing on the screen. */
export function NotesForm({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() && !body.trim()) return;
    try {
      await api.createNote({ kind: 'note', title: title.trim(), body: body.trim() });
      onSaved();
    } catch (err) {
      notify(`Could not add the note: ${errorMessage(err)}`);
    }
  };
  return (
    <form className="stack no-print" onSubmit={(e) => void add(e)} aria-label="Add a note">
      <label className="field"><span>Title</span><input type="text" aria-label="Title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} autoFocus /></label>
      <label className="field"><span>Note</span><textarea aria-label="Note" rows={3} value={body} onChange={(e) => setBody(e.target.value)} /></label>
      <div className="row">
        <button type="submit" className="btn btn-primary">Add note</button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

/** The section as a screen shows it: what has been written down, and one button. Adding one asks the
 * list to read itself again, so the new note is on the screen that wrote it; remounting the list
 * instead would throw away every note somebody had open for editing beside it. */
export function Notes({ pins = false }: { pins?: boolean } = {}) {
  const [adding, setAdding] = useState(false);
  const list = useRef<Refetchable>(null);
  return (
    <>
      <p className="muted">Everyone on the hotspot sees these{pins ? ' notes and the pins on the map' : ' notes'}.</p>
      <NotesList ref={list} pins={pins} />
      {adding
        ? <NotesForm onSaved={() => { setAdding(false); void list.current?.refetch(); }} onCancel={() => setAdding(false)} />
        : <button type="button" className="btn no-print" onClick={() => setAdding(true)}>Add a note</button>}
    </>
  );
}
