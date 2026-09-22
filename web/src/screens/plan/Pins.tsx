import { Link } from 'react-router';
import { api } from '../../api/client';
import type { Note } from '../../api/types';
import { useQuery } from '../../api/useQuery';
import { Icon } from '../../icons';
import { gridRef } from '../../map/grid';
import { mapQueryString } from '../../map/query';

/** A pin as a line: what it is called, the map at that spot, and the grid reference to read out over
 * the radio. Pins are dropped on the map, so there is nothing to edit here. */
export function PinRow({ pin }: { pin: Note }) {
  return (
    <li className="row">
      <Link className="pin-link" to={`/map${mapQueryString({ lat: pin.lat as number, lon: pin.lon as number, z: 15, overlays: [], label: pin.title })}`}>
        <Icon name="pin" /> {pin.title}
      </Link>
      <span className="muted">{gridRef(pin.lat as number, pin.lon as number, 6).text}</span>
    </li>
  );
}

export function PinsList() {
  const q = useQuery(() => api.notes('pin'), [], { refetchOnFocus: true });
  return (
    <>
      {q.error && <p className="warning">Pins unavailable: {q.error}</p>}
      <ul className="list" aria-label="Pins">
        {(q.data ?? []).filter((p) => p.lat !== null && p.lon !== null).map((p) => <PinRow key={p.id} pin={p} />)}
        {q.data && q.data.length === 0 && <li className="muted">No pins yet — drop one from the map.</li>}
      </ul>
    </>
  );
}

export function Pins() {
  return <PinsList />;
}
