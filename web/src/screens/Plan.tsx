import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Note } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Html } from '../components/Html';
import { notify } from '../components/Notice';
import { relativeTime } from '../components/Checklist';
import { Icon } from '../icons';
import { useKiosk } from '../kiosk/KioskProvider';
import { gridRef } from '../map/grid';
import { mapQueryString } from '../map/query';

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

export function Plan() {
  const kiosk = useKiosk();
  const planQ = useQuery(() => api.page('household-plan'), []);
  const notesQ = useQuery(() => api.notes('note'), [], { refetchOnFocus: true });
  const pinsQ = useQuery(() => api.notes('pin'), [], { refetchOnFocus: true });
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
    <div className="screen">
      <AppBar title="Plan" actions={!kiosk ? <button type="button" className="btn btn-chrome" onClick={() => window.print()}><Icon name="print" /><span>Print</span></button> : undefined} />
      <h2 className="pad">Household plan</h2>
      {planQ.error && <p className="pad warning">Plan unavailable: {planQ.error}</p>}
      {planQ.data && <Html html={planQ.data.html} />}

      <h2 className="pad">Shared notes</h2>
      <p className="pad muted">Everyone on the hotspot sees these notes.</p>
      <form className="stack pad no-print" onSubmit={(e) => void add(e)}>
        <label className="field"><span>Title</span><input type="text" aria-label="Title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} /></label>
        <label className="field"><span>Note</span><textarea aria-label="Note" rows={3} value={body} onChange={(e) => setBody(e.target.value)} /></label>
        <button type="submit" className="btn btn-primary">Add note</button>
      </form>
      {notesQ.error && <p className="pad warning">Notes unavailable: {notesQ.error}</p>}
      <ul className="list" aria-label="Notes">
        {(notesQ.data ?? []).map((n) => (
          <NoteRow key={n.id} note={n} onChanged={notesQ.refetch} />
        ))}
      </ul>

      <h2 className="pad">Pins on the map</h2>
      <ul className="list" aria-label="Pins">
        {(pinsQ.data ?? []).filter((p) => p.lat !== null && p.lon !== null).map((p) => (
          <li key={p.id} className="row">
            <Link to={`/map${mapQueryString({ lat: p.lat as number, lon: p.lon as number, z: 15, overlays: [], label: p.title })}`}><Icon name="pin" /> {p.title}</Link>
            <span className="muted">{gridRef(p.lat as number, p.lon as number, 6).text}</span>
          </li>
        ))}
        {pinsQ.data && pinsQ.data.length === 0 && <li className="muted">No pins yet. Drop one from the map.</li>}
      </ul>
    </div>
  );
}
