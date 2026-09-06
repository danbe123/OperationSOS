import { Link } from 'react-router';
import { api } from '../../api/client';
import { useQuery } from '../../api/useQuery';
import { Icon } from '../../icons';
import { gridRef } from '../../map/grid';
import { mapQueryString } from '../../map/query';

export function Pins() {
  const pinsQ = useQuery(() => api.notes('pin'), [], { refetchOnFocus: true });
  return (
    <section className="panel" id="pins" aria-label="Pins on the map">
      <h2>Pins on the map</h2>
      <ul className="list" aria-label="Pins">
        {(pinsQ.data ?? []).filter((p) => p.lat !== null && p.lon !== null).map((p) => (
          <li key={p.id} className="row">
            <Link to={`/map${mapQueryString({ lat: p.lat as number, lon: p.lon as number, z: 15, overlays: [], label: p.title })}`}><Icon name="pin" /> {p.title}</Link>
            <span className="muted">{gridRef(p.lat as number, p.lon as number, 6).text}</span>
          </li>
        ))}
        {pinsQ.data && pinsQ.data.length === 0 && <li className="muted">No pins yet. Drop one from the map.</li>}
      </ul>
    </section>
  );
}
