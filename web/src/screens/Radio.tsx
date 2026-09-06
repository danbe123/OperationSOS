import { useMemo } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';
import { useCallsHidden } from '../situation/SituationProvider';

const NUMBERS: [string, string][] = [
  ['Emergency', '999'],
  ['NHS advice', '111'],
  ['Power cut', '105'],
  ['Floodline', '0345 988 1188'],
];

export function Radio() {
  const { data, error, loading } = useQuery(() => api.pages(), []);
  const callsHidden = useCallsHidden();
  const comms = useMemo(() => (data ?? []).filter((p) => p.category === 'comms').sort((a, b) => a.order - b.order), [data]);
  return (
    <Screen title="Phone and radio">
      <Body>
        <Emergency999 />
        {callsHidden ? (
          <p>No number will connect while both networks are down. Use the radio pages below.</p>
        ) : (
          <section className="panel" aria-label="Numbers to ring">
            <h2>Numbers to ring</h2>
            <ul className="list numbers">
              {NUMBERS.map(([what, number]) => (
                <li key={number}><span>{what}</span> <strong>{number}</strong></li>
              ))}
            </ul>
          </section>
        )}
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Pages unavailable: {error}</p>}
        <nav className="tiles tiles-wide" aria-label="Comms pages">
          {comms.map((p) => <Tile key={p.slug} to={`/p/${p.slug}`} icon={p.icon} title={p.title} subtitle={p.summary} />)}
        </nav>
      </Body>
    </Screen>
  );
}
