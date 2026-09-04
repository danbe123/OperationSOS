import { describe, it, expect } from 'vitest';
import { readerCss, textSizeCss, pdfViewerCss, injectStyle, READER_STYLE_ID } from '../../src/theme/readerTheme';

describe('readerCss', () => {
  it('blackout: black background, dim red text and links, dimmed images', () => {
    const css = readerCss('blackout');
    expect(css).toContain('background:#000');
    expect(css).toContain('color:#ff7070');
    expect(css).toContain('a{color:#ff9d9d');
    expect(css).toContain('img{filter:brightness(.5)}');
  });
  it('vault: near-black with green text', () => {
    const css = readerCss('vault');
    expect(css).toContain('background:#0a0f0a');
    expect(css).toContain('color:#d7f2cf');
  });
  it('field: leaves the ZIM styling alone', () => {
    expect(readerCss('field')).toBe('');
  });
});

describe('textSizeCss', () => {
  it('scales the root font size', () => {
    expect(textSizeCss(125)).toBe('html{font-size:125% !important}');
  });
});

describe('pdfViewerCss', () => {
  it('inverts pages in blackout and darkens chrome in vault', () => {
    expect(pdfViewerCss('blackout')).toContain('filter:invert(1)');
    expect(pdfViewerCss('vault')).toContain('#toolbarContainer');
    expect(pdfViewerCss('field')).toBe('');
  });
});

describe('injectStyle', () => {
  it('upserts one <style> element by id', () => {
    const doc = document.implementation.createHTMLDocument('x');
    injectStyle(doc, READER_STYLE_ID, 'body{color:red}');
    injectStyle(doc, READER_STYLE_ID, 'body{color:blue}');
    const styles = doc.querySelectorAll(`style#${READER_STYLE_ID}`);
    expect(styles).toHaveLength(1);
    expect(styles[0].textContent).toBe('body{color:blue}');
  });
  it('creates <head> when the document has none', () => {
    const doc = document.implementation.createDocument(null, 'html', null);
    injectStyle(doc as unknown as Document, 'x', 'p{}');
    expect(doc.documentElement.querySelector('head style#x')).not.toBeNull();
  });
});
