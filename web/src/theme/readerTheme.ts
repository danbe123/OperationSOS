import type { Theme } from './ThemeProvider';

export const READER_STYLE_ID = 'sos-reader-theme';
export const TEXT_SIZE_STYLE_ID = 'sos-reader-size';

/** Stylesheet injected into a Kiwix document on every load. Field leaves the ZIM's own light styling. */
export function readerCss(theme: Theme): string {
  switch (theme) {
    case 'blackout':
      return [
        'html,body{background:#000 !important;color:#ff7070 !important}',
        'body *{background-color:transparent !important;color:inherit !important;border-color:#3a0000 !important}',
        'a{color:#ff9d9d !important}',
        'img{filter:brightness(.5)}',
      ].join('\n');
    case 'vault':
      return [
        'html,body{background:#0a0f0a !important;color:#d7f2cf !important}',
        'body *{background-color:transparent !important;color:inherit !important;border-color:#2a4a2a !important}',
        'a{color:#39ff7a !important}',
      ].join('\n');
    case 'field':
      return '';
  }
}

export function textSizeCss(percent: number): string {
  return `html{font-size:${percent}% !important}`;
}

/** The four token values the PDF viewer needs, read from the app's own root so the viewer follows
 * the theme *and* the dim palette rather than carrying a second set of colours. */
export type ViewerTokens = { ground: string; panel: string; ink: string; line: string };

const VIEWER_FALLBACK: Record<Theme, ViewerTokens> = {
  vault: { ground: '#0b120c', panel: '#121b14', ink: '#dcefdd', line: '#2c4a30' },
  field: { ground: '#f3efe4', panel: '#ffffff', ink: '#1b1b1b', line: '#c3b9a2' },
  blackout: { ground: '#000000', panel: '#0a0000', ink: '#ff9d93', line: '#5a1c17' },
};

/** Read the live token values off a document's root element. */
export function viewerTokens(root: Element | null, theme: Theme): ViewerTokens {
  const fallback = VIEWER_FALLBACK[theme];
  if (!root || typeof getComputedStyle !== 'function') return fallback;
  const style = getComputedStyle(root);
  const read = (name: string, or: string) => style.getPropertyValue(name).trim() || or;
  return {
    ground: read('--ground', fallback.ground),
    panel: read('--panel', fallback.panel),
    ink: read('--ink', fallback.ink),
    line: read('--line', fallback.line),
  };
}

/** Stylesheet injected into the PDF.js viewer document. The viewer's own toolbar was the one vendor
 * surface in the box: a light-grey bar of twelve wordless icons, a page box reading "0 of 0" and an
 * "Automatic Zoom" select, in every theme including blackout. It is hidden here and the app draws
 * the chrome itself (`screens/Doc.tsx`), in the app's own tokens. */
export function pdfViewerCss(theme: Theme, tokens?: ViewerTokens): string {
  const t = tokens ?? VIEWER_FALLBACK[theme];
  const rules = [
    ':root{--toolbar-height:0px !important}',
    '#toolbarContainer,#sidebarContainer,#sidebarResizer,#findbar,#secondaryToolbar,#editorUndoBar{display:none !important}',
    '#outerContainer.sidebarOpen #viewerContainer{inset-inline-start:0 !important}',
    `#outerContainer,#mainContainer,#viewerContainer{background:${t.ground} !important;color:${t.ink} !important}`,
    `#errorWrapper{background:${t.panel} !important;color:${t.ink} !important;border:1px solid ${t.line} !important}`,
  ];
  // Blackout is a red-on-black theme for night vision: a white page in it is a torch in the face.
  if (theme === 'blackout') rules.push('.pdfViewer .page{filter:invert(1) hue-rotate(180deg)}');
  return rules.join('\n');
}

/** Create or replace a <style id> in the document head. Works on any same-origin document. */
export function injectStyle(doc: Document, id: string, css: string): void {
  let head = doc.head as HTMLHeadElement | null;
  if (!head) {
    head = doc.createElement('head');
    doc.documentElement.insertBefore(head, doc.documentElement.firstChild);
  }
  let style = head.querySelector<HTMLStyleElement>(`style#${id}`);
  if (!style) {
    style = doc.createElement('style');
    style.id = id;
    head.appendChild(style);
  }
  style.textContent = css;
}
