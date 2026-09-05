import { useEffect, useState } from 'react';
import { api, ApiError } from '../api/client';
import type { Sensors } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { Icon } from '../icons';
import { ago } from './conditions';
import { readingText, readingTone, sensorIcon, sensorTitle } from './sensors';

export const SENSORS_POLL_MS = 60_000;

/** What the box itself can tell, with the age of each reading. A reading is never the last word:
 * the engine proposes from it, and somebody still says yes. */
export function SensorsPanel() {
  const [sensors, setSensors] = useState<Sensors | null>(null);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const s = await api.sensors();
        if (!alive) return;
        setSensors(s);
        setError(null);
        setMissing(false);
      } catch (e) {
        if (!alive) return;
        // A box whose sensors are not built (or not fitted) answers 404: say nothing rather than alarm.
        if (e instanceof ApiError && e.status === 404) setMissing(true);
        else setError(errorMessage(e));
      }
    };
    void load();
    const id = window.setInterval(() => void load(), SENSORS_POLL_MS);
    return () => { alive = false; window.clearInterval(id); };
  }, []);

  const entries = Object.entries(sensors ?? {}).filter((e): e is [string, NonNullable<(typeof e)[1]>] => e[1] !== null);
  if (missing) return null;
  if (sensors && entries.length === 0 && !error) return null;
  return (
    <section aria-label="Detected" id="sensors">
      <div className="pad">
        <h2>Detected by the box</h2>
        <p className="muted">What the box can sense for itself. It proposes; you decide.</p>
      </div>
      {!sensors && !error && <p className="pad muted">Reading the sensors…</p>}
      {error && <p className="pad muted">No sensor readings: {error}</p>}
      {entries.length > 0 && (
        <ul className="list sensor-list" aria-label="Sensor readings">
          {entries.map(([id, reading]) => {
            const tone = readingTone(id, reading);
            return (
              <li key={id} className="sensor-row">
                <span className="sensor-name"><Icon name={sensorIcon(id)} size={20} /> {sensorTitle(id)}</span>
                <span className={tone === 'default' ? 'badge' : `badge badge-${tone}`}>{readingText(reading)}</span>
                <span className="muted">{ago(reading.at)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
