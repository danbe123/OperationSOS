import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { api } from '../../api/client';
import type { StockCategory, StockItem, StockResponse } from '../../api/types';
import { errorMessage, useQuery } from '../../api/useQuery';
import { notify } from '../../components/Notice';
import { isoToUkDate, ukDateToIso } from '../../tools/dates';

/** How much of a thing one person gets through in a day, by what it is. The rate belongs to the
 * category, not to the tin: a household counting water at three litres a person a day should not be
 * asked the same question again every time it buys another bottle. The API holds the same defaults,
 * so a row added here without a rate is counted the same way. */
export const RATE_BY_CATEGORY: Record<MeteredCategory, { rate: number; unit: string }> = {
  water: { rate: 3, unit: 'L' },
  food: { rate: 1, unit: 'person-days' },
  medicine: { rate: 1, unit: 'days of supply' },
};

/** The order the screen counts in, and the unit each type is prefilled with. Fuel and other are
 * tracked but not rated: nobody drinks diesel at so many litres a person a day. */
export const CATEGORIES: { id: StockCategory; title: string; unit: string }[] = [
  { id: 'water', title: 'Water', unit: 'L' },
  { id: 'food', title: 'Food', unit: 'person-days' },
  { id: 'medicine', title: 'Medicine', unit: 'days of supply' },
  { id: 'fuel', title: 'Fuel', unit: 'L' },
  { id: 'other', title: 'Other', unit: '' },
];

/** The three the box meters: the ones that run out and matter when they do. */
export const METERED = ['water', 'food', 'medicine'] as const;
export type MeteredCategory = (typeof METERED)[number];
const TITLE: Record<MeteredCategory, string> = { water: 'Water', food: 'Food', medicine: 'Medicine' };
/** Two weeks: what the meters, and the kit tiers, are measured against. */
const TARGET_DAYS = 14;

function dayWords(days: number): string {
  return `${days} ${days === 1 ? 'day' : 'days'}`;
}

function peopleWords(people: number): string {
  return `${people} ${people === 1 ? 'person' : 'people'}`;
}

/** The kit a row came from, by name. The API sends the kit's real title; a row saved by an older box has
 * only the slug, so "power-and-light/torch" becomes "Power and light" rather than nothing. */
export function kitTitle(item: Pick<StockItem, 'kit_item' | 'kit_title'>): string {
  if (item.kit_title) return item.kit_title;
  const slug = (item.kit_item ?? '').split('/')[0].replace(/-/g, ' ');
  return slug.charAt(0).toUpperCase() + slug.slice(1);
}

/** What the row says about time, in one badge and at most one hint.
 *
 * The badge answers "how long would this last", and expired outranks everything: a tin that went off
 * in 2020 is worth no days whatever its arithmetic says. The hint answers a different question — "is
 * there anything here to use up soon" — and only a rated row a month from its use-by has both
 * answers to give. A rated row used to have its date swallowed by the days badge, so thirty tins
 * going off next week read "14 days" and nothing else. */
export function daysBadge(item: StockItem, today = new Date()): { text: string; cls: string; hint?: string } | null {
  // The API's own verdict first: an expired row is worth nothing whatever its arithmetic says.
  if (item.expired) return { text: 'expired', cls: 'badge badge-danger' };
  let hint: string | undefined;
  if (item.expires) {
    const exp = new Date(item.expires + 'T00:00:00');
    const days = Math.floor((exp.getTime() - today.getTime()) / 86_400_000);
    if (days < 0) return { text: 'expired', cls: 'badge badge-danger' };
    if (days <= 30) {
      if (item.days_left === null) return { text: `expires in ${days} days`, cls: 'badge badge-warn' };
      hint = `use by ${isoToUkDate(item.expires)}`;
    }
  }
  if (item.days_left === null) return null;
  const text = `${item.days_left} days`;
  return { text, hint, cls: item.days_left < 3 ? 'badge badge-danger' : item.days_left < 7 ? 'badge badge-warn' : 'badge badge-ok' };
}

/** One meter: what is held, how long the API says it lasts, and what a fortnight would take.
 * The days figure is the API's — the screen never counts a second one of its own — but the quantity
 * held is the rows', and an expired row holds nothing. Only rows kept in the category's own unit are
 * added up: forty-two meals and twelve person-days are not fifty-four of anything. A row in some
 * other unit still counts towards the days; it just cannot be added to this total. */
export function meter(c: MeteredCategory, stock: StockResponse): { title: string; held: string; days: number; need: string; fraction: number } {
  const { rate, unit } = RATE_BY_CATEGORY[c];
  const rows = stock.items.filter((i) => i.category === c && !i.expired && i.unit === unit);
  const held = rows.reduce((n, i) => n + i.quantity, 0);
  const days = stock.days[c];
  const needQty = rate * stock.people * TARGET_DAYS;
  return {
    title: TITLE[c],
    held: `${held} ${unit}`.trim(),
    days,
    need: `two weeks needs ${needQty} ${unit}`.trim(),
    fraction: Math.min(1, days / TARGET_DAYS),
  };
}

const ORDER = CATEGORIES.map((c) => c.id);

/** The list's order: the things that matter most first, and inside each the run that ends soonest.
 * A row with no run at all (a torch, a tin with no rate) sorts last rather than first. */
export function sortStock(items: StockItem[]): StockItem[] {
  return [...items].sort((a, b) => {
    const byCategory = ORDER.indexOf(a.category) - ORDER.indexOf(b.category);
    if (byCategory !== 0) return byCategory;
    if (a.days_left !== b.days_left) {
      if (a.days_left === null) return 1;
      if (b.days_left === null) return -1;
      return a.days_left - b.days_left;
    }
    return a.name.localeCompare(b.name);
  });
}

function StockMeters({ stock }: { stock: StockResponse }) {
  return (
    <ul className="meters" aria-label="Stock meters">
      {METERED.map((c) => {
        const m = meter(c, stock);
        const tone = m.fraction < 3 / TARGET_DAYS ? 'meter meter-danger' : m.fraction < 0.5 ? 'meter meter-warn' : 'meter';
        return (
          /* Three lines every time — the name, the figures, the bar. The name and the figures shared
             a line and wrapped only when they had to, so Water sat on one line, Food on two and
             Medicine on one, and the three bars a household reads down the screen were at three
             different offsets. */
          <li className={tone} key={c}>
            <strong className="meter-title">{m.title}</strong>
            <span className="muted meter-figures">{m.held} · {dayWords(m.days)} for {peopleWords(stock.people)} · {m.need}</span>
            <progress className="progress-line" value={m.days} max={TARGET_DAYS} aria-label={`${m.title} against two weeks`} />
          </li>
        );
      })}
    </ul>
  );
}

/** A row is read first and changed second: what it is, how much of it there is and how long it
 * lasts, with the fields behind Change. The date is never on the row twice — the badge says
 * "expired" or how long is left, and the row adds a quiet "use by" only when both are worth saying.
 *
 * The rate is the one thing the add form never asks for, because the category carries it; a
 * household that measures its water in five-litre bottles, or its medicine in weeks, changes it
 * here, on the row it is about. Fuel and Other have no rate to change and are offered none. */
function StockRow({ item, onChanged }: { item: StockItem; onChanged: () => Promise<void> }) {
  // What one person gets through in a day: the row's own rate, or the type's default when the row
  // has never been given one. Only the three metered types have either.
  const byCategory: { rate: number; unit: string } | undefined = RATE_BY_CATEGORY[item.category as MeteredCategory];
  const seedRate = () => (byCategory ? String(item.per_person_day ?? byCategory.rate) : '');
  const [editing, setEditing] = useState(false);
  const [quantity, setQuantity] = useState(String(item.quantity));
  const [useBy, setUseBy] = useState(item.expires ? isoToUkDate(item.expires) : '');
  const [perDay, setPerDay] = useState(seedRate);
  const [confirm, setConfirm] = useState(false);
  // Seeded when the edit opens, not once at mount: a row the box has read again since — from
  // another phone, or a kit — must not be saved back with what it said ten minutes ago.
  const open = () => {
    setQuantity(String(item.quantity));
    setUseBy(item.expires ? isoToUkDate(item.expires) : '');
    setPerDay(seedRate());
    setConfirm(false);
    setEditing(true);
  };
  const close = () => {
    setConfirm(false);
    setEditing(false);
  };
  const save = async () => {
    const q = Number(quantity);
    if (!Number.isFinite(q) || q < 0) { notify(`Write the quantity of ${item.name} as a number of zero or more.`); return; }
    // The empty string, not null: a key left out of the request tells the API to keep the date it
    // has, so null would clear the field on the screen and nothing in the box.
    const expires = useBy.trim() === '' ? '' : ukDateToIso(useBy);
    if (useBy.trim() !== '' && expires === null) { notify('Write the use-by date as day/month/year, like 06/09/2026.'); return; }
    const patch: Partial<StockItem> = {};
    if (q !== item.quantity) patch.quantity = q;
    if ((expires || null) !== item.expires) patch.expires = expires;
    if (byCategory) {
      const r = Number(perDay);
      if (!Number.isFinite(r) || r <= 0) { notify(`Write the rate for ${item.name} as a number greater than zero.`); return; }
      // Compared against what the field was seeded with, not against the stored rate: a row that has
      // never carried one shows the type's default, and leaving that default alone is not a change.
      // As numbers, not as strings: retyping 3 as "3.0" is the same rate, and sending it would write
      // a row and refetch the cupboard for nothing.
      if (r !== Number(seedRate())) patch.per_person_day = r;
    }
    if (Object.keys(patch).length === 0) { close(); return; }
    try {
      await api.updateStock(item.id, patch);
      setEditing(false);
      setConfirm(false);
      await onChanged();
    } catch (e) {
      notify(`Could not update ${item.name}: ${errorMessage(e)}`);
    }
  };
  const remove = async () => {
    try {
      await api.deleteStock(item.id);
      await onChanged();
    } catch (e) {
      notify(`Could not remove ${item.name}: ${errorMessage(e)}`);
      setConfirm(false);
    }
  };
  const badge = daysBadge(item);
  return (
    <li className="stack stock-row">
      <div className="row">
        <strong>{item.name}</strong>
        <span className="muted">{item.quantity} {item.unit || 'units'}</span>
        {badge && <span className={badge.cls}>{badge.text}</span>}
        {/* Both answers, when a row has both: how long it would last, and the date it stops counting. */}
        {badge?.hint && <span className="muted">{badge.hint}</span>}
        {item.kit_item && (
          <Link className="muted" to={`/kit/${item.kit_item.split('/')[0]}`}>From the {kitTitle(item)} kit</Link>
        )}
        {!editing && (
          <button type="button" className="btn btn-small no-print" aria-label={`Change ${item.name}`} onClick={open}>Change</button>
        )}
      </div>
      {item.notes && <p className="note-body">{item.notes}</p>}
      {editing && (
        <div className="stack no-print">
          <div className="row">
            <label className="field"><span>Quantity ({item.unit || 'units'})</span>
              <input type="number" inputMode="decimal" min={0} step="any" aria-label={`Quantity of ${item.name}`} value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            </label>
            <label className="field"><span>Use by</span>
              <input type="text" inputMode="numeric" maxLength={10} placeholder="dd/mm/yyyy" aria-label={`Use by for ${item.name}`} value={useBy} onChange={(e) => setUseBy(e.target.value)} />
            </label>
          </div>
          {byCategory && (
            <label className="field"><span>Counts as ({byCategory.unit} per person a day)</span>
              <input
                /* Save refuses a rate of zero — nothing is got through at no litres a day — so the
                   field's own floor says the same thing rather than promising an accepted nought. */
                type="number" inputMode="decimal" min={0.01} step="any"
                aria-label={`Counts as, in ${byCategory.unit} per person a day, for ${item.name}`}
                value={perDay} onChange={(e) => setPerDay(e.target.value)}
              />
            </label>
          )}
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={() => void save()}>Save</button>
            <button type="button" className="btn" onClick={close}>Cancel</button>
            {confirm ? (
              <>
                <button type="button" className="btn btn-danger" onClick={() => void remove()}>Confirm remove</button>
                <button type="button" className="btn" onClick={() => setConfirm(false)}>Keep it</button>
              </>
            ) : (
              <button type="button" className="btn btn-danger" onClick={() => setConfirm(true)} aria-label={`Remove ${item.name}`}>Remove</button>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

/** Adding something: what it is, how much, and when it goes off. No rate field — the type carries
 * the rate, and leaving it out of the request is what tells the API to use it.
 *
 * The unit follows from the type for the three the box meters, and is said rather than asked: the
 * field was prefilled and editable, so a household could type "bottles" over "L" and get a row the
 * water meter could not add up and a days figure counting six bottles as six litres. Fuel and Other
 * are not metered and keep the free-text field — jerry cans, batteries, rolls, whatever it is. */
function AddStockForm({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const [category, setCategory] = useState<StockCategory>('water');
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('L');
  const [useBy, setUseBy] = useState('');
  const categoryUnit = (CATEGORIES.find((c) => c.id === category) ?? CATEGORIES[0]).unit;
  const metered = (METERED as readonly string[]).includes(category);
  const pick = (id: StockCategory) => {
    setCategory(id);
    setUnit((CATEGORIES.find((c) => c.id === id) ?? CATEGORIES[0]).unit);
  };
  const add = async (e: FormEvent) => {
    e.preventDefault();
    const qty = Number(quantity);
    if (!name.trim() || !Number.isFinite(qty) || qty < 0) { notify('Give the item a name and a quantity of zero or more.'); return; }
    const expires = useBy.trim() === '' ? null : ukDateToIso(useBy);
    if (useBy.trim() !== '' && expires === null) { notify('Write the use-by date as day/month/year, like 06/09/2026.'); return; }
    try {
      await api.addStock({ name: name.trim(), category, quantity: qty, unit: metered ? categoryUnit : unit.trim() || 'units', expires });
      onSaved();
    } catch (err) {
      notify(`Could not add the item: ${errorMessage(err)}`);
    }
  };
  return (
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
        {metered
          ? <p className="field field-fixed"><span>Unit</span><strong>{categoryUnit}</strong></p>
          : <label className="field"><span>Unit</span><input type="text" aria-label="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} maxLength={20} /></label>}
        <label className="field"><span>Use by</span><input type="text" inputMode="numeric" maxLength={10} placeholder="dd/mm/yyyy" aria-label="Use by" value={useBy} onChange={(e) => setUseBy(e.target.value)} /></label>
      </div>
      <div className="row">
        <button type="submit" className="btn btn-primary">Add item</button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

/** The cupboard: three meters, the rows behind them, and one button. Every days figure on it is the
 * API's own, so the screen, the hub, the front door and the board all say the same number. */
export function Stock() {
  const q = useQuery(() => api.stock(), [], { refetchOnFocus: true });
  const [adding, setAdding] = useState(false);
  const stock = q.data;
  const people = stock?.people ?? 1;
  const items = sortStock(stock?.items ?? []);
  return (
    <>
      <p className="muted">
        Days are for {people} on the register. Water counts drinking and basic hygiene at 3 litres a
        person a day; food in person-days; medicine in days of supply.
      </p>
      {q.error && <p className="warning">Stock unavailable: {q.error}</p>}
      {stock && <StockMeters stock={stock} />}
      <ul className="list" aria-label="Stock items">
        {items.map((i) => <StockRow key={i.id} item={i} onChanged={q.refetch} />)}
        {stock && items.length === 0 && <li className="muted">Nothing tracked yet.</li>}
      </ul>
      {adding
        ? <AddStockForm onSaved={() => { setAdding(false); void q.refetch(); }} onCancel={() => setAdding(false)} />
        : <button type="button" className="btn no-print" onClick={() => setAdding(true)}>Add something else</button>}
    </>
  );
}
