import { useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from '../icons';
import { relativeTime } from '../tools/dates';

/** One tick behaves the same way everywhere in the box — on Now, on Things to do and on a guide. A
 * ticked job stays exactly where it is, struck through, with who did it and when, and an Undo beside
 * it for ten seconds. Nothing a finger touches ever disappears under the finger. */
export const UNDO_MS = 10_000;

/** The ten-second window after a tick. `arm()` opens it, `disarm()` closes it early. */
export function useTickUndo(): { armed: boolean; arm: () => void; disarm: () => void } {
  const [armed, setArmed] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const stop = useCallback(() => { window.clearTimeout(timer.current); timer.current = undefined; }, []);
  useEffect(() => stop, [stop]);
  const arm = useCallback(() => {
    stop();
    setArmed(true);
    timer.current = window.setTimeout(() => setArmed(false), UNDO_MS);
  }, [stop]);
  const disarm = useCallback(() => { stop(); setArmed(false); }, [stop]);
  return { armed, arm, disarm };
}

/** The Undo that sits in a just-ticked row. */
export function UndoTick({ label, busy, onUndo }: { label: string; busy?: boolean; onUndo: () => void }) {
  return (
    <button type="button" className="btn btn-small task-undo" disabled={busy} onClick={onUndo} aria-label={`Undo: ${label}`}>
      <Icon name="refresh" size={18} /><span>Undo</span>
    </button>
  );
}

/** Who ticked it and when, on its own line. It is never struck through: only the job's title is. */
export function TickedLine({ at, person }: { at: string | null; person?: string | null }) {
  const when = relativeTime(at);
  if (!when && !person) return null;
  return <span className="task-time">{person ? `${person}, ` : ''}{when ? `ticked ${when}` : 'ticked'}</span>;
}
