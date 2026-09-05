import { useState, type FormEvent } from 'react';
import { api } from '../../api/client';
import type { Note } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';

export function formatStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function EventRow({ event, onChanged }: { event: Note; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(event.title);
  const save = async () => {
    try {
      await api.updateNote(event.id, { title: text.trim() });
      setEditing(false);
      await onChanged();
    } catch (e) {
      notify(`Could not save the entry: ${errorMessage(e)}`);
    }
  };
  const remove = async () => {
    try {
      await api.deleteNote(event.id);
      await onChanged();
    } catch (e) {
      notify(`Could not delete the entry: ${errorMessage(e)}`);
    }
  };
  return (
    <li className="row event-row">
      <time className="muted event-time" dateTime={event.updated_at}>{formatStamp(event.updated_at)}</time>
      {editing ? (
        <>
          <input type="text" aria-label="Edit entry" value={text} onChange={(e) => setText(e.target.value)} />
          <button type="button" className="btn btn-primary" onClick={() => void save()}>Save</button>
          <button type="button" className="btn" onClick={() => setEditing(false)}>Cancel</button>
        </>
      ) : (
        <>
          <span className="event-text">{event.title}</span>
          <span className="row no-print">
            <button type="button" className="btn" onClick={() => setEditing(true)} aria-label={`Edit entry ${event.title}`}>Edit</button>
            <button type="button" className="btn btn-danger" onClick={() => void remove()} aria-label={`Delete entry ${event.title}`}>Delete</button>
          </span>
        </>
      )}
    </li>
  );
}

export function EventLog({ compact = false }: { compact?: boolean }) {
  const q = useQuery(() => api.notes('event'), [], { refetchOnFocus: true, intervalMs: 30_000 });
  const [text, setText] = useState('');
  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      await api.createNote({ kind: 'event', title: text.trim() });
      setText('');
      await q.refetch();
    } catch (err) {
      notify(`Could not log the entry: ${errorMessage(err)}`);
    }
  };
  return (
    <section className="panel" id="log">
      {!compact && <h2>Event log</h2>}
      <p className="muted">What happened and when: "water off", "heard sirens", "gave Sam 5ml paracetamol". The time is stamped for you.</p>
      <form className="row no-print" onSubmit={(e) => void add(e)} aria-label="Log an event">
        <input type="text" aria-label="What happened" className="event-input" value={text} onChange={(e) => setText(e.target.value)} maxLength={200} placeholder="What happened?" />
        <button type="submit" className="btn btn-primary">Log it</button>
      </form>
      {q.error && <p className="warning">Log unavailable: {q.error}</p>}
      <ul className="list" aria-label="Event log">
        {(q.data ?? []).map((ev) => <EventRow key={ev.id} event={ev} onChanged={q.refetch} />)}
        {q.data && q.data.length === 0 && <li className="muted">Nothing logged yet.</li>}
      </ul>
    </section>
  );
}
