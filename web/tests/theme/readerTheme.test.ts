import { describe, it, expect } from 'vitest';
import { readerCss, textSizeCss, pdfViewerCss, injectStyle, READER_STYLE_ID, viewerTokens } from '../../src/theme/readerTheme';

describe('readerCss', () => {
  it('paints an article in the app\u2019s own tokens rather than a second set of colours', () => {
    const css = readerCss('blackout', { ground: '#000000', panel: '#0a0000', ink: '#ff9d93', line: '#5a1c17', link: '#ffc4bc' });
    expect(css).toContain('background:#000000');
    expect(css).toContain('color:#ff9d93');
    // a body link in the ink colour is not a link
    expect(css).toContain('color:#ffc4bc');
    expect(css).toContain('text-decoration:underline');
  });
  it('follows the dim palette it is handed, and dims photographs further with it', () => {
    const lit = readerCss('vault', { ground: '#0b120c', panel: '#121b14', ink: '#dcefdd', line: '#2c4a30', link: '#6cf08c' });
    const dim = readerCss('vault', { ground: '#050805', panel: '#0a0f0b', ink: '#b6d2b8', line: '#223a26', link: '#57c274' }, true);
    expect(lit).toContain('background:#0b120c');
    expect(dim).toContain('background:#050805');
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
    for (const theme of ['vault', 'field', 'blackout'] as const) {
      expect(pdfViewerCss(theme)).toContain('#toolbarContainer,#sidebarContainer');
      expect(pdfViewerCss(theme)).toContain('display:none !important');
      expect(pdfViewerCss(theme)).toContain('--toolbar-height:0px');
    }
  });
  it('paints the viewer in the tokens it is given, so dim reaches it too', () => {
    const css = pdfViewerCss('vault', { ground: '#050805', panel: '#0a0f0b', ink: '#b6d2b8', line: '#223a26', link: '#57c274' });
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
    expect(viewerTokens(null, 'blackout')).toEqual({ ground: '#000000', panel: '#0a0000', ink: '#ff9d93', line: '#5a1c17', link: '#ffc4bc' });
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
