import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Icon } from '../icons';

/** A row of cards that scrolls sideways — the books being read, the last things viewed — with the
 * cues a row like that needs: a slim bar in the app's own tone rather than the browser's grey one, a
 * fade at whichever edge the row goes on past, and an arrow at each end for a mouse (a finger swipes;
 * on a screen with no hover the arrows stay away). */
export function Strip({ label, children }: { label: string; children: ReactNode }) {
  const ref = useRef<HTMLUListElement>(null);
  const [edge, setEdge] = useState({ left: false, right: false });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let frame = 0;
    const read = () => {
      frame = 0;
      const more = el.scrollWidth - el.clientWidth;
      const next = { left: el.scrollLeft > 4, right: more - el.scrollLeft > 4 };
      setEdge((was) => (was.left === next.left && was.right === next.right ? was : next));
    };
    // One read a frame, not one a scroll event: a fast swipe fires hundreds, and each one re-rendered.
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(read); };
    read();
    el.addEventListener('scroll', onScroll, { passive: true });
    const watcher = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(read) : null;
    watcher?.observe(el);
    return () => { el.removeEventListener('scroll', onScroll); watcher?.disconnect(); if (frame) cancelAnimationFrame(frame); };
  }, [children]);
  const by = (dir: -1 | 1) => {
    const el = ref.current;
    if (el) el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: 'smooth' });
  };
  return (
    <div className="strip">
      <ul className="book-strip" aria-label={label} ref={ref}>{children}</ul>
      {edge.left && <button type="button" className="btn strip-arrow strip-arrow-left" aria-label="Scroll back" onClick={() => by(-1)}><Icon name="back" size={20} /></button>}
      {edge.right && <button type="button" className="btn strip-arrow strip-arrow-right" aria-label="Scroll on" onClick={() => by(1)}><Icon name="forward" size={20} /></button>}
    </div>
  );
}
