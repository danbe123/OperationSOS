import { useEffect, useState } from 'react';
import { flushSync } from 'react-dom';

/** Whether the page is being put on paper. A Print button is only one of the ways: a PDF export, the
 * browser's own print command and a kiosk's "save as PDF" all arrive as the print medium with no
 * `beforeprint` anybody can hear, so the medium itself is watched as well. */
export function usePrinting(): boolean {
  const [printing, setPrinting] = useState(() => typeof window !== 'undefined' && window.matchMedia?.('print')?.matches === true);
  useEffect(() => {
    const before = () => flushSync(() => setPrinting(true));
    const after = () => setPrinting(false);
    window.addEventListener('beforeprint', before);
    window.addEventListener('afterprint', after);
    const paper = window.matchMedia?.('print');
    const onMedium = (e: MediaQueryListEvent) => setPrinting(e.matches);
    paper?.addEventListener?.('change', onMedium);
    return () => {
      window.removeEventListener('beforeprint', before);
      window.removeEventListener('afterprint', after);
      paper?.removeEventListener?.('change', onMedium);
    };
  }, []);
  return printing;
}

/** The date on a printed sheet, in British words: "Sunday 6 September 2026, 06:12". */
export function printedOn(now: number = Date.now()): string {
  const at = new Date(now);
  const date = at.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const time = at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false });
  return `${date}, ${time}`;
}
