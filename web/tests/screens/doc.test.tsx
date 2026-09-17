import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, act, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { documentFileUrl, documentTitle, pdfViewerUrl } from '../../src/screens/Doc';
import { replaceFrameLocation } from '../../src/links';
import { READER_STYLE_ID } from '../../src/theme/readerTheme';
import { pdfItem, epubItem, extItem, wikiItem } from '../fixtures/api';

const mocks = vi.hoisted(() => {
  const handlers: Record<string, (loc: unknown) => void> = {};
  const rendition = {
    display: vi.fn(async () => undefined), next: vi.fn(), prev: vi.fn(),
    on: vi.fn((event: string, cb: (loc: unknown) => void) => { handlers[event] = cb; }),
    off: vi.fn((event: string) => { delete handlers[event]; }),
    themes: { register: vi.fn(), select: vi.fn(), fontSize: vi.fn() },
    hooks: { content: { register: vi.fn() } },
  };
  const book = { renderTo: vi.fn(() => rendition), destroy: vi.fn(), spine: { length: 4 } };
  return { rendition, book, handlers, ePub: vi.fn(() => book) };
});
vi.mock('epubjs', () => ({ default: mocks.ePub }));
vi.mock('../../src/links', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../../src/links')>();
  return { ...mod, replaceFrameLocation: vi.fn() };
});
const replaceMock = vi.mocked(replaceFrameLocation);

describe('pdfViewerUrl', () => {
  it('encodes the file URL, adds the theme and passes the page fragment through', () => {
    expect(pdfViewerUrl('/docs/core/nrr-2025.pdf', 'mono', '#page=12')).toBe('/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fnrr-2025.pdf&theme=mono#page=12');
    expect(pdfViewerUrl('/docs/core/nrr-2025.pdf', 'field', '')).toBe('/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fnrr-2025.pdf&theme=field');
  });
});

/** The reader is up once its bar is drawn *and* its mount effect has wired the rendition: under a loaded
 * test run the button can be found a tick before the effect runs, and a test that fires `relocated`
 * in that tick finds no handler. */
async function readerUp() {
  await screen.findByRole('button', { name: 'Next' });
  await waitFor(() => expect(typeof mocks.handlers.relocated).toBe('function'));
}

describe('Doc', () => {
  beforeEach(() => {
    // No saved place unless a test says otherwise: the reader opens at the start.
    vi.spyOn(api, 'getReading').mockResolvedValue(null);
    localStorage.clear();
    delete document.documentElement.dataset.reading;
  });

  it('reads every book in the box\'s own type: one serif at 18 px, ragged right, no page to itself for a chapter head', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    const rules = mocks.rendition.themes.register.mock.calls.at(-1)![1] as Record<string, Record<string, string>>;
    expect(rules.html['font-size']).toBe('18px');
    expect(rules.body['font-family']).toMatch(/Source Serif 4/);
    expect(rules.body['text-align']).toBe('left');
    expect(rules.body.hyphens).toBe('auto');
    expect(rules['h1, h2, h3']['page-break-before']).toBe('auto');
    // the face is loaded into the frame, which has none of the app's stylesheets
    const hook = mocks.rendition.hooks.content.register.mock.calls[0][0] as (c: { addStylesheet: (s: string) => Promise<void> }) => void;
    const addStylesheet = vi.fn(async () => undefined);
    hook({ addStylesheet });
    expect(addStylesheet).toHaveBeenCalledWith(expect.stringMatching(/\/fonts\/reader\.css$/));
  });

  it('puts the chrome away for the book and brings it back with a tap on the middle of the page', async () => {
    localStorage.setItem('sos.reader.flow', 'paginated');   // the taps on either side are page turns
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(document.documentElement.dataset.reading).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Just the book' }));
    expect(document.documentElement.dataset.reading).toBe('on');
    expect(localStorage.getItem('sos.reader.immersed')).toBe('on');
    // The page has the whole screen; a tap on its left turns back, on its right turns on, and in the
    // middle brings the controls back. The frame is 900 px wide here.
    const host = document.querySelector('.epub-host') as HTMLElement;
    Object.defineProperty(host, 'clientWidth', { value: 900, configurable: true });
    const tap = (x: number) => act(() => { mocks.handlers.click({ clientX: x, target: host } as unknown as MouseEvent); });
    tap(800);
    expect(mocks.rendition.next).toHaveBeenCalledTimes(1);
    tap(100);
    expect(mocks.rendition.prev).toHaveBeenCalledTimes(1);
    tap(450);
    expect(document.documentElement.dataset.reading).toBeUndefined();
    expect(localStorage.getItem('sos.reader.immersed')).toBe('off');
    // and the keys turn pages wherever the focus is
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(mocks.rendition.next).toHaveBeenCalledTimes(2);
  });

  it('opens with the chrome away when that is how you last read, and Escape brings it back', async () => {
    localStorage.setItem('sos.reader.immersed', 'on');
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(document.documentElement.dataset.reading).toBe('on');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(document.documentElement.dataset.reading).toBeUndefined();
  });

  it('scrolls by default, turns pages on request at the same place, and remembers the choice and the size', async () => {
    localStorage.setItem('sos.reader.size', '125');
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(mocks.rendition.themes.fontSize).toHaveBeenLastCalledWith('125%');   // the size you chose last time
    expect(mocks.book.renderTo).toHaveBeenLastCalledWith(expect.anything(), expect.objectContaining({ flow: 'scrolled', manager: 'continuous', spread: 'none' }));
    expect(screen.getByRole('button', { name: 'Scrolling' })).toHaveAttribute('aria-pressed', 'true');
    // scrolling, a tap on the right of the page is not a page turn: there are none
    const host = document.querySelector('.epub-host') as HTMLElement;
    Object.defineProperty(host, 'clientWidth', { value: 900, configurable: true });
    act(() => { mocks.handlers.click({ clientX: 800, target: host } as unknown as MouseEvent); });
    expect(mocks.rendition.next).not.toHaveBeenCalled();
    expect(document.documentElement.dataset.reading).toBe('on');
    mocks.handlers.relocated({ start: { index: 2, cfi: 'epubcfi(/6/12)', displayed: { page: 1, total: 4 } }, end: {}, atStart: false, atEnd: false });
    mocks.rendition.display.mockClear();
    act(() => { mocks.handlers.click({ clientX: 450, target: host } as unknown as MouseEvent); });   // the controls back
    await user.click(screen.getByRole('button', { name: 'Scrolling' }));
    expect(mocks.book.destroy).toHaveBeenCalled();
    expect(mocks.book.renderTo).toHaveBeenLastCalledWith(expect.anything(), expect.objectContaining({ flow: 'paginated', spread: 'none' }));
    expect(mocks.rendition.display).toHaveBeenCalledWith('epubcfi(/6/12)');
    expect(screen.getByRole('button', { name: 'Pages' })).toHaveAttribute('aria-pressed', 'false');
    expect(localStorage.getItem('sos.reader.flow')).toBe('paginated');
  });

  it('opens a Library EPUB where it was left and saves the position once per pause', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    vi.spyOn(api, 'getReading').mockResolvedValue({
      key: 'doc:where-there-is-no-doctor', title: epubItem.title, author: null, cover_url: null, url: '/doc/where-there-is-no-doctor',
      cfi: 'epubcfi(/6/8!/4/2)', percent: 30, updated_at: '2026-09-17T10:00:00Z',
    });
    const put = vi.spyOn(api, 'putReading').mockResolvedValue({ ok: true });
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(mocks.rendition.display).toHaveBeenCalledWith('epubcfi(/6/8!/4/2)');
    // Real timers until the reader is up (findByRole polls with them); fake ones only for the debounce.
    vi.useFakeTimers();
    try {
      const loc = (index: number, page: number) => ({ start: { index, cfi: `epubcfi(/6/${index})`, displayed: { page, total: 10 } }, end: {}, atStart: false, atEnd: false });
      mocks.handlers.relocated(loc(1, 1));
      mocks.handlers.relocated(loc(1, 6));
      expect(put).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(2000);
      expect(put).toHaveBeenCalledTimes(1);
      expect(put).toHaveBeenCalledWith('doc:where-there-is-no-doctor', { title: epubItem.title, author: null, cover_url: null, cfi: 'epubcfi(/6/1)', percent: 37.5 });
    } finally {
      vi.useRealTimers();
    }
  });

  it('saves the last page turn when the reader closes before the pause, and reopens there after the layout toggle', async () => {
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    const put = vi.spyOn(api, 'putReading').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    mocks.rendition.display.mockClear();
    mocks.handlers.relocated({ start: { index: 2, cfi: 'epubcfi(/6/12)', displayed: { page: 1, total: 4 } }, end: {}, atStart: false, atEnd: false });
    await user.click(screen.getByRole('button', { name: /Original PDF/ }));   // unmounts the EPUB reader at once
    await waitFor(() => expect(put).toHaveBeenCalledTimes(1));
    expect(put).toHaveBeenCalledWith('doc:where-there-is-no-doctor', expect.objectContaining({ cfi: 'epubcfi(/6/12)', percent: 50 }));
    await user.click(screen.getByRole('button', { name: /Reflowed text/ }));
    await readerUp();
    expect(mocks.rendition.display).toHaveBeenCalledWith('epubcfi(/6/12)');
  });

  it('places the book again once the frame\'s face has arrived, so the place is the one you left', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    vi.spyOn(api, 'getReading').mockResolvedValue({
      key: 'doc:where-there-is-no-doctor', title: epubItem.title, author: null, cover_url: null, url: null,
      cfi: 'epubcfi(/6/8!/4/2)', percent: 30, updated_at: '2026-09-17T10:00:00Z',
    });
    let fontsIn: () => void = () => undefined;
    const ready = new Promise<void>((resolve) => { fontsIn = resolve; });
    (mocks.book.renderTo as unknown as { mockImplementationOnce: (f: (host: HTMLElement) => typeof mocks.rendition) => void }).mockImplementationOnce((host) => {
      const frame = document.createElement('iframe');
      host.appendChild(frame);
      Object.defineProperty(frame.contentDocument, 'fonts', { value: { ready }, configurable: true });
      return mocks.rendition;
    });
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    await waitFor(() => expect(mocks.rendition.display).toHaveBeenCalledTimes(1));
    await act(async () => { fontsIn(); await ready; });
    await waitFor(() => expect(mocks.rendition.display).toHaveBeenCalledTimes(2));
    expect(mocks.rendition.display).toHaveBeenLastCalledWith('epubcfi(/6/8!/4/2)');
  });

  it('starts at the beginning when the saved place no longer resolves', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    vi.spyOn(api, 'getReading').mockResolvedValue({
      key: 'doc:where-there-is-no-doctor', title: epubItem.title, author: null, cover_url: null, url: null,
      cfi: 'epubcfi(/6/999)', percent: 30, updated_at: '2026-09-17T10:00:00Z',
    });
    mocks.rendition.display.mockRejectedValueOnce(new Error('No Section Found'));
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    await waitFor(() => expect(mocks.rendition.display).toHaveBeenCalledTimes(2));
    expect(mocks.rendition.display.mock.calls[1]).toEqual([]);   // the second display() asks for the start
    expect(screen.queryByText(/Could not open/)).not.toBeInTheDocument();
  });

  it('opens a PDF in the bundled viewer at the requested page and themes the viewer on load', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(pdfItem);
    renderRoute('/doc/nrr-2025#page=12');
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fnrr-2025.pdf&theme=field#page=12');
    await act(async () => { fireEvent.load(frame); });
    expect(frame.contentDocument!.getElementById(READER_STYLE_ID)?.textContent).toContain('#toolbarContainer');
    expect(screen.getByRole('heading', { name: 'National Risk Register 2025' })).toBeInTheDocument();
  });

  it('reloads the same iframe (not the wrong document) when navigating to a different PDF without unmounting the Doc route', async () => {
    const otherPdf = { ...pdfItem, id: 'other-pdf', title: 'Other PDF', url: '/doc/other-pdf', file_url: '/docs/core/other-pdf.pdf' };
    vi.spyOn(api, 'libraryItem').mockImplementation(async (id: string) => (id === otherPdf.id ? otherPdf : pdfItem));
    const { router } = renderRoute('/doc/nrr-2025');
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fnrr-2025.pdf&theme=field');
    expect(replaceMock).not.toHaveBeenCalled();

    await act(async () => { await router.navigate('/doc/other-pdf'); });
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Other PDF' })).toBeInTheDocument());

    // Same iframe instance (Doc route never unmounted) reused for the new document, via replaceFrameLocation
    // rather than a stale `src`.
    expect(screen.getByTitle('Document')).toBe(frame);
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fnrr-2025.pdf&theme=field');
    expect(replaceMock).toHaveBeenCalledTimes(1);
    expect(replaceMock).toHaveBeenCalledWith(frame.contentWindow, '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fother-pdf.pdf&theme=field');
  });

  it('opens an EPUB with epubjs, with next/previous and text size controls', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(mocks.ePub).toHaveBeenCalledWith('/docs/core/where-there-is-no-doctor.epub');
    expect(mocks.book.renderTo).toHaveBeenCalled();
    // The palette is the app's own tokens, rebuilt per theme and per dim state, not one of three
    // hard-coded sets living in the reader.
    expect(mocks.rendition.themes.register).toHaveBeenCalledWith('sos-field-lit', expect.objectContaining({ body: expect.anything() }));
    expect(mocks.rendition.themes.select).toHaveBeenCalledWith('sos-field-lit');
    await user.click(screen.getByRole('button', { name: 'Next' }));
    await user.click(screen.getByRole('button', { name: 'Previous' }));
    expect(mocks.rendition.next).toHaveBeenCalledTimes(1);
    expect(mocks.rendition.prev).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: /Text size/ }));
    expect(mocks.rendition.themes.fontSize).toHaveBeenLastCalledWith('125%');
  });

  it('wears the app\'s chrome, not the viewer\'s: page x of n, Previous, Next, Find and the size', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(pdfItem);
    renderRoute('/doc/nrr-2025');
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    await act(async () => { fireEvent.load(frame); });
    // PDF.js's own toolbar is hidden; nothing of the vendor's is on the screen
    const injected = frame.contentDocument!.getElementById(READER_STYLE_ID)!.textContent!;
    expect(injected).toContain('#toolbarContainer,#sidebarContainer');
    expect(injected).toContain('--toolbar-height:0px');
    expect(screen.queryByText('Automatic Zoom')).toBeNull();
    // and every control is an app button with a word on it
    for (const name of ['Previous', 'Next', 'Find', 'Text size']) {
      expect(screen.getByRole('button', { name: new RegExp(name) })).toBeInTheDocument();
    }
    expect(screen.getByRole('textbox', { name: 'Page number' })).toHaveValue('1');
    // Before the file has been read the count is not zero: it is not yet known, and the chrome says so.
    expect(screen.getByText(/Counting the pages…|of \d+/)).toBeInTheDocument();
    expect(screen.getByRole('searchbox', { name: 'Find in this document' })).toBeInTheDocument();
  });

  it('says the box does not have the document, and what to do, when the file is not on the drive', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(pdfItem);
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 404 }));
    renderRoute('/doc/nrr-2025');
    expect(await screen.findByText('The box does not have this document.')).toBeInTheDocument();
    expect(screen.queryByTitle('Document')).toBeNull();
    expect(screen.getByRole('link', { name: /Open the library entry/ })).toHaveAttribute('href', '/library/sources/uk-official#item-nrr-2025');
    expect(screen.getByRole('link', { name: /Search the box for this/ })).toHaveAttribute('href', '/search?q=National%20Risk%20Register%202025');
    // and the probe asked the drive for the file, never the app's own route, which the SPA answers
    // 200 for whatever you ask it
    expect(fetchMock).toHaveBeenCalledWith('/docs/core/nrr-2025.pdf', { method: 'HEAD' });
    fetchMock.mockRestore();
  });

  it('hands the viewer the file on the drive, never the app route', () => {
    expect(documentFileUrl(pdfItem)).toBe('/docs/core/nrr-2025.pdf');
    expect(documentFileUrl(epubItem)).toBe('/docs/core/where-there-is-no-doctor.epub');
    // a box built before the field, and an item the drive does not carry, are both "cannot open"
    expect(documentFileUrl({ ...pdfItem, file_url: null })).toBeNull();
    expect(documentFileUrl({ ...pdfItem, available: false })).toBeNull();
  });

  it('leaves the catalogue\u2019s edition parenthetical off the screen title', () => {
    expect(documentTitle('Where There Is No Doctor (Hesperian, 1992 revised edition)')).toBe('Where There Is No Doctor');
    expect(documentTitle('National Risk Register 2025')).toBe('National Risk Register 2025');
  });

  it('explains when the document is on a missing drive or is not a document', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValueOnce({ ...pdfItem, available: false, url: null, tier: 'extended', drive_label: 'On external drive (not connected)' });
    const a = renderRoute('/doc/nrr-2025');
    expect(await screen.findByText(/On external drive \(not connected\)/)).toBeInTheDocument();
    a.unmount();
    vi.spyOn(api, 'libraryItem').mockResolvedValueOnce(wikiItem);
    renderRoute('/doc/wikipedia_en_100_mini_2026-01');
    expect(await screen.findByText(/is not a PDF or EPUB/)).toBeInTheDocument();
    expect(extItem.available).toBe(false);
  });

  it('offers the original PDF layout for a converted book, and switches between the two viewers', async () => {
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(screen.queryByTitle('Document')).toBeNull();

    await user.click(screen.getByRole('button', { name: 'Original PDF' }));
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', expect.stringContaining('file=%2Fdocs%2Fcore%2Fwhere-there-is-no-doctor.pdf'));

    await user.click(screen.getByRole('button', { name: 'Reflowed text' }));
    expect(await screen.findByRole('button', { name: 'Next' })).toBeInTheDocument();
    expect(screen.queryByTitle('Document')).toBeNull();
  });

  it('opens a #page= citation into a converted book at that page of the original PDF', async () => {
    // The 805 `doc:<id>#page=N` citations in the playbooks were authored against the original PDF's
    // own page numbers; the reflowed EPUB has no such page, so the citation lands on the PDF.
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor#page=9');
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fwhere-there-is-no-doctor.pdf&theme=field#page=9');
    // and the reflowed text is still one press away
    await user.click(screen.getByRole('button', { name: 'Reflowed text' }));
    expect(await screen.findByRole('button', { name: 'Next' })).toBeInTheDocument();
    expect(screen.queryByTitle('Document')).toBeNull();
  });

  it('opens a converted book reflowed when nothing cites a page', async () => {
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    expect(screen.queryByTitle('Document')).toBeNull();
  });

  it('shows no original-layout toggle for a book that was never converted from a PDF', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    // even under a #page= citation: with no original beside it there is nothing to fall back to
    renderRoute('/doc/where-there-is-no-doctor#page=9');
    await readerUp();
    expect(screen.queryByRole('button', { name: /Original PDF/ })).toBeNull();
    expect(screen.queryByTitle('Document')).toBeNull();
  });

  it('puts the epub toolbar and the original-layout toggle in one compact bar, never stacked in a screen-body row', async () => {
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    renderRoute('/doc/where-there-is-no-doctor');
    await readerUp();
    const toggle = screen.getByRole('button', { name: 'Original PDF' });
    const previous = screen.getByRole('button', { name: 'Previous' });
    const next = screen.getByRole('button', { name: 'Next' });
    const textSize = screen.getByRole('button', { name: /Text size/ });
    const bar = toggle.closest('.doc-tools');
    expect(bar).not.toBeNull();
    expect(previous.closest('.doc-tools')).toBe(bar);
    expect(next.closest('.doc-tools')).toBe(bar);
    expect(textSize.closest('.doc-tools')).toBe(bar);
    // and nothing between the bar and the screen stacks these buttons into a column
    const screenEl = bar!.closest('.screen')!;
    expect(screenEl).not.toBeNull();
    let node: Element | null = bar;
    while (node && node !== screenEl) {
      expect(node.classList.contains('screen-body')).toBe(false);
      node = node.parentElement;
    }
  });

  it('moves the Reflowed text toggle into PdfFrame\'s own toolbar for the original PDF layout', async () => {
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    renderRoute('/doc/where-there-is-no-doctor#page=9');
    await screen.findByTitle('Document');
    const reflowed = screen.getByRole('button', { name: 'Reflowed text' });
    const previous = screen.getByRole('button', { name: 'Previous' });
    const bar = reflowed.closest('.doc-tools');
    expect(bar).not.toBeNull();
    expect(previous.closest('.doc-tools')).toBe(bar);
  });
});
