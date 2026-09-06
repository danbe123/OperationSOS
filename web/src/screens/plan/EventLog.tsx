import { useState, type FormEvent } from 'react';
import { api } from '../../api/client';
import type { Note } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';
import { eventTitle } from '../../api/words';

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
          <span className="event-text">{eventTitle(event.title)}</span>
          <span className="row no-print">
            <button type="button" className="btn" onClick={() => setEditing(true)} aria-label={`Edit entry ${event.title}`}>Edit</button>
            <button type="button" className="btn btn-danger" onClick={() => void remove()} aria-label={`Delete entry ${event.title}`}>Delete</button>
          </span>
        </>
      )}
    </li>
  );
}

/** The log, newest first: what happened and when, with a way to correct a mistyped entry. */
export function EventLogList() {
  const q = useQuery(() => api.notes('event'), [], { refetchOnFocus: true, intervalMs: 30_000 });
  return (
    <>
      {q.error && <p className="warning">Log unavailable: {q.error}</p>}
      <ul className="list" aria-label="Event log">
        {(q.data ?? []).map((ev) => <EventRow key={ev.id} event={ev} onChanged={q.refetch} />)}
        {q.data && q.data.length === 0 && <li className="muted">Nothing logged yet.</li>}
      </ul>
    </>
  );
}

/** One line, one button: the box stamps the time. */
export function EventLogForm({ onAdded, onCancel }: { onAdded: () => void; onCancel?: () => void }) {
  const [text, setText] = useState('');
  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      await api.createNote({ kind: 'event', title: text.trim() });
      setText('');
      onAdded();
    } catch (err) {
      notify(`Could not log the entry: ${errorMessage(err)}`);
    }
  };
  return (
    <form className="row no-print" onSubmit={(e) => void add(e)} aria-label="Log an event">
      <input type="text" aria-label="What happened" className="event-input" value={text} onChange={(e) => setText(e.target.value)} maxLength={200} placeholder="What happened?" autoFocus />
      <button type="submit" className="btn btn-primary">Log it</button>
      {onCancel && <button type="button" className="btn" onClick={onCancel}>Cancel</button>}
    </form>
  );
}

/** The log as a screen shows it: the entries, and the form behind a button. A form standing open
 * above the entries is a form on every screen the log appears on, and the log is read far more
 * often than it is written to. The list is keyed on the count of entries added here, so logging
 * one reads the log back rather than leaving the new line off the screen that just wrote it. */
export function EventLog() {
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(0);
  return (
    <>
      <p className="muted">What happened and when: "water off", "heard sirens", "gave Sam 5ml paracetamol". The time is stamped for you.</p>
      {adding
        ? <EventLogForm onAdded={() => { setAdding(false); setAdded((n) => n + 1); }} onCancel={() => setAdding(false)} />
        : <button type="button" className="btn no-print" onClick={() => setAdding(true)}>Add an entry</button>}
      <EventLogList key={added} />
    </>
  );
}
