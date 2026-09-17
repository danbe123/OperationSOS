/** A book as pieces for the voice: from where you are, paragraph by paragraph, chapter after chapter,
 * each piece with the CFI of its first paragraph so the page can follow the voice and the box can
 * remember where the reading got to. The chapters are read from the book's files, not from the screen,
 * so the voice can go on past the end of what is rendered — and the furniture around a book (a licence,
 * a contents table, a list of illustrations, captions, footnote marks) is taken out first, as a person
 * reading aloud would skip it. Spec: docs/superpowers/specs/2026-09-17-read-aloud-books-design.md. */
import { CHUNK_CHARS } from '../tools/speech';

/** The first piece is short so the voice starts within a couple of seconds on the Pi; the rest are
 * the size the box already reads a briefing in. */
export const FIRST_CHUNK_CHARS = 200;
/** How many files from the front are searched for chapter one. */
const FRONT_FILES = 15;

export type Piece = { text: string; cfi: string; heading?: boolean };

/** What the reader hands over: enough of an epub.js spine and section to walk a book's text. */
export type SpineLike = { get(index: number): SectionLike | null };
export type SectionLike = {
  index: number;
  load(request?: unknown): Promise<Element>;
  unload?(): void;
  cfiFromElement(el: Element): string;
};

/** The blocks a voice reads one after another: the innermost ones, so a list item's paragraph is read
 * once and not again as its item. */
const BLOCKS = 'p, h1, h2, h3, h4, h5, h6, li, blockquote, dd, dt, pre';
/* By local name: a Gutenberg file is XHTML, and in an XML document `tagName` keeps the file's case
   while `localName` is always lower. The first cut compared against "H2" and found no chapter anywhere. */
const HEADINGS = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
const isHeading = (el: Element) => HEADINGS.has(el.localName);

/** The furniture: Project Gutenberg's licence header and footer, its cover wrapper, transcriber's notes
 * and title pages; contents and illustration tables and any navigation; every table (a table read aloud
 * is noise, and the reflowed guides carry none); figure captions and "(Larger)" links; footnote marks and
 * page numbers. Removed from a copy of the chapter before its blocks are taken. */
export const FURNITURE = [
  '.pgheader', '.pg-boilerplate', '.pgfooter', '#pg-header', '#pg-footer', '.x-ebookmaker-cover', '.transnote', '.titlepage',
  'nav', 'table', '#toc', '#loi', '.toc', '.loi', '[epub\\:type~="toc"]', '[epub\\:type~="landmarks"]',
  'figcaption', 'a[title="linked image"]', 'sup', '.pagenum', '.pageno', '.footnote-anchor', 'a.fnanchor', 'script', 'style',
].join(', ');

/** A chapter's heading: "CHAPTER I", "Part Two", "Book III.", "Letter 4", a bare "XII" or "7". */
const CHAPTER = /^(chapter|part|book|canto|letter|prologue|epilogue|act|scene|stave)\b/i;
const ROMAN = /^(?=[ivxlc])(c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\.?$/i;
const NUMBERED = /^\d{1,3}\.?$/;

export function isChapterHeading(text: string): boolean {
  const t = text.trim();
  return CHAPTER.test(t) || ROMAN.test(t) || NUMBERED.test(t);
}

function romanValue(s: string): number {
  const v: Record<string, number> = { i: 1, v: 5, x: 10, l: 50, c: 100 };
  let total = 0;
  const letters = s.toLowerCase().replace(/\./g, '');
  for (let i = 0; i < letters.length; i++) {
    const a = v[letters[i]];
    const b = v[letters[i + 1]] ?? 0;
    total += a < b ? -a : a;
  }
  return total;
}

/** What the voice says for a heading: "CHAPTER I" and a bare "XII" become "Chapter 1" and "Chapter 12",
 * which Piper says as numbers rather than as letters; anything else is said as written. */
export function spokenHeading(text: string): string {
  const t = text.replace(/\s+/g, ' ').trim();
  if (ROMAN.test(t)) return `Chapter ${romanValue(t)}`;
  if (NUMBERED.test(t)) return `Chapter ${t.replace('.', '')}`;
  const m = /^(chapter|part|book|canto|letter|act|scene|stave)\s+([ivxlc]+)\b\.?(.*)$/i.exec(t);
  if (m && ROMAN.test(m[2])) {
    const word = m[1][0].toUpperCase() + m[1].slice(1).toLowerCase();
    const rest = m[3].replace(/^[\s.:—–-]+/, '');
    return rest ? `${word} ${romanValue(m[2])}. ${rest}` : `${word} ${romanValue(m[2])}`;
  }
  return t;
}

/** A block that is mostly links is a list of contents written as paragraphs, not prose. */
function mostlyLinks(el: Element): boolean {
  const all = (el.textContent ?? '').replace(/\s+/g, ' ').trim().length;
  if (all === 0) return true;
  let linked = 0;
  for (const a of Array.from(el.querySelectorAll('a'))) linked += (a.textContent ?? '').replace(/\s+/g, ' ').trim().length;
  return linked / all >= 0.6;
}

/** The blocks of a chapter a voice would read, in order, with the furniture gone. The chapter's
 * elements are the ones returned (not copies), so a CFI can be made from each. */
export function readableBlocks(root: Element): Element[] {
  const furniture = new Set(Array.from(root.querySelectorAll(FURNITURE)));
  const inFurniture = (el: Element): boolean => {
    for (let n: Element | null = el; n; n = n.parentElement) if (furniture.has(n)) return true;
    return false;
  };
  const found = Array.from(root.querySelectorAll(BLOCKS)).filter((el) => !inFurniture(el) && !el.querySelector(BLOCKS));
  return found.filter((el) => blockText(el).length > 0 && !mostlyLinks(el));
}

/** The words of one block, without the furniture inside it. */
export function blockText(el: Element): string {
  const copy = el.cloneNode(true) as Element;
  for (const junk of Array.from(copy.querySelectorAll(FURNITURE))) junk.remove();
  for (const br of Array.from(copy.querySelectorAll('br'))) br.replaceWith(' ');   // "CHAPTER I<br/>Robinson’s Family" is two words
  return (copy.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The block a CFI sits in, or null when the CFI does not resolve in this document. */
export type Locate = (doc: Document, cfi: string) => Node | null;

function blockOf(node: Node | null, blocks: Element[]): number {
  let n: Node | null = node;
  while (n) {
    const i = blocks.indexOf(n as Element);
    if (i >= 0) return i;
    n = n.parentNode;
  }
  return -1;
}

type Block = { text: string; cfi: string; heading: boolean };

/** Fold blocks into pieces of up to `max` characters, never cutting a block that fits on its own; a
 * block longer than `max` becomes its own piece (the voice's own chunking cuts it further). A heading
 * is a piece on its own, so the voice pauses either side of it. */
export function fold(blocks: Block[], firstMax: number, max: number): Piece[] {
  const pieces: Piece[] = [];
  let open: Piece | null = null;
  for (const b of blocks) {
    const limit = pieces.length === 0 ? firstMax : max;
    if (open && !b.heading && !open.heading && open.text.length + 1 + b.text.length <= limit) {
      open.text = `${open.text} ${b.text}`;
      continue;
    }
    if (open) pieces.push(open);
    open = { text: b.text, cfi: b.cfi, ...(b.heading ? { heading: true } : {}) };
    if (b.heading || open.text.length >= limit) { pieces.push(open); open = null; }
  }
  if (open) pieces.push(open);
  return pieces;
}

async function chapterBlocks(section: SectionLike, request: unknown): Promise<{ doc: Document; blocks: Element[] }> {
  const root = await section.load(request);
  const doc = root.ownerDocument ?? (root as unknown as Document);
  let blocks = readableBlocks(root);
  if (blocks.length === 0) {
    const body = doc.body ?? root;
    if (blockText(body).length > 0 && !body.querySelector(FURNITURE)) blocks = [body];
  }
  return { doc, blocks };
}

/** Where the story starts: the first block, in the first files of the book, whose heading says Chapter
 * (or Part, Book, a bare numeral); failing that, the first file with three readable paragraphs; failing
 * that, the first file with anything to read. */
export async function firstChapter(spine: SpineLike, request: unknown): Promise<{ index: number; block: number } | null> {
  let fallback: { index: number; block: number } | null = null;
  let first: { index: number; block: number } | null = null;
  for (let index = 0; index < FRONT_FILES; index += 1) {
    const section = spine.get(index);
    if (!section) break;
    const { blocks } = await chapterBlocks(section, request);
    section.unload?.();
    const at = blocks.findIndex((el) => isHeading(el) && isChapterHeading(blockText(el)));
    if (at >= 0) return { index, block: at };
    if (!fallback && blocks.filter((el) => el.localName === 'p').length >= 3) fallback = { index, block: 0 };
    if (!first && blocks.length > 0) first = { index, block: 0 };
  }
  return fallback ?? first;
}

/** Every piece of the book from `start` on. From the front matter — anything before chapter one — the
 * reading starts at chapter one instead. Each chapter's file is read as the voice reaches it and let go
 * of afterwards; the generator stops when the caller does. */
export async function* bookPieces(spine: SpineLike, request: unknown, start: { index: number; cfi: string | null }, locate: Locate,
  sizes: { first: number; rest: number } = { first: FIRST_CHUNK_CHARS, rest: CHUNK_CHARS }): AsyncGenerator<Piece> {
  const opening = await firstChapter(spine, request);
  let index = start.index;
  let from = 0;
  let placed = false;
  if (start.cfi) {
    const section = spine.get(index);
    if (section) {
      const { doc, blocks } = await chapterBlocks(section, request);
      const at = blockOf(locate(doc, start.cfi), blocks);
      if (at >= 0) { from = at; placed = true; }
      section.unload?.();
    }
  }
  // Before the story, or nowhere in particular: chapter one.
  if (opening && (!placed || index < opening.index || (index === opening.index && from < opening.block))) {
    index = opening.index;
    from = opening.block;
  }
  let first = true;
  for (; ; index += 1) {
    const section = spine.get(index);
    if (!section) return;
    const { blocks } = await chapterBlocks(section, request);
    const texts: Block[] = blocks.slice(first ? from : 0).map((el) => {
      const heading = isHeading(el);
      const text = blockText(el);
      return { text: heading ? spokenHeading(text) : text, cfi: section.cfiFromElement(el), heading };
    });
    for (const piece of fold(texts, first ? sizes.first : sizes.rest, sizes.rest)) {
      yield piece;
      first = false;
    }
    section.unload?.();
    first = false;
  }
}
