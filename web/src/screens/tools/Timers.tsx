import { useEffect, useReducer, useState } from 'react';
import { Link } from 'react-router';
import { AppBar } from '../../components/AppBar';
import { Icon } from '../../icons';
import { click } from '../../tools/audio';
import { cancelTimer, startTimer, useTimers } from '../../tools/timerStore';
import { beatsSince, CPR_BPM, falloutMarks, formatCountdown, PRESETS, remainingSeconds } from '../../tools/timers';

function useNow(intervalMs: number): number {
  const [, bump] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(bump, intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return Date.now();
}

function Countdowns() {
  const timers = useTimers();
  const now = useNow(500);
  const [custom, setCustom] = useState('10');
  return (
    <section className="card-box pad-inner">
      <h3>Countdowns</h3>
      <ul className="list" aria-label="Running timers">
        {timers.map((t) => (
          <li key={t.id} className="row">
            <span className="timer-big" aria-live="off">{formatCountdown(remainingSeconds(t, now))}</span>
            <span>{t.label}</span>
            <button type="button" className="btn" onClick={() => cancelTimer(t.id)} aria-label={`Cancel ${t.label}`}>Cancel</button>
          </li>
        ))}
        {timers.length === 0 && <li className="muted">No timer running.</li>}
      </ul>
      <div className="row">
        {PRESETS.map((p) => <button key={p.id} type="button" className="btn" onClick={() => startTimer(p.label, p.seconds)}>{p.label}</button>)}
        <label className="field"><span>Minutes</span><input type="number" inputMode="numeric" min={1} max={720} aria-label="Custom minutes" value={custom} onChange={(e) => setCustom(e.target.value)} /></label>
        <button type="button" className="btn btn-primary" onClick={() => { const m = Number(custom); if (m > 0) startTimer(`${m} min timer`, Math.round(m * 60)); }}>Start</button>
      </div>
      <p className="muted">{PRESETS[0].note} Timers keep running while you read other screens and sound when they finish.</p>
    </section>
  );
}

function Cpr() {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [beat, setBeat] = useState(0);
  useEffect(() => {
    if (startedAt === null) return;
    const id = window.setInterval(() => { click(); setBeat((b) => b + 1); }, 60_000 / CPR_BPM);
    return () => window.clearInterval(id);
  }, [startedAt]);
  const count = startedAt === null ? 0 : beatsSince(startedAt, Date.now());
  return (
    <section className="card-box pad-inner">
      <h3>CPR beat</h3>
      <p>{CPR_BPM} compressions a minute, 5 to 6 cm deep. 30 compressions then 2 breaths. <Link to="/medical/card/cpr-adult">Adult CPR card</Link> · <Link to="/medical/card/cpr-child">Child CPR card</Link></p>
      <div className="row">
        {startedAt === null ? (
          <button type="button" className="btn btn-primary btn-big" onClick={() => { setStartedAt(Date.now()); setBeat(0); }}>Start the beat</button>
        ) : (
          <>
            <span className={`cpr-pulse ${beat % 2 ? 'on' : ''}`} aria-hidden="true" />
            <span className="timer-big" aria-label="Compressions so far">{count}</span>
            <span className="muted">compressions · cycle {Math.floor(count / 30) + 1}</span>
            <button type="button" className="btn btn-danger" onClick={() => setStartedAt(null)}>Stop</button>
          </>
        )}
      </div>
    </section>
  );
}

function localInputValue(ms: number): string {
  const d = new Date(ms);
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function Fallout() {
  const [when, setWhen] = useState(() => localInputValue(Date.now()));
  const now = useNow(1000);
  const detonation = Date.parse(when);
  const marks = Number.isNaN(detonation) ? [] : falloutMarks(detonation, now);
  return (
    <section className="card-box pad-inner">
      <h3>Fallout 7:10 rule</h3>
      <p>After a nuclear detonation the radiation dose rate falls to about a tenth every time the elapsed time multiplies by seven. Stay sheltered; the first two days matter most. <Link to="/m/radiation">Radiation module</Link> · <Link to="/s/nuclear-war">Nuclear war playbook</Link></p>
      <label className="field"><span>Time of the detonation</span><input type="datetime-local" aria-label="Time of the detonation" value={when} onChange={(e) => setWhen(e.target.value)} /></label>
      <table className="fallout" aria-label="Fallout marks">
        <thead><tr><th>Mark</th><th>Dose rate</th><th>Reached</th></tr></thead>
        <tbody>
          {marks.map((m) => (
            <tr key={m.label}>
              <td>{m.label}</td>
              <td>{m.factor} of the 1-hour rate</td>
              <td>{m.reached ? <span className="badge badge-ok">passed</span> : <span>in {formatCountdown(m.remainingSeconds)}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function Timers() {
  return (
    <div className="screen">
      <AppBar title="Timers" />
      <p className="pad warning">Someone not breathing normally: call 999 and start CPR. <Icon name="phone" size={18} /> 999</p>
      <div className="stack pad">
        <Countdowns />
        <Cpr />
        <Fallout />
      </div>
    </div>
  );
}
