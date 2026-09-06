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

/** One row per authored page. The engine searches several books at once and the same page can be
 * found in more than one of them, and the box's own guides carry a section anchor per match — so
 * "Severe bleeding" arrived five times, once for each heading inside it. The anchor is not a
 * different answer, so the key drops it; `#page=` is, because two pages of a 200-page PDF are two
 * places to turn to. */
export function documentKey(url: string): string {
  const hash = url.indexOf('#');
  if (hash === -1) return url;
  return url.slice(hash + 1).startsWith('page=') ? url : url.slice(0, hash);
}

export function dedupe(results: SearchResult[]): SearchResult[] {
  const seen = new Set<string>();
  return results.filter((r) => {
    const key = r.url ? documentKey(r.url) : `${r.source}:${r.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/* The publisher's own furniture, which a crawl of a website picks up along with the answer: the NHS
 * survey prompt, its footer navigation and the Crown copyright line filled two of the top results
 * for "bleeding" with no medicine in them at all. */
const FURNITURE = [
  /Help us improve our website[^.]*/gi,
  /Can you answer a \d+ minute survey[^?]*\?/gi,
  /Take our survey/gi,
  /Support links\b[^.]*/gi,
  /Home Health A to Z NHS services Live Well[^.]*/gi,
  /©?\s*Crown copyright/gi,
  /Skip to main content/gi,
  /Cookies on GOV\.UK[^.]*/gi,
  /Is this page useful\?[^.]*/gi,
];

/** A directive the box resolves before it renders a card leaks into the search index as its own
 * source text: a household must never be shown `[[call 999]]`. */
const TOKENS = /\[\[[^\]]*\]\]|\{\{[^}]*\}\}/g;

const ENTITIES: Record<string, string> = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&nbsp;': ' ' };

function decode(text: string): string {
  return text.replace(/&(?:amp|lt|gt|quot|#39|nbsp);/g, (m) => ENTITIES[m] ?? m);
}

/** A snippet worth printing, or nothing. The engine marks its matches with `<b>`; anything left
 * after the publisher's furniture and the box's own template tokens have gone is the answer. */
export function cleanSnippet(snippet: string): string {
  let text = snippet ?? '';
  for (const rule of FURNITURE) text = text.replace(rule, ' ');
  text = text.replace(TOKENS, ' ').replace(/\s{2,}/g, ' ').replace(/\s+([,.;:])/g, '$1').trim();
  const words = text.replace(/<\/?b>/g, '').trim();
  // Furniture with no match in it is not a snippet: it is somebody else's navigation bar.
  if (!text.includes('<b>') && words.length < 24) return '';
  return text;
}

export type SnippetPart = { text: string; match: boolean };

/** The engine's `<b>` marks, as parts to render — never as HTML handed to a browser. The screen used
 * to print the tags themselves: "&lt;b&gt;Adders&lt;/b&gt; The &lt;b&gt;adder&lt;/b&gt; is…". */
export function highlightParts(snippet: string): SnippetPart[] {
  const out: SnippetPart[] = [];
  const re = /<b>([\s\S]*?)<\/b>/gi;
  let at = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(snippet)) !== null) {
    if (m.index > at) out.push({ text: decode(snippet.slice(at, m.index)), match: false });
    out.push({ text: decode(m[1]), match: true });
    at = m.index + m[0].length;
  }
  if (at < snippet.length) out.push({ text: decode(snippet.slice(at)), match: false });
  return out.filter((p) => p.text !== '');
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
    title: chipLabel(g.title),
    sources: g.key === 'own' ? OWN : [g.key],
    count: g.results.length,
  }));
}

/** A chip is a word, not a catalogue entry. "Wicipedia (Welsh Wikipedia, with images) (8)" and
   "Motor Vehicle Maintenance and Repair Q&A (Stack Exchange) (2)" filled a 480 px screen with eight
   chips over four rows, and the first result was 553 px down. */
export function chipLabel(title: string): string {
  const text = (title ?? '').replace(/\s*\([^()]*\)\s*$/, '').trim() || (title ?? '').trim();
  if (text.length <= 22) return text;
  // Cut at a word, not inside one: "Wikipedia me…" is not a word anybody was looking for.
  const cut = text.slice(0, 22).replace(/\s+\S*$/, '').trimEnd();
  return `${cut.length >= 8 ? cut : text.slice(0, 21).trimEnd()}…`;
}
