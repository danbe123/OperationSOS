// The nearest facilities panel: what each kind looks like, and what one place comes to in words.
// The shapes here are `GET /api/nearby?lat&lon` exactly as the box answers it.
import type { NearbyFacility, NearbyPlace } from '../api/types';
import type { IconName } from '../icons';
import { bearingDeg, distanceKm, formatBearing, formatDistance, formatWalk, naismithMinutes, type LngLat } from './measure';

/** An icon per facility id. The box names the facilities, so an unknown id still draws something. */
export const NEARBY_ICON: Record<string, IconName> = {
  'emergency-department': 'medical',
  pharmacy: 'medical',
  gp: 'heart',
  fuel: 'bolt',
  'water-works': 'drop',
  'fire-station': 'fire',
  'rest-centre': 'home',
};

export function nearbyIcon(id: string): IconName {
  return NEARBY_ICON[id] ?? 'pin';
}

export type Route = { km: number; bearing: number; minutes: number; text: string };

/** A straight line, not a route: the box has no routing engine, so it says the bearing, the distance
 * and a Naismith walking time, and leaves the roads to the map. */
export function describeRoute(from: LngLat, to: LngLat, title: string, fromLabel = 'home'): Route {
  const km = distanceKm(from, to);
  const bearing = bearingDeg(from, to);
  const minutes = naismithMinutes(km);
  return {
    km,
    bearing,
    minutes,
    text: `${title}: ${formatDistance(km)} from ${fromLabel}, bearing ${formatBearing(bearing)}, about ${formatWalk(minutes)} on foot`,
  };
}

const POINT: Record<string, string> = { N: 'north', S: 'south', E: 'east', W: 'west' };

/** "NE" as a person says it: north-east. The compass point comes from the box so the screen and the
 * printed report agree; only the wording is ours. */
export function compassWord(compass: string): string {
  return compass.split('').map((c) => POINT[c.toUpperCase()] ?? '').filter(Boolean).join('-');
}

/** How one place reads in the list: how far, which way and how long on foot, as a sentence rather
 * than three readings joined by dots. */
export function describeNearby(place: Pick<NearbyPlace, 'distance_m' | 'walk_minutes' | 'bearing_deg' | 'compass'>): string {
  const way = compassWord(place.compass);
  return `${formatDistance(place.distance_m / 1000)}${way ? ` to the ${way}` : ''}, about ${formatWalk(place.walk_minutes)} on foot`;
}

/** The one facility the panel leads with: the kind somebody chose, or — until they choose — the
 * first kind the box actually found something for, so the head of the panel is never a gap while
 * there are answers in the list underneath it. */
export function leadFacility(facilities: NearbyFacility[], chosenId: string | null): NearbyFacility | null {
  const chosen = chosenId ? facilities.find((f) => f.id === chosenId) : undefined;
  return chosen ?? facilities.find((f) => f.nearest) ?? facilities[0] ?? null;
}

/** What a facility with nothing found should say, in one line. */
export function nearbyGap(f: NearbyFacility): string {
  return f.why ?? `Nothing matching on this box.`;
}

/** A place with no name on it in OpenStreetMap is still a place: "Unnamed" is not what it is called,
 * it is the absence of a name. The kind it was found under says what it is. */
export function placeName(name: string | null | undefined, facilityTitle: string): string {
  const text = (name ?? '').trim();
  if (!text || /^unnamed$/i.test(text)) return `${facilityTitle} (no name recorded)`;
  return text;
}

/** A caveat with no map data in it. The box's own note used to print an OpenStreetMap tag name at a
 * household — "The overlay does not carry the `emergency=yes` tag" — and any note the engine grows
 * later could do the same, so anything shaped like a raw tag is taken out on the way to the screen
 * rather than trusted to have been written for a reader. */
const RAW_TAG = /\s*\b[a-z][a-z0-9_:]*=[A-Za-z0-9_:*-]+\b/g;

export function plainNote(note: string | null | undefined): string {
  const text = (note ?? '').replace(/`/g, '');
  if (!RAW_TAG.test(text)) { RAW_TAG.lastIndex = 0; return text.trim(); }
  RAW_TAG.lastIndex = 0;
  // Drop whole sentences that only exist to name a tag, then any tag left inside one that does not.
  const kept = text
    .split(/(?<=[.;])\s+/)
    .filter((sentence) => { RAW_TAG.lastIndex = 0; return !RAW_TAG.test(sentence); })
    .join(' ')
    .trim();
  RAW_TAG.lastIndex = 0;
  return kept || 'These come from OpenStreetMap and are as complete as the map is.';
}
