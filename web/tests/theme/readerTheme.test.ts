import { describe, it, expect } from 'vitest';
import { readerCss, textSizeCss, pdfViewerCss, injectStyle, READER_STYLE_ID, viewerTokens } from '../../src/theme/readerTheme';

describe('readerCss', () => {
  it('paints an article in the app\u2019s own tokens rather than a second set of colours', () => {
    const css = readerCss('mono', { ground: '#000000', panel: '#0a0a0a', ink: '#f2f2f2', line: '#2a2a2a', link: '#ffffff' });
    expect(css).toContain('background:#000000');
    expect(css).toContain('color:#f2f2f2');
    // a body link in the ink colour is not a link
    expect(css).toContain('color:#ffffff');
    expect(css).toContain('text-decoration:underline');
  });
  it('follows the dim palette it is handed, and dims photographs further with it', () => {
    const lit = readerCss('mono', { ground: '#000000', panel: '#0a0a0a', ink: '#f2f2f2', line: '#2a2a2a', link: '#ffffff' });
    const dim = readerCss('mono', { ground: '#000000', panel: '#000000', ink: '#c8c8c8', line: '#232323', link: '#d4d4d4' }, true);
    expect(lit).toContain('color:#f2f2f2');
    expect(dim).toContain('color:#c8c8c8');
    expect(lit).toContain('brightness(0.55)');
    expect(dim).toContain('brightness(0.35)');
  });
  it('field leaves the ZIM styling alone until the box dims', () => {
    expect(readerCss('field')).toBe('');
    expect(readerCss('field', undefined, true)).toContain('brightness');
  });
});

describe('textSizeCss', () => {
  it('scales the root font size', () => {
    expect(textSizeCss(125)).toBe('html{font-size:125% !important}');
  });
});

describe('pdfViewerCss', () => {
  it('hides the viewer\'s own toolbar in every theme, so the app can draw the chrome itself', () => {
    for (const theme of ['field', 'mono'] as const) {
      expect(pdfViewerCss(theme)).toContain('#toolbarContainer,#sidebarContainer');
      expect(pdfViewerCss(theme)).toContain('display:none !important');
      expect(pdfViewerCss(theme)).toContain('--toolbar-height:0px');
    }
  });
  it('paints the viewer in the tokens it is given, so dim reaches it too', () => {
    const css = pdfViewerCss('mono', { ground: '#000000', panel: '#000000', ink: '#c8c8c8', line: '#232323', link: '#d4d4d4' });
    expect(css).toContain('background:#000000');
    expect(css).toContain('color:#c8c8c8');
  });
  it('inverts the page in mono only: a white page at 03:00 is a torch in the face', () => {
    expect(pdfViewerCss('mono')).toContain('filter:invert(1)');
    expect(pdfViewerCss('field')).not.toContain('filter:invert(1)');
  });
});

describe('viewerTokens', () => {
  it('reads the live values off the app root, and falls back to the theme when it cannot', () => {
    const root = document.createElement('div');
    root.style.setProperty('--ground', '#123456');
    document.body.appendChild(root);
    expect(viewerTokens(root, 'mono').ground).toBe('#123456');
    expect(viewerTokens(null, 'mono')).toEqual({ ground: '#000000', panel: '#0a0a0a', ink: '#f2f2f2', line: '#2a2a2a', link: '#ffffff' });
    expect(viewerTokens(null, 'field')).toEqual({ ground: '#ffffff', panel: '#f3efe4', ink: '#1b1b1b', line: '#c3b9a2', link: '#1a3f8a' });
    root.remove();
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
