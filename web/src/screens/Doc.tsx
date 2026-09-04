import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useParams } from 'react-router';
import ePub, { type Rendition } from 'epubjs';
import { api } from '../api/client';
import { errorMessage, useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Icon } from '../icons';
import { replaceFrameLocation } from '../links';
import { injectStyle, pdfViewerCss, READER_STYLE_ID } from '../theme/readerTheme';
import { useTheme, type Theme } from '../theme/ThemeProvider';

export function pdfViewerUrl(fileUrl: string, theme: Theme, hash: string): string {
  return `/pdfjs/web/viewer.html?file=${encodeURIComponent(fileUrl)}&theme=${theme}${hash}`;
}

function PdfFrame({ url, theme, hash }: { url: string; theme: Theme; hash: string }) {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [initialSrc] = useState(() => pdfViewerUrl(url, theme, hash));
  const themeRef = useRef(theme);
  themeRef.current = theme;

  const apply = useCallback(() => {
    const doc = frameRef.current?.contentDocument;
    if (doc) injectStyle(doc, READER_STYLE_ID, pdfViewerCss(themeRef.current));
  }, []);
  useEffect(() => { apply(); }, [theme, apply]);

  // A later #page= link to the same document: change the viewer's hash in place (PDF.js listens for hashchange).
  useEffect(() => {
    const win = frameRef.current?.contentWindow;
    if (!win || !hash || !win.location.href.startsWith(window.location.origin)) return;
    if (win.location.hash !== hash) replaceFrameLocation(win, win.location.pathname + win.location.search + hash);
  }, [hash]);

  return (
    <div className="frame-wrap">
      <iframe ref={frameRef} title="Document" src={initialSrc} onLoad={apply} />
    </div>
  );
}

const EPUB_SIZES = [100, 125, 150];

function EpubReader({ url, theme }: { url: string; theme: Theme }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const [size, setSize] = useState(100);
  const [error, setError] = useState<string | null>(null);
  const themeRef = useRef(theme);
  themeRef.current = theme;

  useEffect(() => {
    if (!hostRef.current) return;
    const book = ePub(url);
    const rendition = book.renderTo(hostRef.current, { width: '100%', height: '100%', flow: 'paginated' });
    renditionRef.current = rendition;
    rendition.themes.register('vault', { body: { background: '#0a0f0a', color: '#d7f2cf' }, a: { color: '#39ff7a' } });
    rendition.themes.register('blackout', { body: { background: '#000000', color: '#ff7070' }, a: { color: '#ff9d9d' }, img: { filter: 'brightness(.5)' } });
    rendition.themes.register('field', { body: { background: '#f4efe4', color: '#1a1a1a' }, a: { color: '#1a3f8a' } });
    rendition.themes.select(themeRef.current);
    rendition.display().catch((e: unknown) => setError(errorMessage(e)));
    return () => {
      book.destroy();
      renditionRef.current = null;
    };
  }, [url]);

  useEffect(() => { renditionRef.current?.themes.select(theme); }, [theme]);
  useEffect(() => { renditionRef.current?.themes.fontSize(`${size}%`); }, [size]);

  return (
    <div className="epub">
      <div className="row epub-controls no-print">
        <button type="button" className="btn" onClick={() => void renditionRef.current?.prev()}><Icon name="back" /><span>Previous</span></button>
        <button type="button" className="btn" onClick={() => void renditionRef.current?.next()}><span>Next</span><Icon name="forward" /></button>
        <button type="button" className="btn" onClick={() => setSize((s) => EPUB_SIZES[(EPUB_SIZES.indexOf(s) + 1) % EPUB_SIZES.length])}><Icon name="text-size" /><span>Text size {size}%</span></button>
      </div>
      {error && <p className="pad warning">Could not open this book: {error}</p>}
      <div ref={hostRef} className="epub-host" />
    </div>
  );
}

export function Doc() {
  const { id = '' } = useParams();
  const location = useLocation();
  const { theme } = useTheme();
  const { data: item, error, loading } = useQuery(() => api.libraryItem(id), [id]);
  return (
    <div className="screen screen-fill">
      <AppBar title={item?.title ?? 'Document'} />
      {loading && <p className="pad muted">Loading…</p>}
      {error && <p className="pad warning">Could not load this document: {error}</p>}
      {item && !item.available && <p className="pad warning">{item.title} is not available: {item.drive_label}.</p>}
      {item && item.available && item.url && item.kind === 'pdf' && <PdfFrame url={item.url} theme={theme} hash={location.hash} />}
      {item && item.available && item.url && item.kind === 'epub' && <EpubReader url={item.url} theme={theme} />}
      {item && item.available && item.kind !== 'pdf' && item.kind !== 'epub' && <p className="pad warning">{item.title} is not a PDF or EPUB.</p>}
    </div>
  );
}
