import type { MapConfig } from '../api/types';
import { Icon, type IconName } from '../icons';
import { coverageNote } from './overlays';

/** The short word on a chip; the manifest titles stay long for search and the card. */
export const CHIP_LABELS: Record<string, string> = {
  footpaths: 'Footpaths', 'access-land': 'Access land', 'flood-zones': 'Flood zones', health: 'Health', fuel: 'Fuel',
  water: 'Water', rail: 'Rail', 'nuclear-sites': 'Nuclear', 'chemical-sites': 'Chemical', airports: 'Airports', military: 'Military',
};
const CHIP_ICONS: Record<string, IconName> = {
  footpaths: 'boot', 'access-land': 'leaf', 'flood-zones': 'waves', health: 'medical', fuel: 'bolt', water: 'drop', rail: 'train',
  'nuclear-sites': 'radiation', 'chemical-sites': 'flask', airports: 'plane', military: 'shield',
};
export function chipIcon(id: string): IconName {
  return CHIP_ICONS[id] ?? 'layers';
}

export type Terrain = { contours: boolean; hillshade: boolean };

/** Every layer, always on screen: one chip per overlay in config order, then the two terrain chips.
 * A chip that cannot be turned on (not built for this box) is disabled and says why in its title. */
export function LayerChips({ config, overlaysOn, onToggle, terrain, onTerrain }: {
  config: MapConfig; overlaysOn: string[]; onToggle: (id: string, on: boolean) => void;
  terrain: Terrain; onTerrain: (t: Terrain) => void;
}) {
  return (
    <div className="map-chips no-print" role="group" aria-label="Map layers">
      {config.overlays.map((o) => {
        const on = overlaysOn.includes(o.id);
        const note = o.available ? coverageNote(o) : 'Not installed on this box';
        return (
          <button key={o.id} type="button" className={on ? 'map-chip active' : 'map-chip'} aria-pressed={on} disabled={!o.available}
            title={note ?? undefined} onClick={() => onToggle(o.id, !on)}>
            <Icon name={chipIcon(o.id)} size={16} />
            <span className="map-chip-dot" style={{ background: o.color }} aria-hidden="true" />
            <span>{CHIP_LABELS[o.id] ?? o.title}</span>
          </button>
        );
      })}
      {config.terrain.contours && (
        <button type="button" className={terrain.contours ? 'map-chip active' : 'map-chip'} aria-pressed={terrain.contours}
          onClick={() => onTerrain({ ...terrain, contours: !terrain.contours })}><Icon name="mountain" size={16} /><span>Contours</span></button>
      )}
      {config.terrain.hillshade && (
        <button type="button" className={terrain.hillshade ? 'map-chip active' : 'map-chip'} aria-pressed={terrain.hillshade}
          onClick={() => onTerrain({ ...terrain, hillshade: !terrain.hillshade })}><Icon name="sun" size={16} /><span>Hillshade</span></button>
      )}
    </div>
  );
}
