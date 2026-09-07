import { Link } from 'react-router';
import type { PlaceGuidance } from '../api/types';
import { Html } from '../components/Html';
import { Icon } from '../icons';
import { gridRef } from './grid';
import { bearingDeg, distanceKm, formatBearing, formatDistance, formatWalk, naismithMinutes, type LngLat } from './measure';
import { MapPanel } from './MapPanel';
import type { TappedPlace } from './tooltip';

/** Where the distance is measured from: home when the box has one, else the middle of the map. */
export type From = LngLat & { label: 'home' | 'the map centre' };

/** How far the place is, which way, and how long it would take to walk there — one sentence, from a
 * point the line names, because a distance with no origin on it answers nothing. */
export function distanceLine(place: LngLat, from: From): string {
  const km = distanceKm(from, place);
  return `${formatDistance(km)} ${formatBearing(bearingDeg(from, place))} from ${from.label}, about ${formatWalk(naismithMinutes(km))} on foot`;
}

/** What one place on the map is, what it has, how far away it is and what to expect there in an
 * emergency. The hover popup names the thing; this is where a household reads about it. */
export function PlaceCard({ place, from, guidance, onClose, onRoute, onPin, onNearby }: {
  place: TappedPlace; from: From; guidance: PlaceGuidance | null;
  onClose: () => void; onRoute: () => void; onPin: () => void; onNearby: () => void;
}) {
  // The type is already the line above the rows; it does not need saying twice.
  const rows = place.rows.filter(([label]) => label !== 'Type');
  return (
    <MapPanel
      label="Place" title={place.title} onClose={onClose}
      lead={
        <>
          <p className="map-lead-line">{place.typeLine}</p>
          <p className="map-lead-answer">{distanceLine(place, from)}</p>
          <p className="map-lead-line">{gridRef(place.lat, place.lon).text}</p>
        </>
      }
      actions={
        <>
          <button type="button" className="btn btn-small" onClick={onRoute}><Icon name="compass" size={18} /><span>Route from {from.label === 'home' ? 'home' : 'the centre'}</span></button>
          <button type="button" className="btn btn-small" onClick={onPin}><Icon name="pin" size={18} /><span>Pin this place</span></button>
          <button type="button" className="btn btn-small" onClick={onNearby}><Icon name="search" size={18} /><span>Nearby from here</span></button>
        </>
      }
    >
      {rows.length > 0 && (
        <section>
          <h3>What it has</h3>
          <dl className="place-rows">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
        </section>
      )}
      {guidance && (
        <section>
          <h3>What to expect here</h3>
          {/* The box's own guidance, rendered on the box: its links navigate in the app like every
              other rendered guide, and the button under it opens the guide they came from. */}
          <Html className="place-expect" html={guidance.html} />
          <Link className="btn" to={guidance.link.href}><Icon name="book" size={18} /><span>Open {guidance.link.title}</span></Link>
        </section>
      )}
    </MapPanel>
  );
}
