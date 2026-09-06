import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';

export type PanelBodySize = { width: number; height: number };

/** One map panel. Its head, its answer and its actions are pinned; only the middle scrolls — the
 * kiosk used to show the top sliver of "Set as home" at the bottom edge of the screen with no cue
 * that there was anything below.
 *
 * `lead` is the answer the panel was opened for: the nearest hospital, the two grid references. It
 * sits between the title and the list because a phone sheet that scrolls its answer out of sight,
 * or hides it behind its own action row, has not answered anything.
 *
 * On a phone the panel is a bottom sheet, so the map an instruction asks you to aim stays live above
 * the instruction. It starts at 55 % of the map and takes 70 % once there is more in the body than
 * the body can show; it never shrinks back, because a sheet that flaps between two heights while
 * somebody is reading it is worse than either height. */
export function MapPanel({ label, title, onClose, lead, actions, onBodySize, children }: {
  label: string;
  title: string;
  onClose: () => void;
  lead?: ReactNode;
  actions?: ReactNode;
  /** Told the body's own box whenever it changes, for the panel that has to size a picture to it. */
  onBodySize?: (size: PanelBodySize) => void;
  children: ReactNode;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const report = useRef(onBodySize);
  const size = useRef<PanelBodySize>({ width: -1, height: -1 });
  const [tall, setTall] = useState(false);

  const measure = useCallback(() => {
    const el = bodyRef.current;
    if (!el) return;
    if (el.scrollHeight > el.clientHeight + 1) setTall(true);
    if (el.clientWidth !== size.current.width || el.clientHeight !== size.current.height) {
      size.current = { width: el.clientWidth, height: el.clientHeight };
      report.current?.(size.current);
    }
  }, []);

  useEffect(() => { report.current = onBodySize; }, [onBodySize]);
  // After every render, because the body's own box does not change when the list inside it arrives,
  // so a resize observer on its own would never notice that there is now more than fits.
  useEffect(measure);
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    window.addEventListener('resize', measure);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(el);
    return () => {
      window.removeEventListener('resize', measure);
      observer?.disconnect();
    };
  }, [measure]);

  return (
    <div className={tall ? 'map-panel map-panel-tall' : 'map-panel'} role="dialog" aria-label={label}>
      <div className="map-panel-head">
        <h2>{title}</h2>
        <button type="button" className="btn btn-small" onClick={onClose}>Close</button>
      </div>
      {lead && <div className="map-panel-lead">{lead}</div>}
      <div className="map-panel-body" ref={bodyRef}>{children}</div>
      {actions && <div className="row map-panel-actions">{actions}</div>}
    </div>
  );
}
