import { describe, it, expect, vi } from 'vitest';
import { bookPieces, fold, readableBlocks, type SectionLike } from '../../src/reader/aloud';

const section = (index: number, html: string, unload = vi.fn()): SectionLike & { unload: ReturnType<typeof vi.fn> } => {
  const doc = document.implementation.createHTMLDocument('s');
  doc.body.innerHTML = html;
  return {
    index,
    load: async () => doc.documentElement,
    unload,
    cfiFromElement: (el: Element) => `epubcfi(/6/${(index + 1) * 2}!/4/${Array.from(doc.body.querySelectorAll('*')).indexOf(el) + 2})`,
  };
};

describe('readableBlocks', () => {
  it('reads the innermost blocks once each, in order, and skips empty ones', () => {
    const doc = document.implementation.createHTMLDocument('s');
    doc.body.innerHTML = '<h1>One</h1><ul><li><p>Two</p></li><li>Three</li></ul><p></p><blockquote><p>Four</p></blockquote>';
    expect(readableBlocks(doc.documentElement).map((el) => el.textContent)).toEqual(['One', 'Two', 'Three', 'Four']);
  });
});

describe('fold', () => {
  it('starts with a short piece so the voice begins quickly, then fills pieces to the chunk size', () => {
    const blocks = [{ text: 'a'.repeat(120), cfi: 'c1' }, { text: 'b'.repeat(120), cfi: 'c2' }, { text: 'c'.repeat(300), cfi: 'c3' }, { text: 'd'.repeat(200), cfi: 'c4' }, { text: 'e'.repeat(10), cfi: 'c5' }];
    const pieces = fold(blocks, 200, 600);
    expect(pieces.map((p) => [p.cfi, p.text.length])).toEqual([['c1', 120], ['c2', 120 + 1 + 300], ['c4', 200 + 1 + 10]]);
  });

  it('gives a block longer than the size a piece of its own', () => {
    expect(fold([{ text: 'x'.repeat(900), cfi: 'c1' }, { text: 'y', cfi: 'c2' }], 200, 600).map((p) => p.cfi)).toEqual(['c1', 'c2']);
  });
});

describe('bookPieces', () => {
  it('starts at the paragraph you are on, goes on into the next chapter, and lets each chapter go', async () => {
    const one = section(0, '<h2>Chapter one</h2><p>First para.</p><p>Second para, where you are.</p><p>Third para.</p>');
    const two = section(1, '<h2>Chapter two</h2><p>Opens here.</p>');
    const spine = { get: (i: number) => [one, two][i] ?? null };
    const locate = (doc: Document, cfi: string) => (cfi === 'here' ? doc.querySelectorAll('p')[1].firstChild : null);
    const out: { text: string; cfi: string }[] = [];
    for await (const piece of bookPieces(spine, undefined, { index: 0, cfi: 'here' }, locate, { first: 30, rest: 600 })) out.push(piece);
    expect(out.map((p) => p.text)).toEqual(['Second para, where you are.', 'Third para.', 'Chapter two Opens here.']);
    expect(out[0].cfi).toBe('epubcfi(/6/2!/4/4)');
    expect(out[2].cfi).toBe('epubcfi(/6/4!/4/2)');
    expect(one.unload).toHaveBeenCalled();
    expect(two.unload).toHaveBeenCalled();
  });

  it('reads from the top of the chapter when there is no place, and the whole body when a file has no blocks', async () => {
    const plain = section(0, 'Just words in the body.');
    const spine = { get: (i: number) => (i === 0 ? plain : null) };
    const out: string[] = [];
    for await (const piece of bookPieces(spine, undefined, { index: 0, cfi: null }, () => null)) out.push(piece.text);
    expect(out).toEqual(['Just words in the body.']);
  });
});
