import type { MapConfig, Overlay } from '../api/types';
import { Icon, isIconName, type IconName } from '../icons';
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
/** The icon this app drew for the overlay, else the one the manifest asked for if the box actually has an
 * icon by that name, else the stack of layers: a manifest can name an icon that was never drawn, and a
 * chip is no place for a question mark. */
export function chipIcon(id: string, icon?: string | null): IconName {
  if (CHIP_ICONS[id]) return CHIP_ICONS[id];
  if (icon && isIconName(icon)) return icon;
  return 'layers';
}

export type Terrain = { contours: boolean; hillshade: boolean };

/** Why an overlay that is switched on stops where it does. The same words are in the chip's title, and a
 * title is a mouse thing: on a phone there is no hover, so the reason a layer looks empty over half of
 * Scotland has to be on the screen. Only the pressed chips speak, so the row stays one or two lines. */
function chipNotes(overlays: Overlay[], on: string[]): { id: string; label: string; note: string }[] {
  return overlays
    .filter((o) => o.available && on.includes(o.id))
    .map((o) => ({ id: o.id, label: CHIP_LABELS[o.id] ?? o.title, note: coverageNote(o) }))
    .filter((n): n is { id: string; label: string; note: string } => n.note !== null);
}

/** Every layer, always on screen: one chip per overlay in config order, then the two terrain chips.
 * A chip that cannot be turned on (not built for this box) is disabled and says why in its title. */
export function LayerChips({ config, overlaysOn, onToggle, terrain, onTerrain }: {
  config: MapConfig; overlaysOn: string[]; onToggle: (id: string, on: boolean) => void;
  terrain: Terrain; onTerrain: (t: Terrain) => void;
}) {
  const notes = chipNotes(config.overlays, overlaysOn);
  return (
    <>
      <div className="map-chips no-print" role="group" aria-label="Map layers" id="map-layers">
        {config.overlays.map((o) => {
          const note = coverageNote(o);
          const title = o.available ? note : ['Not installed on this box', note].filter(Boolean).join('. ');
          const on = overlaysOn.includes(o.id);
          return (
            <button key={o.id} type="button" className={on ? 'map-chip active' : 'map-chip'} aria-pressed={on} disabled={!o.available}
              title={title ?? undefined} onClick={() => onToggle(o.id, !on)}>
              <Icon name={chipIcon(o.id, o.icon)} size={16} />
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
      {notes.map((n) => <p key={n.id} className="map-chips-note muted">{n.label}: {n.note}</p>)}
    </>
  );
}
