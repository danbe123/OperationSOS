import type { Map as MlMap, PointLike } from 'maplibre-gl';
import { floodZoneOf } from './describe';
import { overlaySourceId } from './overlays';

/** The flood zone under a point, read from the flood overlay as it is drawn right now.
 * Null when the overlay is not on the map (or has nothing there): the box never guesses a zone. */
export function floodZoneAt(map: MlMap, point: PointLike): string | null {
  const prefix = `${overlaySourceId('flood-zones')}`;
  const layers = map.getStyle().layers.filter((l) => l.id.startsWith(prefix)).map((l) => l.id);
  if (layers.length === 0) return null;
  const features = map.queryRenderedFeatures(point, { layers });
  for (const f of features) {
    const zone = floodZoneOf(f.properties ?? {});
    if (zone) return zone;
  }
  return null;
}
