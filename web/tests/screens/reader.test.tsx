import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, act, fireEvent } from '@testing-library/react';
import { renderRoute } from '../render';
import { replaceFrameLocation, NOT_IN_LIBRARY } from '../../src/links';
import { DECLUTTER_STYLE_ID, READER_STYLE_ID, TEXT_SIZE_STYLE_ID } from '../../src/theme/readerTheme';
import { WIKI } from '../fixtures/api';

vi.mock('../../src/links', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../../src/links')>();
  return { ...mod, replaceFrameLocation: vi.fn() };
});

const replaceMock = vi.mocked(replaceFrameLocation);
const MAIN = `/read/${WIKI}/A/Main_Page`;

function frame(): HTMLIFrameElement {
  return screen.getByTitle('Article') as HTMLIFrameElement;
}
/** The reader is one of the routes the shell fetches on demand, so the first look at any of its
 * screen waits for the chunk. */
async function reader(): Promise<HTMLIFrameElement> {
  return await screen.findByTitle('Article') as HTMLIFrameElement;
}
/** Simulate the frame having loaded an article: fill the about:blank document and fire `load`. */
async function loadArticle(title: string, html: string) {
  const doc = (await reader()).contentDocument!;
  doc.title = title;
  doc.body.innerHTML = html;
  await act(async () => { fireEvent.load(frame()); });
  return doc;
}
const ARTICLE = `
<h1>Main Page</h1>
<a id="in" href="/kiwix/content/${WIKI}/A/Water">Water</a>
<a id="rel" href="../A/Ice">Ice</a>
<a id="out" href="https://en.wikipedia.org/wiki/Water">Out</a>
<a id="catch" href="/kiwix/catch/external?source=https%3A%2F%2Fexample.org%2F">Catch</a>
<a id="frag" href="#History">History</a>
<input id="q" type="search">`;

beforeEach(() => replaceMock.mockReset());

describe('Reader', () => {
  it('opens encoded PDF links in PDF.js and returns to the article on Back', async () => {
    const { router } = renderRoute(MAIN);
    const pdfPath = 'files/First%20Aid%20and%20Medicine%20(1).pdf';
    const doc = await loadArticle('Main Page', `<a href="/kiwix/content/${WIKI}/${pdfPath}#page=2">Manual</a>`);
    await act(async () => { fireEvent.click(doc.querySelector('a')!); });
    const viewer = screen.getByTitle('Document');
    const src = new URL(viewer.getAttribute('src')!, window.location.origin);
    expect(src.pathname).toBe('/pdfjs/web/viewer.html');
    expect(src.searchParams.get('file')).toBe(`/kiwix/content/${WIKI}/${pdfPath}`);
    expect(src.hash).toBe('#page=2');
    expect(replaceMock).not.toHaveBeenCalled();
    await act(async () => { await router.navigate(-1); });
    expect(frame()).toHaveAttribute('src', `/kiwix/content/${WIKI}/A/Main_Page`);
  });

  it('recovers from a protected frame Location when navigating Back', async () => {
    const { router } = renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    await act(async () => { fireEvent.click(doc.getElementById('in')!); });
    await loadArticle('Water', '<h1>Water</h1>');
    Object.defineProperty(frame(), 'contentWindow', { configurable: true, value: {
      get location() { throw new DOMException('Blocked a cross-origin frame', 'SecurityError'); },
    } });
    replaceMock.mockImplementationOnce(() => { throw new DOMException('Blocked', 'SecurityError'); });
    await act(async () => { await router.navigate(-1); });
    expect(frame()).toHaveAttribute('src', `/kiwix/content/${WIKI}/A/Main_Page`);
    expect(screen.queryByText('Unexpected Application Error!')).toBeNull();
  });

  it('renders a sandboxed same-origin iframe whose src is set once', async () => {
    renderRoute(MAIN);
    const f = await reader();
    expect(f).toHaveAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms allow-modals');
    // An archived page must not tell anyone where it was read from.
    expect(f).toHaveAttribute('referrerpolicy', 'no-referrer');
    expect(f).toHaveAttribute('src', `/kiwix/content/${WIKI}/A/Main_Page`);
  });

  it('injects the theme and text-size styles on load and shows the article title', async () => {
    renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    // Field is the box default and leaves the ZIM's own light styling alone.
    expect(doc.getElementById(READER_STYLE_ID)?.textContent).toBe('');
    expect(doc.getElementById(TEXT_SIZE_STYLE_ID)?.textContent).toBe('html{font-size:100% !important}');
    // The archived site's cookie banner is furniture from a place that no longer exists here.
    expect(doc.getElementById(DECLUTTER_STYLE_ID)?.textContent).toContain('.govuk-cookie-banner');
    expect(screen.getByRole('heading', { name: 'Main Page' })).toBeInTheDocument();
    await act(async () => { screen.getByRole('button', { name: /Text size/ }).click(); });
    expect(doc.getElementById(TEXT_SIZE_STYLE_ID)?.textContent).toBe('html{font-size:125% !important}');
    expect(localStorage.getItem('sos.textSize')).toBe('125');
    // In mono the sheet is the app's own tokens, not a second palette: the black ground, and links
    // in the accent so a body link is a link.
    await act(async () => { screen.getByRole('button', { name: /Change the theme. Field now/ }).click(); });
    expect(doc.getElementById(READER_STYLE_ID)?.textContent).toContain('html,body{background:#000000');
    expect(doc.getElementById(READER_STYLE_ID)?.textContent).toContain('a,a *{color:#ffffff');
    expect(doc.getElementById(READER_STYLE_ID)?.textContent).toContain('text-decoration:underline');
  });

  it('turns content links into app navigation plus a location.replace in the frame, keeping src unchanged', async () => {
    const { router } = renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    await act(async () => { fireEvent.click(doc.getElementById('in')!); });
    expect(router.state.location.pathname).toBe(`/read/${WIKI}/A/Water`);
    expect(replaceMock).toHaveBeenCalledWith(frame().contentWindow, `/kiwix/content/${WIKI}/A/Water`);
    expect(frame()).toHaveAttribute('src', `/kiwix/content/${WIKI}/A/Main_Page`);
    await act(async () => { fireEvent.click(doc.getElementById('rel')!); });
    expect(router.state.location.pathname).toBe(`/read/${WIKI}/A/Ice`);
    expect(replaceMock).toHaveBeenLastCalledWith(frame().contentWindow, `/kiwix/content/${WIKI}/A/Ice`);
  });

  it('turns links to the internet and the external catcher into plain text on load', async () => {
    renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    expect(doc.getElementById('out')).toBeNull();
    expect(doc.getElementById('catch')).toBeNull();
    expect(doc.body.textContent).toContain('Out');
    expect(doc.body.textContent).toContain('Catch');
    expect(Array.from(doc.querySelectorAll('a')).map((a) => a.id)).toEqual(['in', 'rel', 'frag']);
  });

  it('shows the in-app notice for an external link a page script adds after load', async () => {
    const { router } = renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    const late = doc.createElement('a');
    late.id = 'late';
    late.href = 'https://example.org/late';
    late.textContent = 'Late';
    doc.body.appendChild(late);
    await act(async () => { fireEvent.click(late); });
    expect(screen.getByText(new RegExp(NOT_IN_LIBRARY.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(MAIN);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it('replaces fragments in place so they add no history entry', async () => {
    renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    await act(async () => { fireEvent.click(doc.getElementById('frag')!); });
    expect(replaceMock).toHaveBeenCalledWith(frame().contentWindow, `/kiwix/content/${WIKI}/A/Main_Page#History`);
  });

  it('Back moves the frame to the previous article', async () => {
    const { router } = renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    await act(async () => { fireEvent.click(doc.getElementById('in')!); });
    await loadArticle('Water', '<h1>Water</h1>');
    replaceMock.mockReset();
    await act(async () => { await router.navigate(-1); });
    expect(router.state.location.pathname).toBe(MAIN);
    expect(replaceMock).toHaveBeenCalledWith(frame().contentWindow, `/kiwix/content/${WIKI}/A/Main_Page`);
  });

  it('prints via the frame window, except in kiosk mode where the button is hidden', async () => {
    renderRoute(MAIN);
    await loadArticle('Main Page', ARTICLE);
    const win = frame().contentWindow!;
    expect(frame().getAttribute('sandbox')?.split(' ')).toContain('allow-modals');
    win.print = vi.fn();
    await act(async () => { screen.getByRole('button', { name: /Print/ }).click(); });
    expect(win.print).toHaveBeenCalled();
    screen.getByRole('link', { name: /Open in library/ });
  });

  // 20 seconds because this is the one test that waits for a lazily fetched chunk (the keyboard's),
  // and a loaded run transforms `simple-keyboard` and its stylesheet on the way.
  it('hides Print in kiosk mode and attaches the keyboard to the frame document', { timeout: 20_000 }, async () => {
    renderRoute(MAIN, { kiosk: true });
    const doc = await loadArticle('Main Page', ARTICLE);
    expect(screen.queryByRole('button', { name: /Print/ })).toBeNull();
    const input = doc.getElementById('q') as HTMLInputElement;
    await act(async () => { input.dispatchEvent(new (doc.defaultView!.FocusEvent)('focusin', { bubbles: true })); });
    // The pad itself is fetched by the first field anybody focuses, so the box never parses
    // `simple-keyboard` for a screen nobody types on.
    // Fetching the pad's own chunk is a disk read, and under a loaded test run it can outlast the
    // default timeout; the box shows it the moment it lands.
    expect(await screen.findByTestId('keyboard', {}, { timeout: 5_000 })).toBeInTheDocument();
  });
});
