import { describe, it, expect } from 'vitest';
import { readerCss, textSizeCss, pdfViewerCss, injectStyle, READER_STYLE_ID, viewerTokens } from '../../src/theme/readerTheme';

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
  it('hides the viewer\'s own toolbar in every theme, so the app can draw the chrome itself', () => {
    for (const theme of ['vault', 'field', 'blackout'] as const) {
      expect(pdfViewerCss(theme)).toContain('#toolbarContainer,#sidebarContainer');
      expect(pdfViewerCss(theme)).toContain('display:none !important');
      expect(pdfViewerCss(theme)).toContain('--toolbar-height:0px');
    }
  });
  it('paints the viewer in the tokens it is given, so dim reaches it too', () => {
    const css = pdfViewerCss('vault', { ground: '#050805', panel: '#0a0f0b', ink: '#b6d2b8', line: '#223a26' });
    expect(css).toContain('background:#050805');
    expect(css).toContain('color:#b6d2b8');
  });
  it('inverts the page in blackout only: a white page at 03:00 is a torch in the face', () => {
    expect(pdfViewerCss('blackout')).toContain('filter:invert(1)');
    expect(pdfViewerCss('vault')).not.toContain('filter:invert(1)');
    expect(pdfViewerCss('field')).not.toContain('filter:invert(1)');
  });
});

describe('viewerTokens', () => {
  it('reads the live values off the app root, and falls back to the theme when it cannot', () => {
    const root = document.createElement('div');
    root.style.setProperty('--ground', '#123456');
    document.body.appendChild(root);
    expect(viewerTokens(root, 'vault').ground).toBe('#123456');
    expect(viewerTokens(null, 'blackout')).toEqual({ ground: '#000000', panel: '#0a0000', ink: '#ff9d93', line: '#5a1c17' });
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
