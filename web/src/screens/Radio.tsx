import { useMemo } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import { CallsNotice } from '../situation/CallsNotice';
import { useCallsHidden } from '../situation/SituationProvider';

export function Radio() {
  const { data, error, loading } = useQuery(() => api.pages(), []);
  const callsHidden = useCallsHidden();
  const comms = useMemo(() => (data ?? []).filter((p) => p.category === 'comms').sort((a, b) => a.order - b.order), [data]);
  return (
    <Screen title="Phone and radio">
      <Body>
        <CallsNotice />
        {callsHidden ? (
          <p className="warning">No number will connect while both networks are down. Use the radio pages below, and <Link to="/p/no-phones">getting help without phones</Link>.</p>
        ) : (
          <p className="panel">Emergency <strong>999</strong> · NHS <strong>111</strong> · Power cut <strong>105</strong> · Floodline <strong>0345 988 1188</strong></p>
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
