import './tools.css';
import { useState } from 'react';
import { Link } from 'react-router';
import { Screen, Body } from '../../shell/Screen';
import { batteryHours, formatHours, generatorHours, rationDays, solarDailyWh } from '../../tools/calc';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function Num({ label, value, onChange, unit }: { label: string; value: string; onChange: (v: string) => void; unit?: string }) {
  return (
    <label className="field"><span>{label}{unit ? ` (${unit})` : ''}</span>
      <input type="number" inputMode="decimal" min={0} step="any" aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

const INVALID = 'Enter numbers above zero.';

function Generator() {
  const [tank, setTank] = useState('20');
  const [rate, setRate] = useState('1.2');
  const h = generatorHours(Number(tank), Number(rate));
  return (
    <section className="panel" aria-label="Generator runtime">
      <h3>Generator runtime</h3>
      <div className="row"><Num label="Fuel in the tank and cans" unit="litres" value={tank} onChange={setTank} /><Num label="Consumption at your load" unit="litres an hour" value={rate} onChange={setRate} /></div>
      <p className="result">{h === null ? INVALID : `About ${formatHours(h)} of running.`}</p>
      <p className="muted">A small petrol generator burns about 1 to 1.5 litres an hour at half load; check the plate. Outdoors only: <Link to="/medical/card/carbon-monoxide">carbon monoxide</Link>.</p>
    </section>
  );
}

function Battery() {
  const [wh, setWh] = useState('1000');
  const [load, setLoad] = useState('60');
  const h = batteryHours(Number(wh), Number(load));
  return (
    <section className="panel" aria-label="Battery hours">
      <h3>Battery hours</h3>
      <div className="row"><Num label="Battery capacity" unit="watt-hours" value={wh} onChange={setWh} /><Num label="Load" unit="watts" value={load} onChange={setLoad} /></div>
      <p className="result">{h === null ? INVALID : `About ${formatHours(h)} through an inverter (85% efficient).`}</p>
      <p className="muted">A 100 Ah 12 V leisure battery is about 1,200 Wh but only half is usable if lead-acid; LiFePO4 solar generators quote usable watt-hours. A fridge averages 40 to 80 W. <Link to="/p/solar-islanding">Solar panels in a power cut</Link></p>
    </section>
  );
}

function Solar() {
  const [watts, setWatts] = useState('200');
  const [month, setMonth] = useState(String(new Date().getMonth() + 1));
  const r = solarDailyWh(Number(watts), Number(month));
  return (
    <section className="panel" aria-label="Solar yield">
      <h3>Solar yield</h3>
      <div className="row">
        <Num label="Panel rating" unit="watts" value={watts} onChange={setWatts} />
        <label className="field"><span>Month</span><select aria-label="Month" value={month} onChange={(e) => setMonth(e.target.value)}>{MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}</select></label>
      </div>
      <p className="result">{r === null ? INVALID : `Roughly ${r.low} to ${r.high} Wh a day in the UK.`}</p>
      <p className="muted">From the UK band on the solar page: 0.5 to 1 kWh per kWp a day in December, 4 to 5 in June. Cloud, shading and panel angle push it lower. <Link to="/p/solar-islanding">Solar panels in a power cut</Link></p>
    </section>
  );
}

function Rations() {
  const [qty, setQty] = useState('36');
  const [people, setPeople] = useState('3');
  const [rate, setRate] = useState('3');
  const d = rationDays(Number(qty), Number(people), Number(rate));
  return (
    <section className="panel" aria-label="Rationing">
      <h3>Rationing</h3>
      <div className="row"><Num label="Stock" value={qty} onChange={setQty} /><Num label="People" value={people} onChange={setPeople} /><Num label="Per person a day" value={rate} onChange={setRate} /></div>
      <p className="result">{d === null ? INVALID : `${d.toFixed(1)} days.`}</p>
      <p className="muted">Water: 3 litres a person a day for drinking and basic hygiene; more in heat or illness. Track it properly under <Link to="/plan#stock">Stock</Link>.</p>
    </section>
  );
}

export function Calculators() {
  return (
    <Screen title="Calculators">
      <Body>
        <Generator />
        <Battery />
        <Solar />
        <Rations />
      </Body>
    </Screen>
  );
}
