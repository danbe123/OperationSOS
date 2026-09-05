/** Watch activity in the app and its same-origin readers, including nested EPUB frames. */
export function watchActivity(doc: Document, onActivity: () => void): () => void {
  const frames = new Map<HTMLIFrameElement, () => void>();
  const events = ['pointerdown', 'keydown', 'wheel', 'touchmove'] as const;
  for (const event of events) doc.addEventListener(event, onActivity, { capture: true, passive: true });

  const scan = () => {
    for (const [frame, detach] of frames) {
      if (!doc.contains(frame)) {
        detach();
        frames.delete(frame);
      }
    }
    for (const frame of doc.querySelectorAll('iframe')) {
      if (frames.has(frame)) continue;
      let detachDocument: (() => void) | undefined;
      const loaded = () => {
        detachDocument?.();
        detachDocument = undefined;
        try {
          if (frame.contentDocument) detachDocument = watchActivity(frame.contentDocument, onActivity);
        } catch {
          // Cross-origin or opaque sandbox documents cannot be observed.
        }
      };
      frame.addEventListener('load', loaded);
      frames.set(frame, () => {
        frame.removeEventListener('load', loaded);
        detachDocument?.();
      });
      loaded();
    }
  };
  const observer = new MutationObserver(scan);
  observer.observe(doc, { childList: true, subtree: true });
  scan();
  return () => {
    observer.disconnect();
    for (const event of events) doc.removeEventListener(event, onActivity, true);
    for (const detach of frames.values()) detach();
    frames.clear();
  };
}
