import type { ReactNode } from 'react';

/** One map panel. Its head and its actions are pinned; only the middle scrolls — the kiosk used to
 * show the top sliver of "Set as home" at the bottom edge of the screen with no cue that there was
 * anything below. On a phone it is a bottom sheet at 55 % of the map, so the map an instruction asks
 * you to aim stays live above the instruction. */
export function MapPanel({ label, title, onClose, actions, children }: {
  label: string;
  title: string;
  onClose: () => void;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="map-panel" role="dialog" aria-label={label}>
      <div className="map-panel-head">
        <h2>{title}</h2>
        <button type="button" className="btn btn-small" onClick={onClose}>Close</button>
      </div>
      <div className="map-panel-body">{children}</div>
      {actions && <div className="row map-panel-actions">{actions}</div>}
    </div>
  );
}
