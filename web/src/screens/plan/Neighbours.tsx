import { useState, type FormEvent } from 'react';
import { api } from '../../api/client';
import type { Neighbour } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';
import { Icon } from '../../icons';
import { useSituation } from '../../situation/SituationProvider';

const EMPTY = { name: '', address: '', needs: '', skills: '', contacts: '', notes: '' };
type Form = typeof EMPTY;

function NeighbourForm({ initial, onSave, onCancel, label, submit }: {
  initial: Form; onSave: (n: Partial<Neighbour>) => Promise<void>; onCancel: () => void; label: string; submit: string;
}) {
  const [form, setForm] = useState(initial);
  const set = (k: keyof Form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const submitForm = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    await onSave({
      name: form.name.trim(), address: form.address.trim(), needs: form.needs.trim(),
      skills: form.skills.trim(), contacts: form.contacts.trim(), notes: form.notes.trim(),
    });
  };
  return (
    <form className="stack no-print" onSubmit={(e) => void submitForm(e)} aria-label={label}>
      <div className="row">
        <label className="field"><span>Name</span><input type="text" aria-label="Neighbour name" value={form.name} onChange={set('name')} maxLength={80} required /></label>
        <label className="field"><span>Address</span><input type="text" aria-label="Neighbour address" value={form.address} onChange={set('address')} maxLength={120} placeholder="14 Mill Lane" /></label>
      </div>
      <label className="field"><span>What they need</span><input type="text" aria-label="What they need" value={form.needs} onChange={set('needs')} placeholder="oxygen concentrator, cannot manage stairs" /></label>
      <label className="field"><span>What they can do</span><input type="text" aria-label="What they can do" value={form.skills} onChange={set('skills')} placeholder="nurse, has a generator, drives a van" /></label>
      <label className="field"><span>How to reach them</span><input type="text" aria-label="How to reach them" value={form.contacts} onChange={set('contacts')} placeholder="07700 900123, daughter Anna 07700 900456" /></label>
      <label className="field"><span>Notes</span><input type="text" aria-label="Neighbour notes" value={form.notes} onChange={set('notes')} maxLength={200} placeholder="key is with number 12" /></label>
      <div className="row">
        <button type="submit" className="btn btn-primary">{submit}</button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function NeighbourRow({ neighbour, checkOn, onChanged }: { neighbour: Neighbour; checkOn: boolean; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const save = async (n: Partial<Neighbour>) => {
    try {
      await api.updateNeighbour(neighbour.id, n);
      setEditing(false);
      await onChanged();
    } catch (e) {
      notify(`Could not save ${neighbour.name}: ${errorMessage(e)}`);
    }
  };
  const remove = async () => {
    try {
      await api.deleteNeighbour(neighbour.id);
      await onChanged();
    } catch (e) {
      notify(`Could not remove ${neighbour.name}: ${errorMessage(e)}`);
    }
  };
  if (editing) {
    return (
      <li>
        <NeighbourForm
          label={`Edit ${neighbour.name}`}
          submit="Save"
          initial={{ name: neighbour.name, address: neighbour.address, needs: neighbour.needs, skills: neighbour.skills, contacts: neighbour.contacts, notes: neighbour.notes }}
          onSave={save}
          onCancel={() => setEditing(false)}
        />
      </li>
    );
  }
  return (
    <li className="stack">
      <div className="row">
        <strong>{neighbour.name}</strong>
        {neighbour.address && <span className="muted">{neighbour.address}</span>}
        {checkOn && <span className="badge badge-warn"><span aria-hidden="true">▲</span> check on</span>}
      </div>
      {neighbour.needs && <p><span className="muted">Needs: </span>{neighbour.needs}</p>}
      {neighbour.skills && <p><span className="muted">Can do: </span>{neighbour.skills}</p>}
      {neighbour.contacts && <p><span className="muted">Reach on: </span>{neighbour.contacts}</p>}
      {neighbour.notes && <p className="muted">{neighbour.notes}</p>}
      <div className="row no-print">
        <button type="button" className="btn btn-small" onClick={() => setEditing(true)} aria-label={`Edit ${neighbour.name}`}>Edit</button>
        {confirm ? (
          <>
            <button type="button" className="btn btn-small btn-danger" onClick={() => void remove()}>Confirm remove</button>
            <button type="button" className="btn btn-small" onClick={() => setConfirm(false)}>Cancel</button>
          </>
        ) : (
          <button type="button" className="btn btn-small btn-danger" onClick={() => setConfirm(true)} aria-label={`Remove ${neighbour.name}`}>Remove</button>
        )}
      </div>
    </li>
  );
}

/** The sheet to take out with you: one page, through doors, with no screen in the way. */
export function StreetListLink() {
  return (
    <a className="btn btn-small no-print" href="/api/street-list" target="_blank" rel="noreferrer">
      <Icon name="print" size={18} /><span>Printable street list</span>
    </a>
  );
}

/** What the box has worked out the street can do, when it has worked anything out. */
export function StreetSkills() {
  const { view } = useSituation();
  const skills = view?.neighbours?.skills ?? [];
  if (skills.length === 0) return null;
  return (
    <section className="panel panel-signal" aria-label="What the street can do">
      <h3>What the street can do</h3>
      <ul className="list">
        {skills.map((s) => (
          <li key={s.rule}>
            <strong>{s.name}</strong>{s.address && <span className="muted"> · {s.address}</span>}: {s.text || s.skill}
            {s.contacts && <span className="muted"> · {s.contacts}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The street: who lives near, what they need, what they can do. Whoever the box says to check on is
 * flagged here and appears as a job on the task list. */
export function NeighboursList() {
  const q = useQuery(() => api.neighbours(), [], { refetchOnFocus: true });
  const { view } = useSituation();
  // A check_on entry is also a task, ticked on the task list; here it is only a flag on the row.
  const checkOn = new Set((view?.neighbours?.check_on ?? []).map((n) => n.name));
  return (
    <>
      {q.error && <p className="warning">Neighbours unavailable: {q.error}</p>}
      <ul className="list" aria-label="Neighbours">
        {(q.data ?? []).map((n) => <NeighbourRow key={n.id} neighbour={n} checkOn={checkOn.has(n.name)} onChanged={q.refetch} />)}
        {q.data && q.data.length === 0 && <li className="muted">Nobody on the street list yet.</li>}
      </ul>
    </>
  );
}

/** Adding a neighbour: six fields, and none of them on the screen until they are asked for. */
export function NeighboursForm({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const add = async (n: Partial<Neighbour>) => {
    try {
      await api.addNeighbour(n);
      onSaved();
    } catch (e) {
      notify(`Could not add the neighbour: ${errorMessage(e)}`);
    }
  };
  return <NeighbourForm label="Add a neighbour" submit="Add neighbour" initial={EMPTY} onSave={add} onCancel={onCancel} />;
}

/** The section as a screen shows it: what the street can do, who is on it, and one button. */
export function Neighbours() {
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(0);
  return (
    <>
      <p className="muted">Who is on the street, what they need and what they can do. The box turns this into
        jobs when something goes off, and the street list prints on one page to put through doors.</p>
      <StreetSkills />
      <NeighboursList key={added} />
      {adding
        ? <NeighboursForm onSaved={() => { setAdding(false); setAdded((n) => n + 1); }} onCancel={() => setAdding(false)} />
        : <button type="button" className="btn no-print" onClick={() => setAdding(true)}>Add a neighbour</button>}
    </>
  );
}
