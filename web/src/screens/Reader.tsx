import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { Screen } from '../shell/Screen';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { useKiosk } from '../kiosk/KioskProvider';
import { attachKeyboardTo } from '../kiosk/editable';
import { classifyHref, kiwixContentUrl, NOT_IN_LIBRARY, parseKiwixContentPath, readerRoute, replaceFrameLocation, sameOriginFrameUrl, unlinkExternal } from '../links';
import { DECLUTTER_CSS, DECLUTTER_STYLE_ID, injectStyle, isDim, READER_STYLE_ID, readerCss, TEXT_SIZE_STYLE_ID, textSizeCss, viewerTokens } from '../theme/readerTheme';
import { useTheme } from '../theme/ThemeProvider';
import { useRecordView } from '../reader/recent';
import { PdfFrame } from './Doc';
import { api } from '../api/client';

export const TEXT_SIZES = [100, 125, 150] as const;
export const TEXT_SIZE_KEY = 'sos.textSize';

function readStoredSize(): number {
  const n = Number(localStorage.getItem(TEXT_SIZE_KEY));
  return (TEXT_SIZES as readonly number[]).includes(n) ? n : 100;
}

/** Where "Open in library" goes: the item's own kind of source, scrolled to its card, once the
 * catalogue has said which kind that is; the Sources shelf until then or for an archive outside it. */
function useLibraryHref(id: string): string {
  const [category, setCategory] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    void api.libraryItem(id).then((item) => { if (active) setCategory(item.category); }).catch(() => undefined);
    return () => { active = false; };
  }, [id]);
  return category ? `/library/sources/${category}#item-${id}` : '/library/sources';
}

function frameBase(win: Window, fallbackPath: string): string {
  return sameOriginFrameUrl(win)?.href ?? new URL(fallbackPath, window.location.origin).href;
}

export function Reader() {
  const { id = '' } = useParams();
  const location = useLocation();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const libraryHref = useLibraryHref(id);
  useEffect(() => {
    let active = true;
    // Saved links may use a dated archive name from before the full library was installed.
    void api.libraryItem(id).then((item) => {
      if (active && item.id !== id) {
        const tail = location.pathname.slice(`/read/${id}`.length);
        navigate(`/read/${item.id}${tail}${location.search}${location.hash}`, { replace: true });
      }
    }).catch(() => { /* The reader can also open archives outside the managed catalogue. */ });
    return () => { active = false; };
  }, [id, location.pathname, location.search, location.hash, navigate]);
  const prefix = `/read/${id}/`;
  const path = location.pathname.startsWith(prefix) ? location.pathname.slice(prefix.length) : '';
  if (/\.pdf$/i.test(path)) {
    let title = path.split('/').pop() ?? 'PDF';
    try { title = decodeURIComponent(title); } catch { /* Keep malformed names readable. */ }
    return <Screen title={title} search={false} fill actions={<Link className="btn btn-small" to={libraryHref}><Icon name="library" size={18} /><span>Open in library</span></Link>}>
      <PdfFrame url={kiwixContentUrl(id, path) + location.search} theme={theme} hash={location.hash} />
    </Screen>;
  }
  return <ArticleReader key={id} />;
}

function ArticleReader() {
  const { id = '' } = useParams();
  const libraryHref = useLibraryHref(id);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const kiosk = useKiosk();

  // Read the raw pathname so percent-encoding in article paths survives (useParams decodes the splat).
  const prefix = `/read/${id}/`;
  const path = location.pathname.startsWith(prefix) ? location.pathname.slice(prefix.length) : '';
  const target = kiwixContentUrl(id, path) + location.search + location.hash;

  const frameRef = useRef<HTMLIFrameElement>(null);
  const [initialSrc] = useState(target); // set once: browser history holds one entry per article via the app URL
  const pending = useRef<string | null>(target);
  const targetRef = useRef(target);
  targetRef.current = target;
  const [title, setTitle] = useState('Reader');
  // Once the article has said its name: the key is the article's own path, so each article is one entry.
  // Kiwix's own "Page not found" is a page with a title too, and it is not something anyone opened.
  useRecordView(title !== 'Reader' && path && !/not found/i.test(title) ? { key: `article:${id}/${path}`, kind: 'article', title, url: location.pathname } : null);
  const [textSize, setTextSize] = useState<number>(readStoredSize);
  const themeRef = useRef(theme);
  themeRef.current = theme;
  const sizeRef = useRef(textSize);
  sizeRef.current = textSize;

  const applyStyles = useCallback(() => {
    const doc = frameRef.current?.contentDocument;
    // documentElement is briefly null while the frame is mid-navigation (jsdom; harmless no-op elsewhere).
    if (!doc || !doc.documentElement) return;
    const root = document.documentElement;
    injectStyle(doc, READER_STYLE_ID, readerCss(themeRef.current, viewerTokens(root, themeRef.current), isDim(root)));
    injectStyle(doc, TEXT_SIZE_STYLE_ID, textSizeCss(sizeRef.current));
    injectStyle(doc, DECLUTTER_STYLE_ID, DECLUTTER_CSS);
  }, []);

  useEffect(() => { applyStyles(); }, [theme, textSize, applyStyles]);
  useEffect(() => { localStorage.setItem(TEXT_SIZE_KEY, String(textSize)); }, [textSize]);

  // The app URL changed without an in-frame click (Back, Forward, a search result): move the frame to match.
  useEffect(() => {
    const win = frameRef.current?.contentWindow;
    if (!win) return;
    if (pending.current === target) return;
    const url = sameOriginFrameUrl(win);
    const current = url ? url.pathname + url.search + url.hash : '';
    if (current !== target) {
      pending.current = target;
      try {
        replaceFrameLocation(win, target);
      } catch {
        // A protected native viewer can reject Location access; navigate via the iframe element.
        if (frameRef.current) frameRef.current.src = target;
      }
    }
  }, [target]);

  const onFrameClick = useCallback(
    (e: Event) => {
      const win = frameRef.current?.contentWindow;
      if (!win) return;
      const t = e.target as { closest?: (selector: string) => Element | null } | null;
      const anchor = t?.closest?.('a[href]');
      if (!anchor) return;
      const href = anchor.getAttribute('href') ?? '';
      const base = frameBase(win, targetRef.current);
      const c = classifyHref(href, base);
      if (c.kind === 'external') {
        e.preventDefault();
        e.stopPropagation();
        notify(NOT_IN_LIBRARY);
        return;
      }
      if (c.kind === 'hash') {
        e.preventDefault();
        const u = new URL(href, base);
        replaceFrameLocation(win, u.pathname + u.search + u.hash);
        return;
      }
      if (c.kind === 'app') {
        e.preventDefault();
        e.stopPropagation();
        const u = new URL(href, base);
        const parsed = parseKiwixContentPath(u.pathname);
        if (parsed && !/\.pdf$/i.test(parsed.path)) {
          const next = kiwixContentUrl(parsed.id, parsed.path) + u.search + u.hash;
          pending.current = next;
          replaceFrameLocation(win, next);
        }
        navigate(c.to);
      }
      // 'other' (static files inside the frame): the browser handles it.
    },
    [navigate],
  );

  const locRef = useRef(location);
  locRef.current = location;
  const onLoad = useCallback(() => {
    const frame = frameRef.current;
    const doc = frame?.contentDocument;
    const win = frame?.contentWindow;
    if (!doc || !win) return;
    pending.current = null;
    applyStyles();
    // Links to the internet become plain text: nothing on this box can follow them. The click handler
    // below still catches any a page's own scripts add later.
    unlinkExternal(doc, frameBase(win, targetRef.current));
    doc.addEventListener('click', onFrameClick, true);
    win.open = () => null; // target=_blank and window.open never leave the app
    setTitle(doc.title || decodeURIComponent(targetRef.current.split('/').pop() ?? '') || 'Reader');
    if (kiosk) attachKeyboardTo(doc);
    // A form submit or redirect inside the frame: keep the app URL honest.
    const url = sameOriginFrameUrl(win);
    if (url) {
      const parsed = parseKiwixContentPath(url.pathname);
      if (parsed) {
        const route = readerRoute(parsed.id, parsed.path) + url.search + url.hash;
        const here = locRef.current.pathname + locRef.current.search + locRef.current.hash;
        if (route !== here) navigate(route, { replace: true });
      }
    }
  }, [applyStyles, onFrameClick, kiosk, navigate]);

  const cycleSize = () => setTextSize((s) => TEXT_SIZES[(TEXT_SIZES.indexOf(s as (typeof TEXT_SIZES)[number]) + 1) % TEXT_SIZES.length]);
  const print = () => frameRef.current?.contentWindow?.print();

  return (
    <Screen
      title={title}
      search={false}
      fill
      actions={
        <>
          {/* A verb and a word, not a reading: "Text size 100%" told a reader a number, not what
              pressing it would do. The percentage is in the accessible name. */}
          <button type="button" className="btn btn-small" onClick={cycleSize} aria-label={`Text size, ${textSize} per cent now`}><Icon name="text-size" size={18} /><span>Text size</span></button>
          <Link className="btn btn-small" to={libraryHref}><Icon name="library" size={18} /><span>Open in library</span></Link>
          {!kiosk && <button type="button" className="btn btn-small" onClick={print}><Icon name="print" size={18} /><span>Print</span></button>}
        </>
      }
    >
      <div className="frame-wrap">
        <iframe ref={frameRef} title="Article" src={initialSrc} sandbox="allow-same-origin allow-scripts allow-forms allow-modals" referrerPolicy="no-referrer" onLoad={onLoad} />
      </div>
    </Screen>
  );
}
