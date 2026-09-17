import { describe, expect, it } from 'vitest';
import type { Location } from 'epubjs/types/rendition';
import { readingPercent } from '../../src/reader/position';

const loc = (index: number, page: number, total: number, atEnd = false): Location => {
  const point = { index, cfi: 'x', href: '', location: 0, percentage: 0, displayed: { page, total } };
  return { start: point, end: point, atStart: false, atEnd };
};

describe('readingPercent', () => {
  it('walks the spine and the pages inside the current section', () => {
    expect(readingPercent(loc(0, 1, 10), 4)).toBe(0);
    expect(readingPercent(loc(1, 1, 10), 4)).toBe(25);
    expect(readingPercent(loc(1, 6, 10), 4)).toBe(37.5);
  });
  it('is the page share alone when the whole book is one section', () => {
    expect(readingPercent(loc(0, 51, 100), 1)).toBe(50);
  });
  it('is 100 at the end and never above it or below 0', () => {
    expect(readingPercent(loc(3, 10, 10, true), 4)).toBe(100);
    expect(readingPercent(loc(9, 1, 1), 4)).toBe(100);
  });
  it('copes with a spine length epub.js has not filled in yet', () => {
    expect(readingPercent(loc(0, 3, 4), undefined)).toBe(50);
  });
});
