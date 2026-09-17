import { describe, it, expect, vi } from 'vitest';
import { bookPieces, firstChapter, fold, isChapterHeading, readableBlocks, spokenHeading, type SectionLike } from '../../src/reader/aloud';

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
const spineOf = (...sections: SectionLike[]) => ({ get: (i: number) => sections[i] ?? null });
const all = async (gen: AsyncGenerator<{ text: string; cfi: string }>) => { const out: { text: string; cfi: string }[] = []; for await (const p of gen) out.push(p); return out; };

describe('readableBlocks', () => {
  it('reads the innermost blocks once each, in order, and skips empty ones', () => {
    const doc = document.implementation.createHTMLDocument('s');
    doc.body.innerHTML = '<h1>One</h1><ul><li><p>Two</p></li><li>Three</li></ul><p></p><blockquote><p>Four</p></blockquote>';
    expect(readableBlocks(doc.documentElement).map((el) => el.textContent)).toEqual(['One', 'Two', 'Three', 'Four']);
  });

  it('leaves out the furniture: the licence, the contents and illustration tables, captions, footnote marks, link lists', () => {
    const doc = document.implementation.createHTMLDocument('s');
    doc.body.innerHTML = `
      <section class="pg-boilerplate pgheader"><h2>The Project Gutenberg eBook of Crusoe</h2><p>This ebook is for the use of anyone.</p></section>
      <div class="transnote"><p>Transcriber’s note: larger versions of the pictures…</p></div>
      <h2>CONTENTS</h2><table id="toc"><tr><td>CHAPTER I</td><td>1</td></tr></table>
      <p><a href="#c1">Chapter one</a> <a href="#c2">Chapter two</a></p>
      <figure><img alt=""/><figcaption><p><a title="linked image">(Larger)</a></p></figcaption></figure>
      <h2 id="c1">CHAPTER I</h2>
      <p>I was born in the year 1632,<sup><a class="fnanchor">[1]</a></sup> in the city of York.<span class="pagenum">2</span></p>
      <p><a href="#n1">1</a></p>`;
    const blocks = readableBlocks(doc.documentElement);
    expect(blocks.map((el) => el.tagName + ':' + (el.textContent ?? '').trim().slice(0, 12))).toEqual(['H2:CONTENTS', 'H2:CHAPTER I', 'P:I was born i']);
  });
});

describe('headings', () => {
  it('knows a chapter heading, and says numerals as numbers', () => {
    for (const t of ['CHAPTER I', 'Chapter 12', 'Part Two', 'BOOK III.', 'XII', '7.', 'Letter 4', 'Prologue']) expect(isChapterHeading(t), t).toBe(true);
    for (const t of ['ROBINSON CRUSOE', 'CONTENTS', 'Illustrator’s preface', 'Fever']) expect(isChapterHeading(t), t).toBe(false);
    expect(spokenHeading('CHAPTER I')).toBe('Chapter 1');
    expect(spokenHeading('CHAPTER XIV.')).toBe('Chapter 14');
    expect(spokenHeading('Chapter IV. The Storm')).toBe('Chapter 4. The Storm');
    expect(spokenHeading('XII')).toBe('Chapter 12');
    expect(spokenHeading('3')).toBe('Chapter 3');
    expect(spokenHeading('Part Two')).toBe('Part Two');
    expect(spokenHeading('Fever')).toBe('Fever');
  });
});

describe('fold', () => {
  it('starts with a short piece so the voice begins quickly, then fills pieces to the chunk size', () => {
    const b = (text: string, cfi: string) => ({ text, cfi, heading: false });
    const blocks = [b('a'.repeat(120), 'c1'), b('b'.repeat(120), 'c2'), b('c'.repeat(300), 'c3'), b('d'.repeat(200), 'c4'), b('e'.repeat(10), 'c5')];
    expect(fold(blocks, 200, 600).map((p) => [p.cfi, p.text.length])).toEqual([['c1', 120], ['c2', 120 + 1 + 300], ['c4', 200 + 1 + 10]]);
  });

  it('gives a heading a piece of its own, so the voice pauses either side of it', () => {
    const pieces = fold([{ text: 'Before.', cfi: 'c1', heading: false }, { text: 'Chapter 2', cfi: 'c2', heading: true }, { text: 'After.', cfi: 'c3', heading: false }], 600, 600);
    expect(pieces.map((p) => p.text)).toEqual(['Before.', 'Chapter 2', 'After.']);
    expect(pieces[1].heading).toBe(true);
  });

  it('gives a block longer than the size a piece of its own', () => {
    expect(fold([{ text: 'x'.repeat(900), cfi: 'c1', heading: false }, { text: 'y', cfi: 'c2', heading: false }], 200, 600).map((p) => p.cfi)).toEqual(['c1', 'c2']);
  });
});

describe('firstChapter', () => {
  it('finds the first chapter heading in the front files, past the cover, the licence, the preface and the contents', async () => {
    const spine = spineOf(
      section(0, '<div class="x-ebookmaker-cover"><img alt=""/></div>'),
      section(1, '<section class="pgheader"><p>The Project Gutenberg eBook of Robinson Crusoe.</p></section>'),
      section(2, '<h2>ILLUSTRATOR’S PREFACE</h2><p>One.</p><p>Two.</p><p>Three.</p>'),
      section(3, '<h2>CONTENTS</h2><table id="toc"><tr><td>I</td></tr></table>'),
      section(4, '<h1>ROBINSON CRUSOE</h1><h2>CHAPTER I</h2><p>I was born in the year 1632.</p>'),
    );
    expect(await firstChapter(spine, undefined)).toEqual({ index: 4, block: 1 });
  });

  it('falls back to the first file with three paragraphs, as a guide with no chapter headings has', async () => {
    const spine = spineOf(section(0, '<h1>Where There Is No Doctor</h1>'), section(1, '<h2>Fever</h2><p>One.</p><p>Two.</p><p>Three.</p>'));
    expect(await firstChapter(spine, undefined)).toEqual({ index: 1, block: 0 });
  });
});

describe('firstChapter in an XHTML file, as Gutenberg ships them', () => {
  it('finds the chapter heading although XML keeps tag names in the file\'s own case', async () => {
    const xml = '<html xmlns="http://www.w3.org/1999/xhtml"><body><div class="chapter"><h2 class="nobreak">CHAPTER I<br/><span class="subhead">Robinson’s Family</span></h2></div><p>I was born in the year 1632.</p></body></html>';
    const doc = new DOMParser().parseFromString(xml, 'application/xhtml+xml');
    const title = new DOMParser().parseFromString('<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>ROBINSON CRUSOE</h1><p class="larger">by DANIEL DEFOE</p></body></html>', 'application/xhtml+xml');
    const sect = (index: number, d: Document): SectionLike => ({ index, load: async () => d.documentElement, cfiFromElement: () => `c${index}` });
    expect(await firstChapter(spineOf(sect(0, title), sect(1, doc)), undefined)).toEqual({ index: 1, block: 0 });
    const out = await all(bookPieces(spineOf(sect(0, title), sect(1, doc)), undefined, { index: 0, cfi: null }, () => null));
    expect(out.map((p) => p.text)).toEqual(['Chapter 1. Robinson’s Family', 'I was born in the year 1632.']);
  });
});

describe('bookPieces', () => {
  it('from the front matter, starts at chapter one and says the heading as a number', async () => {
    const licence = section(0, '<section class="pgheader"><p>The Project Gutenberg eBook.</p></section>');
    const contents = section(1, '<h2>CONTENTS</h2><table id="toc"><tr><td>CHAPTER I</td></tr></table>');
    const one = section(2, '<h1>ROBINSON CRUSOE</h1><h2>CHAPTER I</h2><p>I was born in the year 1632.</p>');
    const two = section(3, '<h2>CHAPTER II</h2><p>Opens here.</p>');
    const out = await all(bookPieces(spineOf(licence, contents, one, two), undefined, { index: 1, cfi: 'somewhere-in-the-contents' }, () => null));
    expect(out.map((p) => p.text)).toEqual(['Chapter 1', 'I was born in the year 1632.', 'Chapter 2', 'Opens here.']);
    expect(out[0].cfi).toBe('epubcfi(/6/6!/4/3)');
    expect(one.unload).toHaveBeenCalled();
  });

  it('from inside the story, starts at the paragraph you are on and goes on into the next chapter', async () => {
    const one = section(0, '<h2>Chapter I</h2><p>First para.</p><p>Second para, where you are.</p><p>Third para.</p>');
    const two = section(1, '<h2>Chapter II</h2><p>Opens here.</p>');
    const locate = (doc: Document, cfi: string) => (cfi === 'here' ? doc.querySelectorAll('p')[1].firstChild : null);
    const out = await all(bookPieces(spineOf(one, two), undefined, { index: 0, cfi: 'here' }, locate, { first: 30, rest: 600 }));
    expect(out.map((p) => p.text)).toEqual(['Second para, where you are.', 'Third para.', 'Chapter 2', 'Opens here.']);
    expect(out[0].cfi).toBe('epubcfi(/6/2!/4/4)');
    expect(two.unload).toHaveBeenCalled();
  });

  it('reads the whole body when a file has no blocks at all', async () => {
    const out = await all(bookPieces(spineOf(section(0, 'Just words in the body.')), undefined, { index: 0, cfi: null }, () => null));
    expect(out.map((p) => p.text)).toEqual(['Just words in the body.']);
  });
});
