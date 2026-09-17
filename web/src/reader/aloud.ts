/** A book as pieces for the voice: from where you are, paragraph by paragraph, chapter after chapter,
 * each piece with the CFI of its first paragraph so the page can follow the voice and the box can
 * remember where the reading got to. The chapters are read from the book's files, not from the screen,
 * so the voice can go on past the end of what is rendered. */
import { CHUNK_CHARS } from '../tools/speech';

/** The first piece is short so the voice starts within a couple of seconds on the Pi; the rest are
 * the size the box already reads a briefing in. */
export const FIRST_CHUNK_CHARS = 200;

export type Piece = { text: string; cfi: string };

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
const BLOCKS = 'p, h1, h2, h3, h4, h5, h6, li, blockquote, dd, dt, figcaption, td, th, pre';

export function readableBlocks(root: Element): Element[] {
  const found = Array.from(root.querySelectorAll(BLOCKS)).filter((el) => !el.querySelector(BLOCKS));
  return found.filter((el) => (el.textContent ?? '').trim().length > 0);
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

/** Fold blocks into pieces of up to `max` characters, never cutting a block that fits on its own; a
 * block longer than `max` becomes its own piece (the voice's own chunking cuts it further). */
export function fold(blocks: { text: string; cfi: string }[], firstMax: number, max: number): Piece[] {
  const pieces: Piece[] = [];
  let open: Piece | null = null;
  for (const b of blocks) {
    const limit = pieces.length === 0 ? firstMax : max;
    if (open && open.text.length + 1 + b.text.length <= limit) {
      open.text = `${open.text} ${b.text}`;
      continue;
    }
    if (open) pieces.push(open);
    open = { text: b.text, cfi: b.cfi };
    if (open.text.length >= limit) { pieces.push(open); open = null; }
  }
  if (open) pieces.push(open);
  return pieces;
}

/** Every piece of the book from `start` on. Each chapter's file is read as the voice reaches it and
 * let go of afterwards; the generator stops when the caller does. */
export async function* bookPieces(spine: SpineLike, request: unknown, start: { index: number; cfi: string | null }, locate: Locate,
  sizes: { first: number; rest: number } = { first: FIRST_CHUNK_CHARS, rest: CHUNK_CHARS }): AsyncGenerator<Piece> {
  let first = true;
  for (let index = start.index; ; index += 1) {
    const section = spine.get(index);
    if (!section) return;
    const root = await section.load(request);
    const doc = root.ownerDocument ?? (root as unknown as Document);
    let blocks = readableBlocks(root);
    if (blocks.length === 0) {
      const body = doc.body ?? root;
      if ((body.textContent ?? '').trim()) blocks = [body];
    }
    let from = 0;
    if (first && start.cfi) {
      const at = blockOf(locate(doc, start.cfi), blocks);
      if (at > 0) from = at;
    }
    const texts = blocks.slice(from).map((el) => ({ text: (el.textContent ?? '').replace(/\s+/g, ' ').trim(), cfi: section.cfiFromElement(el) }));
    for (const piece of fold(texts, first ? sizes.first : sizes.rest, sizes.rest)) {
      yield piece;
      first = false;
    }
    section.unload?.();
    first = false;
  }
}
