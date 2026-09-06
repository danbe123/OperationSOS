import type { Theme } from './ThemeProvider';

export const READER_STYLE_ID = 'sos-reader-theme';
export const TEXT_SIZE_STYLE_ID = 'sos-reader-size';

export function textSizeCss(percent: number): string {
  return `html{font-size:${percent}% !important}`;
}

/** The token values a viewer needs, read from the app's own root so the PDF viewer, the article
 * reader and the EPUB reader all follow the theme *and* the dim palette, rather than each carrying a
 * set of colours of its own. */
export type ViewerTokens = { ground: string; panel: string; ink: string; line: string; link: string };

const VIEWER_FALLBACK: Record<Theme, ViewerTokens> = {
  vault: { ground: '#0b120c', panel: '#121b14', ink: '#dcefdd', line: '#2c4a30', link: '#6cf08c' },
  field: { ground: '#f3efe4', panel: '#ffffff', ink: '#1b1b1b', line: '#c3b9a2', link: '#1a3f8a' },
  blackout: { ground: '#000000', panel: '#0a0000', ink: '#ff9d93', line: '#5a1c17', link: '#ffc4bc' },
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
    link: read('--link', fallback.link),
  };
}

/** Whether the box is in its dim palette right now, so an injected stylesheet can follow it. */
export function isDim(root: Element | null): boolean {
  return (root as HTMLElement | null)?.dataset?.dim === 'on';
}

/** Stylesheet injected into a Kiwix document on every load, in the app's own tokens — the theme and
 * the dim palette both, read off the live root. It used to carry a second set of colours nobody
 * could find: `#0a0f0a`, `#39ff7a`, `#2a4a2a`, `#ff7070`, none of them in `tokens.css` and none of
 * them following dim. Field leaves the ZIM's own light styling alone. */
export function readerCss(theme: Theme, tokens?: ViewerTokens, dim = false): string {
  const t = tokens ?? VIEWER_FALLBACK[theme];
  if (theme === 'field') return dim ? 'img,video{filter:brightness(.8)}' : '';
  return [
    `html,body{background:${t.ground} !important;color:${t.ink} !important}`,
    `body *{background-color:transparent !important;color:inherit !important;border-color:${t.line} !important}`,
    // A body link in the ink colour is not a link. The accent is the one colour that says "go here".
    `a,a *{color:${t.link} !important;text-decoration:underline !important}`,
    // A full-brightness colour photograph inside a night-vision theme is a torch in the face.
    `img,video{filter:brightness(${dim ? 0.35 : 0.55})}`,
  ].join('\n');
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
