import { useRef, type ReactNode, type RefObject } from 'react';
import { Icon } from '../icons';
import { speak, stopSpeaking, useSpeech, visibleText } from '../tools/speech';

/** A speaker button over a block of the screen: it reads what is there aloud, in chunks, with a stop.
 * It hides itself entirely on a box with no voice installed, rather than offering something that fails. */
export function ReadAloud({ id, target, label = 'Read aloud' }: { id: string; target: RefObject<HTMLElement | null>; label?: string }) {
  const { speaking, available } = useSpeech();
  if (!available) return null;
  const reading = speaking === id;
  if (reading) {
    return (
      <button type="button" className="btn btn-danger read-aloud no-print" onClick={() => stopSpeaking()}>
        <Icon name="close" /><span>Stop reading</span>
      </button>
    );
  }
  return (
    <button
      type="button"
      className="btn read-aloud no-print"
      disabled={speaking !== null}
      onClick={() => {
        const el = target.current;
        if (el) void speak(id, visibleText(el));
      }}
    >
      <Icon name="speaker" /><span>{label}</span>
    </button>
  );
}

/** The same button over a block of content it wraps: for a page, a module or a playbook section. */
export function ReadAloudBlock({ id, label, className, children }: { id: string; label?: string; className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div className={className} ref={ref}>
      <div className="pad read-aloud-row no-print"><ReadAloud id={id} target={ref} label={label} /></div>
      {children}
    </div>
  );
}
