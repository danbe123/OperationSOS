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

export const OWN_GROUP = 'From this box';
export const LIBRARY_GROUP = 'From the library';

/** The library's cataloguing, off the front of a title: a ZIM book's badge is its full library
 * title, build stamp and all. */
export function cleanBadge(badge: string): string {
  const text = (badge ?? '')
    .replace(/\s*\((?:[^()]*\bkiwix\b[^()]*)\)\s*/gi, ' ')
    .replace(/\s*\((?:[^()]*\b(?:build|version)\b[^()]*)\)\s*/gi, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
  // A catalogue title of the "Name: what it is" shape is its name on a row: "WikiMed: Wikipedia medical
  // encyclopedia" said forty characters before every title it was the source of; and a trailing
  // parenthesis is cataloguing too ("Wikipedia (English, with images)").
  const bare = text.replace(/\s*\([^()]*\)\s*$/, '').trim() || text;
  const named = /^([^:]{2,28}):\s+\S/.exec(bare);
  return sourceWord(named ? named[1].trim() : bare);
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

/** The section one of the box's own passages is, from its anchor: '/m/water#what-to-do' is
 * "What to do". A converted document's `#page=` is a page, not a section; an article has neither. */
export function sectionOf(url: string): string {
  const hash = (url ?? '').indexOf('#');
  if (hash === -1) return '';
  const frag = url.slice(hash + 1);
  if (!frag || frag.startsWith('page=')) return '';
  const words = frag.replace(/-/g, ' ').trim().split(' ').map((w) => (w === 'uk' ? 'UK' : w)).join(' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** A snippet worth printing, or nothing. The engine marks its matches with `<b>`; anything left
 * after the publisher's furniture and the box's own template tokens have gone is the answer. The
 * section heading a passage opens with ("Key facts - Heat one room…") is said once, beside the
 * title, not again at the front of the snippet. */
export function cleanSnippet(snippet: string, section = ''): string {
  let text = snippet ?? '';
  for (const rule of FURNITURE) text = text.replace(rule, ' ');
  text = text.replace(TOKENS, ' ').replace(/\s{2,}/g, ' ').replace(/\s+([,.;:])/g, '$1').trim();
  if (section) {
    const bare = text.replace(/^(?:<b>)?/, '');
    if (bare.slice(0, section.length).toLowerCase() === section.toLowerCase()) {
      text = bare.slice(section.length).replace(/^<\/b>/, '').replace(/^[\s\-–:.]+/, '');
    }
  }
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

/** Two groups: the box's own guides, cards, modules and pages first, then everything else in the
 * engine's own order. It used to be a group per source, each with a heading, in a fixed order of
 * sources — which put a source's weakest hit above a stronger source's best, and read as a directory
 * rather than an answer. The engine ranks across sources now (title relevance, boilerplate put down,
 * meaning fused in), so the rest is one list, and the word before each title says where it is from. */
export function groupResults(results: SearchResult[]): ResultGroup[] {
  const own: SearchResult[] = [];
  const rest: SearchResult[] = [];
  for (const r of results) (OWN.includes(r.source) ? own : rest).push(r);
  const groups: ResultGroup[] = [];
  if (own.length) groups.push({ key: 'own', title: OWN_GROUP, results: own });
  if (rest.length) groups.push({ key: 'library', title: LIBRARY_GROUP, results: rest });
  return groups;
}

/** The sources a filter chip can turn on, with the counts of the very results underneath them: the
 * chips used to sum to 61 above a line reading "40 results", because the engine counts before it
 * truncates and the screen counted after. The box's own sources are one chip; the rest, one each, in
 * the order the engine first ranks them. */
export function chipsFor(results: SearchResult[]): { key: string; title: string; sources: string[]; count: number }[] {
  const chips = new Map<string, { key: string; title: string; sources: string[]; count: number }>();
  for (const r of results) {
    const own = OWN.includes(r.source);
    const key = own ? 'own' : r.source;
    const chip = chips.get(key) ?? { key, title: own ? OWN_GROUP : chipLabel(cleanBadge(r.badge)), sources: own ? OWN : [r.source], count: 0 };
    chip.count += 1;
    chips.set(key, chip);
  }
  // the box's own chip leads whatever the engine ranked first: it is the group at the top of the screen
  return [...chips.values()].sort((a, b) => (a.key === 'own' ? -1 : b.key === 'own' ? 1 : 0));
}

/** Enough of a stem to match "bleeding" to "bleed" and "tins" to "tinned": the engine's own rule
 * (`search.stem`), so a title is marked where the engine counted it. */
function stemLite(word: string): string {
  let w = word.toLowerCase();
  for (const suffix of ['ation', 'ations', 'ings', 'ing', 'edly', 'ies', 'ied', 'ed', 'es', 's']) {
    if (w.endsWith(suffix) && w.length - suffix.length >= 3) {
      w = w.slice(0, -suffix.length) + (suffix === 'ies' || suffix === 'ied' ? 'y' : '');
      break;
    }
  }
  return w;
}

function sameWord(term: string, word: string): boolean {
  const a = stemLite(term);
  const b = stemLite(word);
  if (a === b) return true;
  const [short, long] = a.length <= b.length ? [a, b] : [b, a];
  return short.length >= 3 && long.startsWith(short) && long.length - short.length <= 3;
}

/** The query's words marked in a title, as parts to render: "Water disinfection" for "water" shows
 * where the title answers the question; "bleeding" marks "Bleed", "tins" marks "Tinned". */
export function markTitle(title: string, query: string): SnippetPart[] {
  const terms = (query ?? '').toLowerCase().split(/\s+/).map((t) => t.replace(/[^\p{L}\p{N}]/gu, '')).filter((t) => t.length >= 2);
  if (!terms.length || !title) return [{ text: title ?? '', match: false }];
  const parts: SnippetPart[] = [];
  const re = /[\p{L}\p{N}]+|[^\p{L}\p{N}]+/gu;
  for (const m of title.match(re) ?? []) {
    const word = m.toLowerCase();
    const hit = /[\p{L}\p{N}]/u.test(m) && terms.some((t) => sameWord(t, word));
    const last = parts[parts.length - 1];
    if (last && last.match === hit) last.text += m;
    else parts.push({ text: m, match: hit });
  }
  // two marked words with only a space between them are one mark: "power cut", not "power" and "cut"
  const joined: SnippetPart[] = [];
  for (const part of parts) {
    const back = joined[joined.length - 2];
    const gap = joined[joined.length - 1];
    if (part.match && back?.match && gap && !gap.match && /^\s+$/.test(gap.text)) {
      back.text += gap.text + part.text;
      joined.pop();
    } else {
      joined.push({ ...part });
    }
  }
  return joined;
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
