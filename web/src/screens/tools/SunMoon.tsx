import { useMemo, useState } from 'react';
import { api } from '../../api/client';
import { useQuery } from '../../api/useQuery';
import { AppBar } from '../../components/AppBar';
import { gridRef } from '../../map/grid';
import { PlaceSearch } from '../../map/PlaceSearch';
import { moonPhase } from '../../tools/moon';
import { formatDayLength, sunTimes } from '../../tools/sun';

const UK_CENTRE = { lat: 54.5, lon: -3.5, label: 'Centre of the UK (set a place for local times)' };

export function hm(d: Date | null | undefined): string {
  if (!d) return '—';
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function isoDate(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function SunMoon() {
  const pinsQ = useQuery(() => api.notes('pin'), []);
  const [picked, setPicked] = useState<{ lat: number; lon: number; label: string } | null>(null);
  const [day, setDay] = useState(() => isoDate(new Date()));
  const lastPin = useMemo(() => (pinsQ.data ?? []).filter((p) => p.lat !== null && p.lon !== null).at(-1), [pinsQ.data]);
  const where = picked ?? (lastPin ? { lat: lastPin.lat as number, lon: lastPin.lon as number, label: `Pin: ${lastPin.title}` } : UK_CENTRE);
  const date = useMemo(() => new Date(`${day}T12:00:00`), [day]);
  const valid = !Number.isNaN(date.getTime());
  const sun = valid ? sunTimes(where.lat, where.lon, new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))) : null;
  const moon = valid ? moonPhase(date) : null;
  const shift = (days: number) => { const d = new Date(date); d.setDate(d.getDate() + days); setDay(isoDate(d)); };
  return (
    <div className="screen">
      <AppBar title="Sun and moon" />
      <div className="stack pad">
        <section className="card-box pad-inner">
          <h3>Where and when</h3>
          <p><strong>{where.label}</strong> <span className="muted">{gridRef(where.lat, where.lon, 6).text || `${where.lat.toFixed(3)}, ${where.lon.toFixed(3)}`}</span></p>
          <PlaceSearch onPick={(p) => setPicked({ lat: p.lat, lon: p.lon, label: p.name })} onGrid={(pt, text) => setPicked({ lat: pt.lat, lon: pt.lon, label: text })} />
          <div className="row">
            <button type="button" className="btn" onClick={() => shift(-1)} aria-label="Previous day">◀ Day before</button>
            <input type="date" aria-label="Date" value={day} onChange={(e) => setDay(e.target.value)} />
            <button type="button" className="btn" onClick={() => shift(1)} aria-label="Next day">Day after ▶</button>
            <button type="button" className="btn" onClick={() => setDay(isoDate(new Date()))}>Today</button>
          </div>
        </section>
        {sun && (
          <section className="card-box pad-inner" aria-label="Sun">
            <h3>Sun</h3>
            {sun.polar === 'day' && <p>The sun does not set here on this date.</p>}
            {sun.polar === 'night' && <p>The sun does not rise here on this date.</p>}
            {sun.polar === null && (
              <table className="sun-table">
                <tbody>
                  <tr><th>First light (civil dawn)</th><td>{hm(sun.civilDawn)}</td></tr>
                  <tr><th>Sunrise</th><td>{hm(sun.sunrise)}</td></tr>
                  <tr><th>Solar noon</th><td>{hm(sun.solarNoon)}</td></tr>
                  <tr><th>Sunset</th><td>{hm(sun.sunset)}</td></tr>
                  <tr><th>Last light (civil dusk)</th><td>{hm(sun.civilDusk)}</td></tr>
                  <tr><th>Daylight</th><td>{formatDayLength(sun.dayLengthMin)}</td></tr>
                </tbody>
              </table>
            )}
            <p className="muted">Times are in this device's clock zone. Civil twilight is bright enough to work outside without a torch.</p>
          </section>
        )}
        {moon && (
          <section className="card-box pad-inner" aria-label="Moon">
            <h3>Moon</h3>
            <p><strong>{moon.name}</strong>, {Math.round(moon.illumination * 100)}% lit, {moon.ageDays} days old{moon.waxing ? ', waxing' : ', waning'}.</p>
            <p className="muted">A full moon gives enough light to move about outside; a new moon means true darkness.</p>
          </section>
        )}
      </div>
    </div>
  );
}
