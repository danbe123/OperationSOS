import { Link } from 'react-router';
import type { PlaceGuidance, PlaceSection } from '../api/types';
import { Html } from '../components/Html';
import { Icon } from '../icons';
import { gridRef } from './grid';
import { bearingDeg, distanceKm, formatBearing, formatDistance, formatWalk, naismithMinutes, type LngLat } from './measure';
import { MapPanel } from './MapPanel';
import { guideLinkLabel, SECTION_ICON_PATHS, SECTION_ICON_SIZE, sectionClassName } from './placeSections';
import type { TappedPlace } from './tooltip';

/** Where the distance is measured from: home when the box has one, else the middle of the map. */
export type From = LngLat & { label: 'home' | 'the map centre' };

/** How far the place is, which way and how long on foot, then where that was measured from and the
 * grid reference: two short lines, because the card's body has to be readable under them on a phone. */
export function distanceLine(place: LngLat, from: From): { answer: string; origin: string } {
  const km = distanceKm(from, place);
  return {
    answer: `${formatDistance(km)} ${formatBearing(bearingDeg(from, place))}, about ${formatWalk(naismithMinutes(km))} on foot`,
    origin: `from ${from.label} · ${gridRef(place.lat, place.lon).text}`,
  };
}

/** One of the four survival sections, in exactly the shape the docked hover panel builds in plain
 * DOM: the same class names, the same icon and the same bullets, off the same file, so a card and a
 * hover of the same hospital can never come to look like two different things. The heading is an h3
 * here because the card's own sections are h3s; the panel, which has no h3s above it, uses h4. */
function GuideSection({ part }: { part: PlaceSection }) {
  return (
    <section className={sectionClassName(part.id)}>
      <h3 className="map-tip-section-head">
        <svg
          className="map-tip-icon" width={SECTION_ICON_SIZE} height={SECTION_ICON_SIZE} viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          aria-hidden="true" focusable="false" dangerouslySetInnerHTML={{ __html: SECTION_ICON_PATHS[part.id] }}
        />
        <span>{part.title}</span>
      </h3>
      <Html html={part.html} />
    </section>
  );
}

/** What one place on the map is, what it has, how far away it is and what to expect there in an
 * emergency. The hover popup names the thing; this is where a household reads about it. */
export function PlaceCard({ place, from, guidance, onClose, onRoute, onPin, onNearby }: {
  place: TappedPlace; from: From; guidance: PlaceGuidance | null;
  onClose: () => void; onRoute: () => void; onPin: () => void; onNearby: () => void;
}) {
  // The type is already the line above the rows; it does not need saying twice.
  const rows = place.rows.filter(([label]) => label !== 'Type');
  const line = distanceLine(place, from);
  return (
    <MapPanel
      label="Place" title={place.title} onClose={onClose}
      lead={
        <>
          <p className="map-lead-line">{place.typeLine}</p>
          <p className="map-lead-answer">{line.answer}</p>
          <p className="map-lead-line">{line.origin}</p>
        </>
      }
      /* Three actions on one row, each a word and an icon, with the full sentence for a screen reader:
         three stacked sentences under a three-line lead left the body a sliver on the kiosk. */
      actions={
        <>
          <button type="button" className="btn btn-small" onClick={onRoute} aria-label={`Route from ${from.label}`} title={`Route from ${from.label}`}><Icon name="compass" size={18} /><span>Route</span></button>
          <button type="button" className="btn btn-small" onClick={onPin} aria-label="Pin this place" title="Pin this place"><Icon name="pin" size={18} /><span>Pin</span></button>
          <button type="button" className="btn btn-small" onClick={onNearby} aria-label="Nearby from here" title="Nearby from here"><Icon name="search" size={18} /><span>Nearby</span></button>
        </>
      }
    >
      {rows.length > 0 && (
        <section className="place-section">
          <h3>What it has</h3>
          <dl className="place-rows">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
        </section>
      )}
      {guidance && (
        <>
          <section className="place-section">
            <h3>What to expect here</h3>
            {/* The box's own guidance, rendered on the box: its links navigate in the app like every
                other rendered guide, and the button under it opens the guide they came from. */}
            <Html className="place-expect" html={guidance.html} />
          </section>
          {/* What is usually here, when it is worth going, when to stay away and how to go about it:
              the same four lists the hover tooltip carries, for the finger that opened the card. */}
          {guidance.sections.map((part) => <GuideSection key={part.id} part={part} />)}
          <Link className="btn map-tip-guide" to={guidance.link.href}><Icon name="book" size={18} /><span>{guideLinkLabel(guidance)}</span></Link>
        </>
      )}
    </MapPanel>
  );
}
