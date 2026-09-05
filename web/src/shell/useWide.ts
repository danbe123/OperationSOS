import { useEffect, useState } from 'react';

export const WIDE = '(min-width: 700px)';

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
