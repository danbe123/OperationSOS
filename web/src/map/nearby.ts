// The nearest facilities panel: what each kind is called, and what a straight line to one comes to.
import type { NearbyKind } from '../api/types';
import { bearingDeg, distanceKm, formatBearing, formatDistance, formatWalk, naismithMinutes, type LngLat } from './measure';

export const NEARBY_TITLE: Record<NearbyKind, string> = {
  'emergency-department': 'A&E',
  pharmacy: 'Pharmacy',
  gp: 'GP surgery',
  fuel: 'Fuel station',
  'water-works': 'Water works',
  'fire-station': 'Fire station',
  'rest-centre': 'Rest centre',
};

export const NEARBY_ICON: Record<NearbyKind, string> = {
  'emergency-department': 'medical',
  pharmacy: 'medical',
  gp: 'heart',
  fuel: 'bolt',
  'water-works': 'drop',
  'fire-station': 'fire',
  'rest-centre': 'home',
};

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

/** How one facility reads in the list: how far, how long on foot, and which way. */
export function describeNearby(item: { distance_m: number; walk_min: number; bearing_deg: number }): string {
  return `${formatDistance(item.distance_m / 1000)} · ${formatWalk(item.walk_min)} on foot · ${formatBearing(item.bearing_deg)}`;
}
