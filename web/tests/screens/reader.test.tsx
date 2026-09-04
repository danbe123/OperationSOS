import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, act, fireEvent } from '@testing-library/react';
import { renderRoute } from '../render';
import { replaceFrameLocation, NOT_IN_LIBRARY } from '../../src/links';
import { READER_STYLE_ID, TEXT_SIZE_STYLE_ID } from '../../src/theme/readerTheme';
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
/** Simulate the frame having loaded an article: fill the about:blank document and fire `load`. */
async function loadArticle(title: string, html: string) {
  const doc = frame().contentDocument!;
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
  it('renders a sandboxed same-origin iframe whose src is set once', async () => {
    renderRoute(MAIN);
    const f = frame();
    expect(f).toHaveAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms');
    expect(f).toHaveAttribute('src', `/kiwix/content/${WIKI}/A/Main_Page`);
  });

  it('injects the theme and text-size styles on load and shows the article title', async () => {
    renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    expect(doc.getElementById(READER_STYLE_ID)?.textContent).toContain('#0a0f0a');
    expect(doc.getElementById(TEXT_SIZE_STYLE_ID)?.textContent).toBe('html{font-size:100% !important}');
    expect(screen.getByRole('heading', { name: 'Main Page' })).toBeInTheDocument();
    await act(async () => { screen.getByRole('button', { name: /Text size/ }).click(); });
    expect(doc.getElementById(TEXT_SIZE_STYLE_ID)?.textContent).toBe('html{font-size:125% !important}');
    expect(localStorage.getItem('sos.textSize')).toBe('125');
    await act(async () => { screen.getByRole('button', { name: /Theme: Vault/ }).click(); });
    expect(doc.getElementById(READER_STYLE_ID)?.textContent).toBe('');
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

  it('shows the in-app notice for external links and the external catcher', async () => {
    const { router } = renderRoute(MAIN);
    const doc = await loadArticle('Main Page', ARTICLE);
    await act(async () => { fireEvent.click(doc.getElementById('out')!); });
    expect(screen.getByText(new RegExp(NOT_IN_LIBRARY.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))).toBeInTheDocument();
    await act(async () => { fireEvent.click(doc.getElementById('catch')!); });
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
    win.print = vi.fn();
    await act(async () => { screen.getByRole('button', { name: /Print/ }).click(); });
    expect(win.print).toHaveBeenCalled();
    screen.getByRole('link', { name: /Open in library/ });
  });

  it('hides Print in kiosk mode and attaches the keyboard to the frame document', async () => {
    renderRoute(MAIN, { kiosk: true });
    const doc = await loadArticle('Main Page', ARTICLE);
    expect(screen.queryByRole('button', { name: /Print/ })).toBeNull();
    const input = doc.getElementById('q') as HTMLInputElement;
    await act(async () => { input.dispatchEvent(new (doc.defaultView!.FocusEvent)('focusin', { bubbles: true })); });
    expect(screen.getByTestId('keyboard')).toBeInTheDocument();
  });
});
