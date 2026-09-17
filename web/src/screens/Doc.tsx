import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import ePub, { EpubCFI, type Rendition } from 'epubjs';
import type { Location } from 'epubjs/types/rendition';
import { api } from '../api/client';
import type { LibraryItem, ReadingEntry } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { Icon } from '../icons';
import { notify } from '../components/Notice';
import { replaceFrameLocation, sameOriginFrameUrl } from '../links';
import { injectStyle, pdfViewerCss, READER_STYLE_ID, viewerTokens } from '../theme/readerTheme';
import { useTheme, type Theme } from '../theme/ThemeProvider';
import { readingPercent, SAVE_DELAY_MS, type EpubMemory } from '../reader/position';
import { fontFaceRules, fontsIn } from '../reader/fonts';
import { bookPieces } from '../reader/aloud';
import { pauseSpeaking, resumeSpeaking, speakFrom, stopSpeaking, useSpeech } from '../tools/speech';
import { setVoicePrefs, SPEEDS, voicePrefs } from '../tools/voice';
import { EPUB_SIZES, FLOW_KEY, IMMERSED_KEY, SIZE_KEY, storedFlow, storedImmersed, storedSize, tapZone, write, type Flow } from '../reader/prefs';

export function pdfViewerUrl(fileUrl: string, theme: Theme, hash: string): string {
  return `/pdfjs/web/viewer.html?file=${encodeURIComponent(fileUrl)}&theme=${theme}${hash}`;
}

/** The file on the drive, never the app's own route. `/api/library/<id>` names both: `url` is where
 * the app opens the document (`/doc/<id>`) and `file_url` is where the bytes are served
 * (`/docs/core/<file>`). Handing the viewer the route made pdf.js fetch `index.html`, which is not a
 * PDF, on every document in the library — and the HEAD probe beside it asked the same route, got
 * 200, and never raised the missing state. A box built before the field carries none, and the item
 * cannot be opened rather than being opened wrongly. */
export function documentFileUrl(item: Pick<LibraryItem, 'available' | 'file_url'> | null | undefined): string | null {
  if (!item?.available) return null;
  return item.file_url || null;
}

/** The screen's title for a document: the catalogue's edition parenthetical is cataloguing, not a
 * title — "Where There Is No Doctor (Hesperian, 1992 revised edition)" is one line of a 480 px
 * screen spent on a publisher's imprint. */
export function documentTitle(title: string): string {
  return (title ?? '').replace(/\s*\((?:[^()]*\b(?:edition|revised|revision|Hesperian|ed\.)\b[^()]*)\)\s*$/i, '').trim() || (title ?? '');
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

const ZOOMS = [0.75, 1, 1.25, 1.5, 2];

function appOf(frame: HTMLIFrameElement | null): PdfApp | null {
  try {
    return (frame?.contentWindow as unknown as { PDFViewerApplication?: PdfApp })?.PDFViewerApplication ?? null;
  } catch {
    return null;
  }
}

/** The document viewer's chrome, in the app's own components and on one row: where you are in the
 * document, the way forward and back, a page to jump to, a search of the text and the size of the
 * page. PDF.js's own toolbar is hidden (`pdfViewerCss`); this replaces it, at 48 px, with a word
 * beside every icon. Three rows of it used to cost a 480 px screen 150 pixels before the book. */
function PdfChrome({ frame, onMissing, leading }: { frame: React.RefObject<HTMLIFrameElement | null>; onMissing: () => void; leading?: ReactNode }) {
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
  const cycleZoom = () => {
    const at = ZOOMS.findIndex((z) => z > zoom + 0.01);
    const next = ZOOMS[at === -1 ? 0 : at];
    const app = appOf(frame.current);
    if (app?.pdfViewer) app.pdfViewer.currentScale = next;
    setZoom(next);
  };
  const find = (again: boolean) => {
    const query = again ? term : typed.trim();
    setTerm(query);
    if (!query) { setMatches(null); return; }
    dispatch('find', { type: again ? 'again' : '', query, caseSensitive: false, entireWord: false, highlightAll: true, findPrevious: false, matchDiacritics: false });
  };

  return (
    <div className="doc-tools no-print">
      {leading}
      <button type="button" className="btn btn-small" disabled={page <= 1} onClick={() => goTo(page - 1)}><Icon name="back" size={18} /><span>Previous</span></button>
      {/* "Page 4 of 210", with the number itself the thing you can change. Before the file has been
          read the count is not zero, it is not yet known, and the screen says so. */}
      <span className="doc-page">
        <span>Page</span>
        <input type="text" inputMode="numeric" aria-label="Page number" value={String(page)}
          onChange={(e) => { const n = Number(e.target.value.replace(/\D/g, '')); if (n > 0) goTo(n); }} />
        <span className="muted">{pages > 0 ? `of ${pages}` : 'Counting the pages…'}</span>
      </span>
      <button type="button" className="btn btn-small" disabled={pages > 0 && page >= pages} onClick={() => goTo(page + 1)}><span>Next</span><Icon name="forward" size={18} /></button>
      <form className="doc-find" role="search" aria-label="Find in this document" onSubmit={(e) => { e.preventDefault(); find(false); }}>
        <input type="search" aria-label="Find in this document" value={typed} placeholder="Find in this document" onChange={(e) => setTyped(e.target.value)} />
        <button type="submit" className="btn btn-small"><Icon name="search" size={18} /><span>Find</span></button>
        {term && <button type="button" className="btn btn-small" onClick={() => find(true)}><Icon name="forward" size={18} /><span>Next match</span></button>}
        {term && <span className="muted" role="status">{matches && matches.total > 0 ? `${matches.current} of ${matches.total}` : 'No matches'}</span>}
      </form>
      <button type="button" className="btn btn-small" onClick={cycleZoom} aria-label={`Text size, ${Math.round(zoom * 100)} per cent now`}>
        <Icon name="text-size" size={18} /><span>Text size</span>
      </button>
    </div>
  );
}

export function PdfFrame({ url, theme, hash, onMissing, leading }: { url: string; theme: Theme; hash: string; onMissing?: () => void; leading?: ReactNode }) {
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
      <PdfChrome frame={frameRef} onMissing={missed} leading={leading} />
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
          <strong>{documentTitle(item.title)}</strong> is listed in the library{item.drive_label ? ` under ${item.drive_label}` : ''}, but the
          file is not on the drive. Nothing you can do on this screen will bring it back — the file is copied on when the box
          is built or updated.
        </p>
        <p className="muted">What to do next:</p>
        <p className="row">
          <Link className="btn" to={`/library/sources/${item.category}#item-${item.id}`}><Icon name="book" size={18} /><span>Open the library entry</span></Link>
          <Link className="btn" to={`/search?q=${encodeURIComponent(documentTitle(item.title))}`}><Icon name="search" size={18} /><span>Search the box for this</span></Link>
        </p>
      </section>
    </Body>
  );
}

/** The EPUB's palette is the app's own tokens, read off the root exactly as the PDF viewer's is, so
 * a book follows the theme *and* the dim palette. It used to carry three hard-coded palettes of its
 * own — `#0a0f0a`, `#39ff7a`, `#1a3f8a`, `#ff7070` — none of which are in `tokens.css` and none of
 * which dimmed at three in the morning. */
export function epubTheme(tokens: { ground: string; panel: string; ink: string; line: string }, link: string, dark: boolean) {
  return {
    // The book's own typography is set aside for the box's: every book reads in one serif at 18 px
    // with the same leading, ragged right, hyphenated, whatever its file asked for (Gutenberg's files
    // ask for Times at 16 px with no space between paragraphs; some justify, which at this measure
    // opens rivers). The Text size button scales the body from this base.
    html: { 'font-size': '18px' },
    body: {
      background: tokens.ground, color: tokens.ink,
      'font-family': "'Source Serif 4', Georgia, 'Times New Roman', serif", 'line-height': '1.55',
      'text-align': 'left', hyphens: 'auto', '-webkit-hyphens': 'auto',
    },
    'p, li, blockquote, dd': { 'text-align': 'left', 'line-height': '1.55' },
    p: { margin: '0 0 0.75em', 'text-indent': '0' },
    a: { color: link },
    'h1, h2, h3, h4': { color: tokens.ink, 'font-family': "'Source Serif 4', Georgia, serif", 'line-height': '1.25', 'text-align': 'left' },
    // A chapter heading does not take a page of its own: with thirteen lines to a kiosk page, a
    // page holding one line is a page turned for nothing.
    'h1, h2, h3': { 'break-before': 'auto', 'page-break-before': 'auto', margin: '1.4em 0 0.6em' },
    'img, svg': { 'max-width': '100%', height: 'auto' },
    // Project Gutenberg puts a "(Larger)" link under every illustration, to a bigger copy of the same
    // picture. In a paginated reader it cannot open anything, and it lands on a page of its own after
    // the picture: a page that says "(Larger)" and nothing else.
    'a[title="linked image"]': { display: 'none' },
    figure: { 'break-inside': 'avoid' },
    ...(dark ? { img: { filter: 'brightness(.6)' } } : {}),
  };
}

const READING_ID = 'book';

/* The rendered views epub.js keeps while a book scrolls, as much of them as placing a CFI needs. */
type ScrolledView = { section?: { index?: number }; contents?: unknown; element: HTMLElement; locationOf: (cfi: string) => { top: number; left: number } };

/** Where a CFI sits in the scrolling container right now, in pixels from its top, or null while the
 * section holding it is not rendered. */
export function scrolledOffsetOf(rendition: Rendition, cfi: string): number | null {
  const manager = (rendition as unknown as { manager?: { views?: { all(): ScrolledView[] } } }).manager;
  const views = manager?.views?.all?.() ?? [];
  let spine: number;
  try {
    spine = new EpubCFI(cfi).spinePos;
  } catch {
    return null;
  }
  const view = views.find((v) => v.section?.index === spine && v.contents);
  if (!view) return null;
  try {
    return Math.max(0, Math.round(view.element.offsetTop + view.locationOf(cfi).top));
  } catch {
    return null;
  }
}

/** The EPUB reader. With `memory` it opens where the box last saw you and, as you turn pages, tells
 * the box where you are (one write per pause, never one per page). It turns pages or scrolls, as you
 * last chose; a tap on the left or right of a page turns it, a tap on the middle puts the chrome away
 * and brings it back; the text size is remembered from book to book. */
export function EpubReader({ url, theme, leading, memory, onPosition }: { url: string; theme: Theme; leading?: ReactNode; memory?: EpubMemory; onPosition?: (cfi: string) => void }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const [size, setSize] = useState(storedSize);
  const [flow, setFlow] = useState<Flow>(storedFlow);
  const [immersed, setImmersed] = useState(storedImmersed);
  const [error, setError] = useState<string | null>(null);
  const bookRef = useRef<ReturnType<typeof ePub> | null>(null);
  const { speaking, available: voice, paused } = useSpeech();
  const [voiceRow, setVoiceRow] = useState(false);
  const [prefs, setPrefs] = useState(voicePrefs);
  const voicesQ = useQuery(() => (voice && voiceRow ? api.voices() : Promise.resolve(null)), [voice, voiceRow]);
  const detachedRef = useRef(false);   // you scrolled while the voice read: the page stops following it
  const themeRef = useRef(theme);
  themeRef.current = theme;
  const memoryRef = useRef(memory);
  memoryRef.current = memory;
  const onPositionRef = useRef(onPosition);
  onPositionRef.current = onPosition;
  const flowRef = useRef(flow);
  flowRef.current = flow;
  // Where the reader is right now, so a change of flow reopens the same book at the same place.
  const hereRef = useRef<string | null>(null);
  // Where the voice has got to: each piece read is the place to come back to, whether or not the page followed.
  const noteRef = useRef<(cfi: string) => void>(() => undefined);

  useEffect(() => { write(SIZE_KEY, String(size)); }, [size]);
  useEffect(() => { write(FLOW_KEY, flow); }, [flow]);
  useEffect(() => {
    write(IMMERSED_KEY, immersed ? 'on' : 'off');
    const root = document.documentElement;
    if (immersed) root.dataset.reading = 'on'; else delete root.dataset.reading;
    return () => { delete root.dataset.reading; };
  }, [immersed]);
  // The keys work wherever the focus is: in the frame, epub.js relays them; outside it, the window does.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'PageDown') void renditionRef.current?.next();
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') void renditionRef.current?.prev();
      else if (e.key === 'Escape') setImmersed(false);
      else return;
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (!hostRef.current) return;
    const host = hostRef.current;
    const book = ePub(url);
    bookRef.current = book;
    // One page at a time: the two-page spread epub.js draws past 800 px read as the columns the reflow
    // had just undone, and the measure is capped by the host so a laptop is not a 1300 px line. Scrolled,
    // the chapters run on continuously, as a web page does.
    const rendition = flowRef.current === 'scrolled'
      ? book.renderTo(host, { width: '100%', height: '100%', flow: 'scrolled', manager: 'continuous', spread: 'none' })
      : book.renderTo(host, { width: '100%', height: '100%', flow: 'paginated', spread: 'none' });
    renditionRef.current = rendition;
    // The book face lives in the app, and the frame has none of the app's stylesheets.
    rendition.hooks.content.register((contents: { addStylesheetRules: (rules: object, key: string) => void }) => contents.addStylesheetRules(fontFaceRules(window.location.origin), 'sos-reader-fonts'));
    const onTap = (e: MouseEvent) => {
      const target = e.target as Element | null;
      if (target?.closest?.('a')) return;   // a link in the book is the book's
      // The frame is the whole book's width, columns side by side; the container scrolls it. The tap's
      // place on the screen is its place in the frame less that scroll.
      const container = host.querySelector<HTMLElement>('.epub-container');
      const width = container?.clientWidth || host.clientWidth;
      const zone = flowRef.current === 'scrolled' ? 'middle' : tapZone(e.clientX - (container?.scrollLeft ?? 0), width);
      if (zone === 'next') void rendition.next();
      else if (zone === 'previous') void rendition.prev();
      else setImmersed((v) => !v);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'PageDown') void rendition.next();
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') void rendition.prev();
      else if (e.key === 'Escape') setImmersed(false);
    };
    rendition.on('click', onTap);
    rendition.on('keydown', onKey);
    // epub.js lays the book out for the host's size once and listens to the window, not the host:
    // when the chrome goes away the host doubles in height and the page would stay the size it was,
    // with the taps below it landing on nothing.
    const watcher = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => { try { rendition.resize(host.clientWidth, host.clientHeight); } catch { /* not rendered yet */ } }) : null;
    watcher?.observe(host);
    const start = hereRef.current || memoryRef.current?.startCfi || undefined;
    let live = true;
    let moved = false;   // you have taken hold of the page: the placing above stops deferring to the remembered spot
    const onHand = () => { moved = true; detachedRef.current = true; };
    for (const ev of ['wheel', 'touchstart', 'mousedown', 'keydown'] as const) rendition.on(ev, onHand);
    host.addEventListener('wheel', onHand, { passive: true });
    host.addEventListener('touchstart', onHand, { passive: true });
    // A remembered place that no longer resolves (the file was rebuilt) is not an error: open at the start.
    const opening = start ? rendition.display(start).catch(() => rendition.display()) : rendition.display();
    opening
      .then(async () => {
        // The book is laid out before its face has arrived, in the fallback serif, which is wider; the
        // place is scrolled to in that layout, and when the face lands the text reflows some six per
        // cent shorter, so what is on the screen is that much further on than where you left — and
        // every reopening drifted by the same share. So: wait for the faces, then place the book again.
        if (!start) return;
        await fontsIn(host.querySelector('iframe')?.contentDocument);
        if (!live) return;
        if (flowRef.current !== 'scrolled') { await rendition.display(start).catch(() => undefined); return; }
        // Scrolling, the chapters before the place are loaded in above it as it settles, each in its
        // own frame with its own copy of the face to fetch, and epub.js's own correction for what they
        // add is off by whatever they grow by afterwards: a place near a chapter's start came back a
        // chapter early. The place is put right by hand instead: where the remembered text is now,
        // measured, is where the scroll goes, again whenever the layout moves, until it has been still
        // for a moment with every frame's faces in — and never once you have begun to scroll yourself.
        const deadline = Date.now() + 6000;
        let quietSince = Date.now();
        let seen = '';
        while (live && !moved && Date.now() < deadline) {
          await new Promise((r) => setTimeout(r, 120));
          const container = host.querySelector<HTMLElement>('.epub-container');
          if (!live || moved || !container) continue;
          const frames = Array.from(host.querySelectorAll('iframe'));
          const busy = frames.some((f) => f.contentDocument?.fonts?.status === 'loading');
          const at = scrolledOffsetOf(rendition, start);
          const sig = `${container.scrollHeight}|${frames.length}|${at}|${busy}`;
          if (at !== null && Math.abs(container.scrollTop - at) > 2) {
            container.scrollTop = at;
            quietSince = Date.now();
            continue;
          }
          if (sig !== seen || busy) { seen = sig; quietSince = Date.now(); continue; }
          if (Date.now() - quietSince > 700) break;
        }
      })
      .catch((e: unknown) => setError(errorMessage(e)));
    let timer: ReturnType<typeof setTimeout> | undefined;
    let pending: Location | null = null;
    const save = () => {
      const m = memoryRef.current;
      const loc = pending;
      pending = null;
      if (!m || !loc) return;
      void api.putReading(m.key, {
        title: m.title, author: m.author, cover_url: m.coverUrl,
        cfi: loc.start.cfi, percent: readingPercent(loc, (book.spine as { length?: number }).length),
      }).catch(() => undefined); // the page turned either way; a missed save costs nothing but the bookmark
    };
    const onRelocated = (loc: Location) => {
      hereRef.current = loc.start.cfi;
      onPositionRef.current?.(loc.start.cfi);
      if (!memoryRef.current) return;
      pending = loc;
      clearTimeout(timer);
      timer = setTimeout(save, SAVE_DELAY_MS);
    };
    noteRef.current = (cfi: string) => {
      let index = 0;
      try { index = Math.max(0, new EpubCFI(cfi).spinePos); } catch { /* a CFI the voice made is always well formed */ }
      onRelocated({ start: { cfi, index, displayed: { page: 1, total: 1 } }, end: { cfi, index }, atStart: false, atEnd: false } as unknown as Location);
    };
    rendition.on('relocated', onRelocated);
    return () => {
      live = false;
      clearTimeout(timer);
      save(); // a page turned in the last two seconds before Back is still the place to come back to
      rendition.off('relocated', onRelocated);
      rendition.off('click', onTap);
      rendition.off('keydown', onKey);
      for (const ev of ['wheel', 'touchstart', 'mousedown', 'keydown'] as const) rendition.off(ev, onHand);
      host.removeEventListener('wheel', onHand);
      host.removeEventListener('touchstart', onHand);
      watcher?.disconnect();
      if (speakingRef.current === READING_ID) stopSpeaking();   // the voice does not outlive the book on the screen
      book.destroy();
      bookRef.current = null;
      renditionRef.current = null;
    };
  }, [url, flow]);
  const speakingRef = useRef(speaking);
  speakingRef.current = speaking;

  /** Read the book aloud from where the screen is — or from chapter one, from the front matter — and keep
   * the screen with the voice until you scroll it yourself. */
  const readAloud = () => {
    detachedRef.current = false;
    const rendition = renditionRef.current;
    const book = bookRef.current;
    const host = hostRef.current;
    if (!rendition || !book || !host) return;
    const here = (rendition as unknown as { location?: { start?: { index?: number; cfi?: string } } }).location?.start;
    const start = { index: here?.index ?? 0, cfi: here?.cfi ?? hereRef.current };
    const locate = (doc: Document, cfi: string): Node | null => {
      try {
        return new EpubCFI(cfi).toRange(doc)?.startContainer ?? null;
      } catch {
        return null;
      }
    };
    const follow = (cfi: string) => {
      noteRef.current(cfi);   // the place to come back to, even when the page is not following
      if (detachedRef.current) return;
      if (flowRef.current === 'scrolled') {
        const container = host.querySelector<HTMLElement>('.epub-container');
        const at = scrolledOffsetOf(rendition, cfi);
        // the page keeps up with the voice: each piece's first paragraph comes to the top as it is read
        if (container && at !== null) { container.scrollTo({ top: at, behavior: 'smooth' }); return; }
      }
      void rendition.display(cfi).catch(() => undefined);
    };
    const pieces = bookPieces(book.spine as unknown as Parameters<typeof bookPieces>[0], book.load.bind(book), start, locate);
    const followed = (async function* () {
      for await (const piece of pieces) yield { text: piece.text, before: () => follow(piece.cfi) };
    })();
    void speakFrom(READING_ID, followed);
  };

  // One palette, rebuilt from the live tokens whenever the theme or the dim mode moves.
  useEffect(() => {
    const rendition = renditionRef.current;
    if (!rendition) return;
    const root = document.documentElement;
    const tokens = viewerTokens(root, theme);
    const link = getComputedStyle(root).getPropertyValue('--link').trim() || tokens.ink;
    const name = `sos-${theme}-${root.dataset.dim === 'on' ? 'dim' : 'lit'}`;
    rendition.themes.register(name, { ...epubTheme(tokens, link, theme !== 'field') } as Parameters<typeof rendition.themes.register>[1]);
    rendition.themes.select(name);
    rendition.themes.fontSize(`${size}%`);
  }, [theme, size, flow]);

  const choose = (next: Partial<typeof prefs>) => {
    setVoicePrefs(next);
    setPrefs(voicePrefs());
  };
  const reading = speaking === READING_ID;
  return (
    <div className="epub">
      <div className="doc-tools no-print">
        {leading}
        {/* Arrows alone, and only where there are pages to turn: the words made the bar two rows on the
            kiosk, and the same turns are a tap on either side of the page or an arrow key. */}
        {flow !== 'scrolled' && <button type="button" className="btn btn-small" onClick={() => void renditionRef.current?.prev()} aria-label="Previous" title="Previous page"><Icon name="back" size={20} /></button>}
        {flow !== 'scrolled' && <button type="button" className="btn btn-small" onClick={() => void renditionRef.current?.next()} aria-label="Next" title="Next page"><Icon name="forward" size={20} /></button>}
        <button type="button" className="btn btn-small" onClick={() => setSize((s) => EPUB_SIZES[(EPUB_SIZES.indexOf(s) + 1) % EPUB_SIZES.length])} aria-label={`Text size, ${size} per cent now`}>
          <Icon name="text-size" size={18} /><span>Text size</span>
        </button>
        <button type="button" className="btn btn-small" aria-pressed={flow === 'scrolled'} onClick={() => setFlow((f) => (f === 'scrolled' ? 'paginated' : 'scrolled'))}
                title={flow === 'scrolled' ? 'Turn pages instead of scrolling' : 'Scroll through the book instead of turning pages'}>
          <Icon name={flow === 'scrolled' ? 'down' : 'book'} size={18} /><span>{flow === 'scrolled' ? 'Scrolling' : 'Pages'}</span>
        </button>
        {voice && !reading && (
          <button type="button" className="btn btn-small" disabled={speaking !== null} onClick={readAloud} title="Read the book aloud from here; from the front, from chapter one">
            <Icon name="speaker" size={18} /><span>Read aloud</span>
          </button>
        )}
        {voice && reading && (paused
          ? <button type="button" className="btn btn-small btn-primary" onClick={() => { detachedRef.current = false; resumeSpeaking(); }}><Icon name="speaker" size={18} /><span>Resume</span></button>
          : <button type="button" className="btn btn-small" onClick={() => pauseSpeaking()}><Icon name="clock" size={18} /><span>Pause</span></button>)}
        {voice && reading && <button type="button" className="btn btn-small btn-danger" onClick={() => stopSpeaking()}><Icon name="close" size={18} /><span>Stop</span></button>}
        {voice && (
          <button type="button" className="btn btn-small" aria-expanded={voiceRow} onClick={() => setVoiceRow((v) => !v)} title="Which voice reads, and how fast">
            <Icon name="settings" size={18} /><span>Voice</span>
          </button>
        )}
        <button type="button" className="btn btn-small" onClick={() => { setImmersed(true); notify('Tap the middle of the page to bring the controls back.'); }}
                title="Put the controls away. Tap the middle of the page to bring them back.">
          <Icon name="expand" size={18} /><span>Just the book</span>
        </button>
      </div>
      {voice && voiceRow && (
        <div className="doc-tools voice-row no-print" role="group" aria-label="Voice">
          <label className="voice-pick">
            <span>Voice</span>
            <select aria-label="Which voice" value={prefs.voice} onChange={(e) => choose({ voice: e.target.value })}>
              <option value="">{voicesQ.data ? `${voicesQ.data.voices.find((v) => v.id === voicesQ.data!.default)?.name ?? 'The box’s own'} (default)` : 'The box’s own'}</option>
              {(voicesQ.data?.voices ?? []).filter((v) => v.id !== voicesQ.data?.default).map((v) => (
                <option key={v.id} value={v.id}>{v.name}{v.quality === 'high' ? ', high quality' : ''}</option>
              ))}
            </select>
          </label>
          <div className="row" role="group" aria-label="Speed">
            {SPEEDS.map((s) => (
              <button key={s.value} type="button" className={prefs.speed === s.value ? 'btn btn-small active' : 'btn btn-small'} aria-pressed={prefs.speed === s.value} onClick={() => choose({ speed: s.value })}>{s.label}</button>
            ))}
          </div>
          <Link className="btn btn-small btn-quiet" to="/library/sources/ai"><Icon name="plus" size={18} /><span>More voices</span></Link>
        </div>
      )}
      {error && <p className="screen-body warning">Could not open this book: {error}</p>}
      {/* The column grows with the type, so a line is the same sixty-odd characters at every text size:
          capped in the app's own units it stayed 608 px while the type went up by half, and the owner's
          lines fell to forty characters on an iPad Pro with a third of the screen empty either side. */}
      <div ref={hostRef} className="epub-host" style={{ maxWidth: `${(38 * size) / 100}em` }} />
    </div>
  );
}

export function Doc() {
  const { id = '' } = useParams();
  const location = useLocation();
  const { theme } = useTheme();
  const { data: item, error, loading } = useQuery(() => api.libraryItem(id), [id]);
  // The library can list a document the drive does not carry. Ask the drive — the file itself, not
  // the app route, which is served by the SPA and answers 200 for everything — before drawing a
  // viewer that would otherwise fail silently behind a vendor toolbar.
  const [missing, setMissing] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  // A playbook cites a document as `doc:<id>#page=N`, authored against the original PDF's own page
  // numbers. The reflowed EPUB has no such page: its own "pages" come from the spine, and mean
  // nothing to a `#page=` link. The original PDF beside it is the exact file the citation was written
  // against, so a cited link into a converted book opens that, at the cited page.
  useEffect(() => {
    setShowOriginal(Boolean(item?.pdf_fallback_url) && location.hash.startsWith('#page='));
  }, [id, item?.pdf_fallback_url, location.hash]);
  const file = useMemo(() => documentFileUrl(item), [item]);
  useEffect(() => {
    setMissing(false);
    if (!file) return;
    let live = true;
    fetch(file, { method: 'HEAD' })
      .then((res) => { if (live && !res.ok) setMissing(true); })
      .catch(() => undefined); // a probe that cannot be made proves nothing: draw the viewer
    return () => { live = false; };
  }, [file]);

  // The saved place is looked up before the reader mounts, keyed by item so a reader never opens on the
  // previous item's answer; a lookup that fails opens the book at the start rather than not at all.
  const memoryQ = useQuery<{ id: string; entry: ReadingEntry | null } | null>(
    () => (item && item.kind === 'epub'
      ? api.getReading(`doc:${item.id}`).then((entry) => ({ id: item.id, entry })).catch(() => ({ id: item.id, entry: null }))
      : Promise.resolve(null)),
    [item?.id, item?.kind],
  );
  const memoryReady = Boolean(item) && item!.kind === 'epub' && memoryQ.data?.id === item!.id;
  // Where the reader last was in this visit: the original/reflowed toggle remounts the reader, and it
  // must come back to the page you were on, not to the place the box remembered when the screen opened.
  const lastCfi = useRef<{ id: string; cfi: string } | null>(null);
  const memory: EpubMemory | undefined = memoryReady
    ? {
      key: `doc:${item!.id}`, title: item!.title, author: null, coverUrl: null,
      startCfi: (lastCfi.current?.id === item!.id ? lastCfi.current.cfi : null) ?? memoryQ.data?.entry?.cfi ?? null,
    }
    : undefined;
  const isDocument = item?.kind === 'pdf' || item?.kind === 'epub';
  const gone = Boolean(item) && isDocument && (missing || !item!.available || !file);
  const hasOriginal = item?.kind === 'epub' && Boolean(item.pdf_fallback_url);
  // The original/reflowed toggle is one button, owned here, and rendered as the leading button of
  // whichever `.doc-tools` bar is on screen — EpubReader's or PdfFrame's — never a row of its own.
  const originalToggle = hasOriginal ? (
    <button type="button" className="btn btn-small" onClick={() => setShowOriginal((v) => !v)}>
      <Icon name={showOriginal ? 'book' : 'pdf'} size={18} />
      <span>{showOriginal ? 'Reflowed text' : 'Original PDF'}</span>
    </button>
  ) : undefined;
  return (
    <Screen title={item ? documentTitle(item.title) : 'Document'} fill={Boolean(item) && isDocument && !gone} search={false}>
      {loading && <p className="screen-body muted">Loading…</p>}
      {error && <p className="screen-body warning">Could not load this document: {error}</p>}
      {item && gone && <DocumentMissing item={item} />}
      {item && !gone && file && item.kind === 'pdf' && <PdfFrame url={file} theme={theme} hash={location.hash} onMissing={() => setMissing(true)} />}
      {item && !gone && file && item.kind === 'epub' && !showOriginal && memoryReady && <EpubReader url={file} theme={theme} leading={originalToggle} memory={memory} onPosition={(cfi) => { lastCfi.current = { id: item.id, cfi }; }} />}
      {item && !gone && hasOriginal && showOriginal && <PdfFrame url={item!.pdf_fallback_url!} theme={theme} hash={location.hash} leading={originalToggle} />}
      {item && !isDocument && <p className="screen-body warning">{documentTitle(item.title)} is not a PDF or EPUB.</p>}
    </Screen>
  );
}
