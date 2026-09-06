import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { api } from '../../api/client';
import type { StockCategory, StockItem } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';
import { isoToUkDate, ukDateToIso } from '../../tools/dates';

export const CATEGORIES: { id: StockCategory; title: string; unit: string; rate: string }[] = [
  { id: 'water', title: 'Water', unit: 'L', rate: '3' },
  { id: 'food', title: 'Food', unit: 'days of meals', rate: '1' },
  { id: 'fuel', title: 'Fuel', unit: 'L', rate: '' },
  { id: 'medicine', title: 'Medicine', unit: 'doses', rate: '' },
  { id: 'other', title: 'Other', unit: '', rate: '' },
];

/** "water/stored-water" -> "Water": the kit's slug as a title, until the row carries the kit's real title. */
export function kitTitle(kitItem: string): string {
  const slug = kitItem.split('/')[0].replace(/-/g, ' ');
  return slug.charAt(0).toUpperCase() + slug.slice(1);
}

export function daysBadge(item: StockItem, today = new Date()): { text: string; cls: string } | null {
  if (item.expires) {
    const exp = new Date(item.expires + 'T00:00:00');
    const days = Math.floor((exp.getTime() - today.getTime()) / 86_400_000);
    if (days < 0) return { text: 'expired', cls: 'badge badge-danger' };
    if (days <= 30 && item.days_left === null) return { text: `expires in ${days} days`, cls: 'badge badge-warn' };
  }
  if (item.days_left === null) return null;
  const text = `${item.days_left} days`;
  return { text, cls: item.days_left < 3 ? 'badge badge-danger' : item.days_left < 7 ? 'badge badge-warn' : 'badge badge-ok' };
}

function StockRow({ item, onChanged }: { item: StockItem; onChanged: () => Promise<void> }) {
  const [quantity, setQuantity] = useState(String(item.quantity));
  const [confirm, setConfirm] = useState(false);
  const save = async () => {
    const q = Number(quantity);
    if (!Number.isFinite(q) || q < 0 || q === item.quantity) { setQuantity(String(item.quantity)); return; }
    try {
      await api.updateStock(item.id, { quantity: q });
      await onChanged();
    } catch (e) {
      notify(`Could not update ${item.name}: ${errorMessage(e)}`);
      setQuantity(String(item.quantity));
    }
  };
  const remove = async () => {
    try {
      await api.deleteStock(item.id);
      await onChanged();
    } catch (e) {
      notify(`Could not remove ${item.name}: ${errorMessage(e)}`);
    }
  };
  const badge = daysBadge(item);
  return (
    <li className="stack stock-row">
      <div className="row">
        <strong>{item.name}</strong>
        {badge && <span className={badge.cls}>{badge.text}</span>}
        {item.expires && <span className="muted">use by {isoToUkDate(item.expires)}</span>}
        {item.kit_item && (
          <Link className="muted" to={`/kit/${item.kit_item.split('/')[0]}`}>From the {kitTitle(item.kit_item)} kit</Link>
        )}
      </div>
      <div className="row no-print">
        <label className="field"><span>Quantity ({item.unit || 'units'})</span>
          <input type="number" inputMode="decimal" min={0} step="any" aria-label={`Quantity of ${item.name}`} value={quantity} onChange={(e) => setQuantity(e.target.value)} onBlur={() => void save()} />
        </label>
        {item.per_person_day !== null && <span className="muted">{item.per_person_day} {item.unit} per person a day</span>}
        {confirm ? (
          <>
            <button type="button" className="btn btn-danger" onClick={() => void remove()}>Confirm remove</button>
            <button type="button" className="btn" onClick={() => setConfirm(false)}>Cancel</button>
          </>
        ) : (
          <button type="button" className="btn btn-danger" onClick={() => setConfirm(true)} aria-label={`Remove ${item.name}`}>Remove</button>
        )}
      </div>
      {item.notes && <p className="note-body">{item.notes}</p>}
    </li>
  );
}

export function Stock({ refreshKey = 0 }: { refreshKey?: number }) {
  const q = useQuery(() => api.stock(), [refreshKey], { refetchOnFocus: true });
  const [category, setCategory] = useState<StockCategory>('water');
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('L');
  const [rate, setRate] = useState('3');
  const [useBy, setUseBy] = useState('');
  const pick = (id: StockCategory) => {
    const c = CATEGORIES.find((x) => x.id === id) ?? CATEGORIES[0];
    setCategory(id);
    setUnit(c.unit);
    setRate(c.rate);
  };
  const add = async (e: FormEvent) => {
    e.preventDefault();
    const qty = Number(quantity);
    if (!name.trim() || !Number.isFinite(qty) || qty < 0) { notify('Give the item a name and a quantity of zero or more.'); return; }
    const expires = useBy.trim() === '' ? null : ukDateToIso(useBy);
    if (useBy.trim() !== '' && expires === null) { notify('Write the use-by date as day/month/year, like 06/09/2026.'); return; }
    try {
      await api.addStock({ name: name.trim(), category, quantity: qty, unit: unit.trim() || 'units',
        per_person_day: rate.trim() === '' ? null : Number(rate), expires });
      setName(''); setQuantity(''); setUseBy('');
      await q.refetch();
    } catch (err) {
      notify(`Could not add the item: ${errorMessage(err)}`);
    }
  };
  const people = q.data?.people ?? 1;
  const items = q.data?.items ?? [];
  const summary = CATEGORIES.map((c) => {
    const inCat = items.filter((i) => i.category === c.id && i.days_left !== null);
    if (!inCat.length) return null;
    return { title: c.title, days: Math.min(...inCat.map((i) => i.days_left as number)) };
  }).filter((x): x is { title: string; days: number } => x !== null);
  return (
    <section className="panel" id="stock" aria-label="Stock">
      <h2>Stock</h2>
      <p className="muted">Days left are for {people} {people === 1 ? 'person' : 'people'} at the rates you set. Water: 3 litres per person a day covers drinking and basic hygiene.</p>
      {q.error && <p className="warning">Stock unavailable: {q.error}</p>}
      {summary.length > 0 && (
        <ul className="row stock-summary" aria-label="Stock summary">
          {summary.map((s) => <li key={s.title} className="badge"><strong>{s.title}</strong> <span className={s.days < 3 ? 'warning' : ''}>{s.days} days</span></li>)}
        </ul>
      )}
      <ul className="list" aria-label="Stock items">
        {items.map((i) => <StockRow key={i.id} item={i} onChanged={q.refetch} />)}
        {q.data && items.length === 0 && <li className="muted">Nothing tracked yet.</li>}
      </ul>
      <form className="stack no-print" onSubmit={(e) => void add(e)} aria-label="Add stock">
        <div className="row">
          <label className="field"><span>Type</span>
            <select aria-label="Type" value={category} onChange={(e) => pick(e.target.value as StockCategory)}>
              {CATEGORIES.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </label>
          <label className="field"><span>Item</span><input type="text" aria-label="Item" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} placeholder="Bottled water" /></label>
        </div>
        <div className="row">
          <label className="field"><span>Quantity</span><input type="number" inputMode="decimal" min={0} step="any" aria-label="Quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label>
          <label className="field"><span>Unit</span><input type="text" aria-label="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} maxLength={20} /></label>
          <label className="field"><span>Per person a day</span><input type="number" inputMode="decimal" min={0} step="any" aria-label="Per person a day" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="leave blank to skip" /></label>
          <label className="field"><span>Use by</span><input type="text" inputMode="numeric" maxLength={10} placeholder="dd/mm/yyyy" aria-label="Use by" value={useBy} onChange={(e) => setUseBy(e.target.value)} /></label>
        </div>
        <button type="submit" className="btn btn-primary">Add item</button>
      </form>
    </section>
  );
}
