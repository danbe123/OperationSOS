import type { SearchResult } from './types';
import { sourceWord } from './words';

/* What a household sees when it searches. The engine ranks everything into one list by score, and
 * that list answered "bleeding" with the side effects of warfarin above the box's own Severe
 * bleeding card, printed "Bleeding" twice, and labelled a result "NHS Medicines A to Z (Kiwix build,
 * December 2025) How and when to take memantine - NHS". None of that is the ranking's fault alone:
 * the screen was rendering whatever arrived, in the order it arrived, with the library's own
 * cataloguing glued to the front of every title. This is where that is put right, on the way to the
 * screen: one entry per target, the box's own guidance first, and a source named in a word. */

/** The sources the box wrote itself, in the order a frightened household wants them. */
const OWN = ['playbooks'];
/** Everything else, best first; anything unknown follows in the order the engine ranked it. */
const ORDER = ['places', 'docs', 'nhs', 'medical', 'library', 'practical', 'survival', 'reference', 'uk-official', 'extended'];

export const OWN_GROUP = 'From this box';

/** The library's cataloguing, off the front of a title: a ZIM book's badge is its full library
 * title, build stamp and all. */
export function cleanBadge(badge: string): string {
  const text = (badge ?? '')
    .replace(/\s*\((?:[^()]*\bkiwix\b[^()]*)\)\s*/gi, ' ')
    .replace(/\s*\((?:[^()]*\b(?:build|version)\b[^()]*)\)\s*/gi, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return sourceWord(text);
}

/** A result's own title, without the publisher's furniture: the NHS repeats itself at the end of
 * every page title, and the Approved Documents carry "ONLINE VERSION" twice. */
export function cleanTitle(title: string): string {
  return (title ?? '')
    .replace(/\s*[-–—]\s*NHS\s*$/i, '')
    .replace(/(\bONLINE VERSION\b)(\s+\1)+/gi, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/** One row per target. The engine searches several books at once and the same page can be found in
 * more than one of them, so "Solar panels in a power cut" arrived three times in the top four. */
export function dedupe(results: SearchResult[]): SearchResult[] {
  const seen = new Set<string>();
  return results.filter((r) => {
    const key = r.url || `${r.source}:${r.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export type ResultGroup = { key: string; title: string; results: SearchResult[] };

/** The results in groups, the box's own guides, cards, modules and pages first. Inside a group the
 * engine's order stands; between groups, what this box was built to answer comes before a mirror of
 * somebody else's website. */
export function groupResults(results: SearchResult[]): ResultGroup[] {
  const groups = new Map<string, ResultGroup>();
  for (const r of results) {
    const own = OWN.includes(r.source);
    const key = own ? 'own' : r.source;
    const group = groups.get(key) ?? { key, title: own ? OWN_GROUP : cleanBadge(r.badge), results: [] };
    group.results.push(r);
    groups.set(key, group);
  }
  const rank = (key: string) => (key === 'own' ? -1 : ORDER.indexOf(key) === -1 ? ORDER.length : ORDER.indexOf(key));
  return [...groups.values()].sort((a, b) => rank(a.key) - rank(b.key));
}

/** The sources a filter chip can turn on, with the counts of the very results underneath them: the
 * chips used to sum to 61 above a line reading "40 results", because the engine counts before it
 * truncates and the screen counted after. */
export function chipsFor(groups: ResultGroup[]): { key: string; title: string; sources: string[]; count: number }[] {
  return groups.map((g) => ({
    key: g.key,
    title: g.title,
    sources: g.key === 'own' ? OWN : [g.key],
    count: g.results.length,
  }));
}
