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

/** Stylesheet injected into the PDF.js viewer document. */
export function pdfViewerCss(theme: Theme): string {
  switch (theme) {
    case 'blackout':
      return [
        '#viewerContainer,#outerContainer,#toolbarContainer,#sidebarContainer{background:#000 !important;color:#ff7070 !important}',
        '.pdfViewer .page{filter:invert(1) hue-rotate(180deg)}',
        '.toolbarButton,.dropdownToolbarButton,#pageNumber{color:#ff7070 !important}',
      ].join('\n');
    case 'vault':
      return [
        '#viewerContainer,#outerContainer{background:#0a0f0a !important}',
        '#toolbarContainer,#sidebarContainer{background:#0e150e !important;color:#39ff7a !important}',
        '.toolbarButton,.dropdownToolbarButton,#pageNumber{color:#39ff7a !important}',
      ].join('\n');
    case 'field':
      return '';
  }
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
