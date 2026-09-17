import type { Location } from 'epubjs/types/rendition';

/** How often the reader tells the box where you are: one write per two seconds of page turning. */
export const SAVE_DELAY_MS = 2000;

/** What the reader remembers a book by. `startCfi` is where it opens; the rest is what the shelf shows. */
export type EpubMemory = { key: string; title: string; author: string | null; coverUrl: string | null; startCfi: string | null };

/** A whole-book percentage without epub.js's `locations` pass (which reads the entire book to count
 * characters and takes seconds on a phone): the section's share of the spine plus the page's share of
 * the section. Coarse between chapters, exact enough for "42% read" on a shelf. */
export function readingPercent(loc: Location, spineLength: number | undefined): number {
  if (loc.atEnd) return 100;
  const sections = spineLength && spineLength > 0 ? spineLength : 1;
  const page = Math.max(1, loc.start.displayed?.page ?? 1);
  const total = Math.max(1, loc.start.displayed?.total ?? 1);
  const within = (page - 1) / total;
  const value = ((loc.start.index ?? 0) + within) / sections * 100;
  return Math.max(0, Math.min(100, Math.round(value * 10) / 10));
}
