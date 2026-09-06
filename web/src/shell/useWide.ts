import { useEffect, useState } from 'react';

/* The rail needs both dimensions: nine rows do not fit a 390 px-tall landscape phone, so under
   440 px the shell draws the bottom bar instead. `shell.css` carries the same query. */
export const WIDE = '(min-width: 700px) and (min-height: 440px)';

/** True where the shell draws a rail rather than a bar. Chrome that exists once — the theme button,
 * the box's own screens — is rendered on one side or the other, never twice in the same document. */
export function useWide(query: string = WIDE): boolean {
  const [wide, setWide] = useState(() => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : false));
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(query);
    const onChange = () => setWide(mq.matches);
    onChange();
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, [query]);
  return wide;
}
