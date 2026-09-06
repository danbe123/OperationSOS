import type { MapConfig } from '../api/types';
import { MapPanel } from './MapPanel';
import { coverageNote } from './overlays';

export function LayerPanel({ config, baseId, onBase, overlaysOn, onToggle, terrainOn, onTerrain, onClose }: {
  config: MapConfig; baseId: 'osm' | 'os'; onBase: (id: 'osm' | 'os') => void;
  overlaysOn: string[]; onToggle: (id: string, on: boolean) => void;
  terrainOn: boolean; onTerrain: (on: boolean) => void; onClose: () => void;
}) {
  const hasTerrain = Boolean(config.terrain.contours || config.terrain.hillshade);
  return (
    <MapPanel label="Layers" title="Layers" onClose={onClose}>
      <h3>Base map</h3>
      {config.bases.map((b) => (
        <label key={b.id} className="check-row">
          <input type="radio" name="base" value={b.id} checked={baseId === b.id} disabled={!b.available} onChange={() => onBase(b.id)} />
          <span>{b.title}{!b.available && <span className="muted"> (not installed)</span>}</span>
        </label>
      ))}
      {hasTerrain && (
        <label className="check-row">
          <input type="checkbox" checked={terrainOn} onChange={(e) => onTerrain(e.target.checked)} />
          <span>Contours and hillshade</span>
        </label>
      )}
      <h3>Overlays</h3>
      {config.overlays.map((o) => {
        const note = coverageNote(o);
        return (
          <div key={o.id} className="check-block">
            <label className="check-row">
              <input type="checkbox" checked={overlaysOn.includes(o.id)} disabled={!o.available} onChange={(e) => onToggle(o.id, e.target.checked)} />
              <span><span className="swatch" style={{ background: o.color }} aria-hidden="true" /> {o.title}</span>
            </label>
            {!o.available && <p className="muted small">Not installed</p>}
            {note && <p className="muted small">{note}</p>}
          </div>
        );
      })}
    </MapPanel>
  );
}
