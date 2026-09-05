import { useState, type FormEvent } from 'react';
import { api } from '../../api/client';
import type { Person } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';

const EMPTY = { name: '', age: '', needs: '', medications: '', contacts: '' };

function PersonForm({ initial, onSave, onCancel, label }: { initial: typeof EMPTY; onSave: (p: Partial<Person>) => Promise<void>; onCancel?: () => void; label: string }) {
  const [form, setForm] = useState(initial);
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    await onSave({ name: form.name.trim(), age: form.age === '' ? null : Number(form.age), needs: form.needs.trim(), medications: form.medications.trim(), contacts: form.contacts.trim() });
    if (!onCancel) setForm(EMPTY);
  };
  return (
    <form className="stack no-print person-form" onSubmit={(e) => void submit(e)} aria-label={label}>
      <div className="row">
        <label className="field"><span>Name</span><input type="text" aria-label="Name" value={form.name} onChange={set('name')} maxLength={80} required /></label>
        <label className="field"><span>Age</span><input type="number" aria-label="Age" inputMode="numeric" min={0} max={120} value={form.age} onChange={set('age')} /></label>
      </div>
      <label className="field"><span>Medical needs</span><input type="text" aria-label="Medical needs" value={form.needs} onChange={set('needs')} placeholder="asthma, insulin-dependent, wheelchair" /></label>
      <label className="field"><span>Medications</span><input type="text" aria-label="Medications" value={form.medications} onChange={set('medications')} placeholder="salbutamol inhaler, 2 puffs when needed" /></label>
      <label className="field"><span>Contacts</span><input type="text" aria-label="Contacts" value={form.contacts} onChange={set('contacts')} placeholder="next of kin, GP, school" /></label>
      <div className="row"><button type="submit" className="btn btn-primary">{onCancel ? 'Save' : 'Add person'}</button>{onCancel && <button type="button" className="btn" onClick={onCancel}>Cancel</button>}</div>
    </form>
  );
}

function PersonRow({ person, onChanged }: { person: Person; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const save = async (p: Partial<Person>) => {
    try {
      await api.updatePerson(person.id, p);
      setEditing(false);
      await onChanged();
    } catch (e) {
      notify(`Could not save ${person.name}: ${errorMessage(e)}`);
    }
  };
  const remove = async () => {
    try {
      await api.deletePerson(person.id);
      await onChanged();
    } catch (e) {
      notify(`Could not remove ${person.name}: ${errorMessage(e)}`);
    }
  };
  if (editing) {
    return <li><PersonForm label={`Edit ${person.name}`} initial={{ name: person.name, age: person.age === null ? '' : String(person.age), needs: person.needs, medications: person.medications, contacts: person.contacts }} onSave={save} onCancel={() => setEditing(false)} /></li>;
  }
  return (
    <li className="stack">
      <div className="row"><strong>{person.name}</strong>{person.age !== null && <span className="muted">age {person.age}</span>}</div>
      {person.needs && <p className="note-body"><span className="muted">Needs: </span>{person.needs}</p>}
      {person.medications && <p className="note-body"><span className="muted">Medications: </span>{person.medications}</p>}
      {person.contacts && <p className="note-body"><span className="muted">Contacts: </span>{person.contacts}</p>}
      <div className="row no-print">
        <button type="button" className="btn" onClick={() => setEditing(true)} aria-label={`Edit ${person.name}`}>Edit</button>
        {confirm ? (
          <>
            <button type="button" className="btn btn-danger" onClick={() => void remove()}>Confirm remove</button>
            <button type="button" className="btn" onClick={() => setConfirm(false)}>Cancel</button>
          </>
        ) : (
          <button type="button" className="btn btn-danger" onClick={() => setConfirm(true)} aria-label={`Remove ${person.name}`}>Remove</button>
        )}
      </div>
    </li>
  );
}

export function Household({ onChanged }: { onChanged?: () => void } = {}) {
  const q = useQuery(() => api.household(), [], { refetchOnFocus: true });
  const refetch = async () => { await q.refetch(); onChanged?.(); };
  const add = async (p: Partial<Person>) => {
    try {
      await api.addPerson(p);
      await refetch();
    } catch (e) {
      notify(`Could not add the person: ${errorMessage(e)}`);
    }
  };
  return (
    <section className="panel" id="household">
      <h2>Household</h2>
      <p className="muted">Who lives here, what they need and who to call. Medical needs also show on the Medical screen.</p>
      {q.error && <p className="warning">Household unavailable: {q.error}</p>}
      <ul className="list" aria-label="Household">
        {(q.data ?? []).map((p) => <PersonRow key={p.id} person={p} onChanged={refetch} />)}
        {q.data && q.data.length === 0 && <li className="muted">Nobody registered yet. Stock figures assume one person until you add people.</li>}
      </ul>
      <PersonForm label="Add a person" initial={EMPTY} onSave={add} />
    </section>
  );
}
