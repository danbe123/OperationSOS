import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import ePub, { type Rendition } from 'epubjs';
import { api } from '../api/client';
import type { LibraryItem } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { Icon } from '../icons';
import { replaceFrameLocation, sameOriginFrameUrl } from '../links';
import { injectStyle, pdfViewerCss, READER_STYLE_ID, viewerTokens } from '../theme/readerTheme';
import { useTheme, type Theme } from '../theme/ThemeProvider';

export function pdfViewerUrl(fileUrl: string, theme: Theme, hash: string): string {
  return `/pdfjs/web/viewer.html?file=${encodeURIComponent(fileUrl)}&theme=${theme}${hash}`;
}

/* The bits of PDF.js's own application object this screen drives. The viewer is bundled and served
 * from the same origin, so the frame's window is readable; every call is guarded because a viewer
 * that has not finished starting (or a jsdom test) has none of it. */
type PdfEvent = { pageNumber?: number; pagesCount?: number; scale?: number; matchesCount?: { current: number; total: number } };
type PdfBus = { on(name: string, cb: (e: PdfEvent) => void): void; off(name: string, cb: (e: PdfEvent) => void): void; dispatch(name: string, payload: Record<string, unknown>): void };
type PdfApp = {
  initializedPromise?: Promise<void>;
  pagesCount?: number;
  eventBus?: PdfBus;
  pdfViewer?: { currentPageNumber: number; currentScale: number };
};

const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

function appOf(frame: HTMLIFrameElement | null): PdfApp | null {
  try {
    return (frame?.contentWindow as unknown as { PDFViewerApplication?: PdfApp })?.PDFViewerApplication ?? null;
  } catch {
    return null;
  }
}

/** The document viewer's chrome, in the app's own components: where you are in the document, the way
 * forward and back, a page to jump to, a search of the text and the size of the page. PDF.js's own
 * toolbar is hidden (`pdfViewerCss`); this replaces it, at 48 px, with a word beside every icon. */
function PdfChrome({ frame, onMissing }: { frame: React.RefObject<HTMLIFrameElement | null>; onMissing: () => void }) {
  const [pages, setPages] = useState(0);
  const [page, setPage] = useState(1);
  const [typed, setTyped] = useState('');
  const [term, setTerm] = useState('');
  const [matches, setMatches] = useState<{ current: number; total: number } | null>(null);
  const [zoom, setZoom] = useState(1);

  const dispatch = useCallback((name: string, payload: Record<string, unknown> = {}) => {
    const app = appOf(frame.current);
    if (!app?.eventBus) return;
    try {
      app.eventBus.dispatch(name, { source: frame.current?.contentWindow, ...payload });
    } catch {
      // the viewer is still starting: the control simply does nothing this once
    }
  }, [frame]);

  // Wire the viewer's own event bus to this toolbar once the viewer has started.
  useEffect(() => {
    let live = true;
    const bus: { name: string; cb: (e: PdfEvent) => void }[] = [];
    const attach = async () => {
      const app = appOf(frame.current);
      if (!app) return;
      await app.initializedPromise?.catch(() => undefined);
      if (!live || !app.eventBus) return;
      const on = (name: string, cb: (e: PdfEvent) => void) => { app.eventBus!.on(name, cb); bus.push({ name, cb }); };
      on('pagesloaded', (e) => { setPages(e.pagesCount ?? app.pagesCount ?? 0); setPage(app.pdfViewer?.currentPageNumber ?? 1); });
      on('pagechanging', (e) => setPage(e.pageNumber ?? 1));
      on('scalechanging', (e) => setZoom(e.scale ?? 1));
      on('updatefindmatchescount', (e) => setMatches(e.matchesCount ?? null));
      on('updatefindcontrolstate', (e) => setMatches(e.matchesCount ?? null));
      on('documenterror', () => onMissing());
      setPages(app.pagesCount ?? 0);
    };
    const id = window.setTimeout(() => void attach(), 0);
    return () => {
      live = false;
      window.clearTimeout(id);
      const app = appOf(frame.current);
      for (const b of bus) { try { app?.eventBus?.off(b.name, b.cb); } catch { /* the frame is gone */ } }
      window.clearTimeout(id);
    };
  }, [frame, onMissing]);

  const goTo = (n: number) => {
    const app = appOf(frame.current);
    const wanted = Math.min(Math.max(1, n), pages || n);
    if (app?.pdfViewer) app.pdfViewer.currentPageNumber = wanted;
    setPage(wanted);
  };
  const setScale = (next: number) => {
    const app = appOf(frame.current);
    if (app?.pdfViewer) app.pdfViewer.currentScale = next;
    setZoom(next);
  };
  const step = (by: number) => {
    const near = ZOOMS.reduce((best, z) => (Math.abs(z - zoom) < Math.abs(best - zoom) ? z : best), ZOOMS[0]);
    setScale(ZOOMS[Math.min(ZOOMS.length - 1, Math.max(0, ZOOMS.indexOf(near) + by))]);
  };
  const find = (again: boolean) => {
    const query = again ? term : typed.trim();
    setTerm(query);
    if (!query) { setMatches(null); return; }
    dispatch('find', { type: again ? 'again' : '', query, caseSensitive: false, entireWord: false, highlightAll: true, findPrevious: false, matchDiacritics: false });
  };

  return (
    <div className="doc-tools no-print">
      <div className="row doc-tools-row" role="group" aria-label="Pages">
        <button type="button" className="btn btn-small" disabled={page <= 1} onClick={() => goTo(page - 1)}><Icon name="back" size={18} /><span>Previous</span></button>
        <label className="field doc-page">
          <span>Page</span>
          <input type="text" inputMode="numeric" aria-label="Page number" value={String(page)}
            onChange={(e) => { const n = Number(e.target.value.replace(/\D/g, '')); if (n > 0) goTo(n); }} />
        </label>
        <span className="muted doc-of">{pages > 0 ? `of ${pages}` : 'of an unknown number'}</span>
        <button type="button" className="btn btn-small" disabled={pages > 0 && page >= pages} onClick={() => goTo(page + 1)}><span>Next</span><Icon name="forward" size={18} /></button>
      </div>
      <form className="row doc-tools-row" role="search" aria-label="Find in this document" onSubmit={(e) => { e.preventDefault(); find(false); }}>
        <label className="field doc-find">
          <span>Find in this document</span>
          <input type="search" aria-label="Find in this document" value={typed} placeholder="a word or a phrase" onChange={(e) => setTyped(e.target.value)} />
        </label>
        <button type="submit" className="btn btn-small"><Icon name="search" size={18} /><span>Find</span></button>
        {term && <button type="button" className="btn btn-small" onClick={() => find(true)}><Icon name="forward" size={18} /><span>Next match</span></button>}
        {term && <span className="muted" role="status">{matches && matches.total > 0 ? `${matches.current} of ${matches.total}` : 'No matches'}</span>}
      </form>
      <div className="row doc-tools-row" role="group" aria-label="Page size">
        <button type="button" className="btn btn-small" onClick={() => step(-1)}><Icon name="minus" size={18} /><span>Smaller</span></button>
        <span className="muted">{Math.round(zoom * 100)}%</span>
        <button type="button" className="btn btn-small" onClick={() => step(1)}><Icon name="plus" size={18} /><span>Bigger</span></button>
      </div>
    </div>
  );
}

export function PdfFrame({ url, theme, hash, onMissing }: { url: string; theme: Theme; hash: string; onMissing?: () => void }) {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [initialSrc] = useState(() => pdfViewerUrl(url, theme, hash));
  const themeRef = useRef(theme);
  themeRef.current = theme;
  const prevUrlRef = useRef(url);
  const missed = useCallback(() => onMissing?.(), [onMissing]);

  const apply = useCallback(() => {
    const doc = frameRef.current?.contentDocument;
    // The viewer's colours are the app's own tokens as they stand right now, so the theme *and* the
    // dim palette reach it without a second set of colours living in the viewer.
    if (doc) injectStyle(doc, READER_STYLE_ID, pdfViewerCss(themeRef.current, viewerTokens(document.documentElement, themeRef.current)));
  }, []);
  useEffect(() => { apply(); }, [theme, apply]);

  // `url` changed to a different document while this PdfFrame instance stayed mounted (e.g. /doc/A -> /doc/B
  // without an unmount): reload the same frame at the new document, matching the single-src-set navigation
  // model used by the /read/:id reader (iframe.src set once, later moves done via replaceFrameLocation).
  useEffect(() => {
    if (prevUrlRef.current === url) return;
    prevUrlRef.current = url;
    const win = frameRef.current?.contentWindow;
    if (win) replaceFrameLocation(win, pdfViewerUrl(url, themeRef.current, hash));
  }, [url, hash]);

  // A later #page= link to the same document: change the viewer's hash in place (PDF.js listens for hashchange).
  useEffect(() => {
    const win = frameRef.current?.contentWindow;
    if (!win || !hash) return;
    const current = sameOriginFrameUrl(win);
    if (current && current.hash !== hash) replaceFrameLocation(win, current.pathname + current.search + hash);
  }, [hash]);

  return (
    <>
      <PdfChrome frame={frameRef} onMissing={missed} />
      <div className="frame-wrap">
        <iframe ref={frameRef} title="Document" src={initialSrc} onLoad={apply} />
      </div>
    </>
  );
}

/** The state the box is in more often than any other: the library knows about this document and the
 * file is not on the drive. It used to be communicated by the numeral 0 in a vendor toolbar. */
function DocumentMissing({ item }: { item: LibraryItem }) {
  return (
    <Body>
      <section className="panel panel-warn" aria-label="Not on this box">
        <h2>The box does not have this document.</h2>
        <p>
          <strong>{item.title}</strong> is listed in the library{item.drive_label ? ` under ${item.drive_label}` : ''}, but the
          file is not on the drive. Nothing you can do on this screen will bring it back — the file is copied on when the box
          is built or updated.
        </p>
        <p className="muted">What to do next:</p>
        <p className="row">
          <Link className="btn" to="/library"><Icon name="book" size={18} /><span>Open the library entry</span></Link>
          <Link className="btn" to={`/search?q=${encodeURIComponent(item.title)}`}><Icon name="search" size={18} /><span>Search the box for this</span></Link>
        </p>
      </section>
    </Body>
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
      <div className="row epub-controls no-print screen-body">
        <button type="button" className="btn" onClick={() => void renditionRef.current?.prev()}><Icon name="back" /><span>Previous</span></button>
        <button type="button" className="btn" onClick={() => void renditionRef.current?.next()}><span>Next</span><Icon name="forward" /></button>
        <button type="button" className="btn" onClick={() => setSize((s) => EPUB_SIZES[(EPUB_SIZES.indexOf(s) + 1) % EPUB_SIZES.length])}><Icon name="text-size" /><span>Text size {size}%</span></button>
      </div>
      {error && <p className="screen-body warning">Could not open this book: {error}</p>}
      <div ref={hostRef} className="epub-host" />
    </div>
  );
}

export function Doc() {
  const { id = '' } = useParams();
  const location = useLocation();
  const { theme } = useTheme();
  const { data: item, error, loading } = useQuery(() => api.libraryItem(id), [id]);
  // The library can list a document the drive does not carry. Ask the drive before drawing a viewer
  // that would otherwise say "0 of 0" over a blank grey page.
  const [missing, setMissing] = useState(false);
  const url = item?.available ? item.url : null;
  useEffect(() => {
    setMissing(false);
    if (!url) return;
    let live = true;
    fetch(url, { method: 'HEAD' })
      .then((res) => { if (live && (res.status === 404 || res.status === 410)) setMissing(true); })
      .catch(() => undefined); // a probe that cannot be made proves nothing: draw the viewer
    return () => { live = false; };
  }, [url]);

  const gone = item && (missing || !item.available || !item.url);
  return (
    <Screen title={item?.title ?? 'Document'} fill={!gone} search={false}>
      {loading && <p className="screen-body muted">Loading…</p>}
      {error && <p className="screen-body warning">Could not load this document: {error}</p>}
      {gone && <DocumentMissing item={item} />}
      {item && !gone && item.url && item.kind === 'pdf' && <PdfFrame url={item.url} theme={theme} hash={location.hash} onMissing={() => setMissing(true)} />}
      {item && !gone && item.url && item.kind === 'epub' && <EpubReader url={item.url} theme={theme} />}
      {item && !gone && item.kind !== 'pdf' && item.kind !== 'epub' && <p className="screen-body warning">{item.title} is not a PDF or EPUB.</p>}
    </Screen>
  );
}
