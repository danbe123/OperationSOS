import './tools.css';
import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../../api/client';
import { useQuery } from '../../api/useQuery';
import { Screen, Body } from '../../shell/Screen';
import { doseFor, FORMS, sourceUrl, type Form, type Medicine } from '../../tools/dose';

export function Dose() {
  const [medicine, setMedicine] = useState<Medicine>('paracetamol');
  const [form, setForm] = useState<Form>('liquid-120');
  const [years, setYears] = useState('');
  const [months, setMonths] = useState('');
  const libQ = useQuery(() => api.library(), []);
  const book = useMemo(() => {
    const items = libQ.data?.categories.flatMap((c) => c.items) ?? [];
    return items.some((i) => i.id === 'nhs_uk' && i.available) ? 'nhs_uk' : 'nhs_medicines';
  }, [libQ.data]);
  const forms = (Object.keys(FORMS) as Form[]).filter((f) => FORMS[f].medicine === medicine);
  const pickMedicine = (m: Medicine) => { setMedicine(m); setForm((Object.keys(FORMS) as Form[]).find((f) => FORMS[f].medicine === m) as Form); };
  const ageMonths = years === '' && months === '' ? NaN : Number(years || 0) * 12 + Number(months || 0);
  const result = doseFor(form, ageMonths);
  return (
    <Screen title="Children's doses">
      <Body>
      <p className="warning">Life-threatening emergency: call 999. Not sure: 111. These are the NHS age bands, not a prescription.</p>
        <div className="row" role="group" aria-label="Medicine">
          <button type="button" className={medicine === 'paracetamol' ? 'btn active' : 'btn'} aria-pressed={medicine === 'paracetamol'} onClick={() => pickMedicine('paracetamol')}>Paracetamol</button>
          <button type="button" className={medicine === 'ibuprofen' ? 'btn active' : 'btn'} aria-pressed={medicine === 'ibuprofen'} onClick={() => pickMedicine('ibuprofen')}>Ibuprofen</button>
        </div>
        <label className="field"><span>Type</span>
          <select aria-label="Type" value={form} onChange={(e) => setForm(e.target.value as Form)}>
            {forms.map((f) => <option key={f} value={f}>{FORMS[f].label}</option>)}
          </select>
        </label>
        <div className="row">
          <label className="field"><span>Age: years</span><input type="number" inputMode="numeric" min={0} max={17} aria-label="Years" value={years} onChange={(e) => setYears(e.target.value)} /></label>
          <label className="field"><span>and months</span><input type="number" inputMode="numeric" min={0} max={11} aria-label="Months" value={months} onChange={(e) => setMonths(e.target.value)} /></label>
        </div>
        <section className="panel dose-result" aria-live="polite" aria-label="Dose">
          {result.ok ? (
            <>
              <p className="dose-amount">{result.amount} <span className="muted">({result.mg})</span></p>
              <p><strong>At most {result.maxPerDay}.</strong> Leave at least {result.intervalHours} hours between doses.</p>
              <ul>{result.notes.map((n) => <li key={n}>{n}</li>)}</ul>
            </>
          ) : (
            <p className="warning">{result.reason}</p>
          )}
          <p className="muted">Source: <Link to={sourceUrl(result.source, book)}>{result.source.title}</Link> (as at {result.source.as_at}). Open it to check before giving anything.</p>
        </section>
      </Body>
    </Screen>
  );
}
