import { describe, it, expect, vi } from 'vitest';
import { screen, act, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { pdfViewerUrl } from '../../src/screens/Doc';
import { replaceFrameLocation } from '../../src/links';
import { READER_STYLE_ID } from '../../src/theme/readerTheme';
import { pdfItem, epubItem, extItem, wikiItem } from '../fixtures/api';

const mocks = vi.hoisted(() => {
  const rendition = { display: vi.fn(async () => undefined), next: vi.fn(), prev: vi.fn(), themes: { register: vi.fn(), select: vi.fn(), fontSize: vi.fn() } };
  const book = { renderTo: vi.fn(() => rendition), destroy: vi.fn() };
  return { rendition, book, ePub: vi.fn(() => book) };
});
vi.mock('epubjs', () => ({ default: mocks.ePub }));
vi.mock('../../src/links', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../../src/links')>();
  return { ...mod, replaceFrameLocation: vi.fn() };
});
const replaceMock = vi.mocked(replaceFrameLocation);

describe('pdfViewerUrl', () => {
  it('encodes the file URL, adds the theme and passes the page fragment through', () => {
    expect(pdfViewerUrl('/docs/core/docs/nrr-2025.pdf', 'blackout', '#page=12')).toBe('/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fdocs%2Fnrr-2025.pdf&theme=blackout#page=12');
    expect(pdfViewerUrl('/docs/core/docs/nrr-2025.pdf', 'vault', '')).toBe('/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fdocs%2Fnrr-2025.pdf&theme=vault');
  });
});

describe('Doc', () => {
  it('opens a PDF in the bundled viewer at the requested page and themes the viewer on load', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(pdfItem);
    renderRoute('/doc/nrr-2025#page=12');
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fdocs%2Fnrr-2025.pdf&theme=vault#page=12');
    await act(async () => { fireEvent.load(frame); });
    expect(frame.contentDocument!.getElementById(READER_STYLE_ID)?.textContent).toContain('#toolbarContainer');
    expect(screen.getByRole('heading', { name: 'National Risk Register 2025' })).toBeInTheDocument();
  });

  it('reloads the same iframe (not the wrong document) when navigating to a different PDF without unmounting the Doc route', async () => {
    const otherPdf = { ...pdfItem, id: 'other-pdf', title: 'Other PDF', url: '/docs/core/docs/other-pdf.pdf' };
    vi.spyOn(api, 'libraryItem').mockImplementation(async (id: string) => (id === otherPdf.id ? otherPdf : pdfItem));
    const { router } = renderRoute('/doc/nrr-2025');
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fdocs%2Fnrr-2025.pdf&theme=vault');
    expect(replaceMock).not.toHaveBeenCalled();

    await act(async () => { await router.navigate('/doc/other-pdf'); });
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Other PDF' })).toBeInTheDocument());

    // Same iframe instance (Doc route never unmounted) reused for the new document, via replaceFrameLocation
    // rather than a stale `src`.
    expect(screen.getByTitle('Document')).toBe(frame);
    expect(frame).toHaveAttribute('src', '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fdocs%2Fnrr-2025.pdf&theme=vault');
    expect(replaceMock).toHaveBeenCalledTimes(1);
    expect(replaceMock).toHaveBeenCalledWith(frame.contentWindow, '/pdfjs/web/viewer.html?file=%2Fdocs%2Fcore%2Fdocs%2Fother-pdf.pdf&theme=vault');
  });

  it('opens an EPUB with epubjs, with next/previous and text size controls', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await screen.findByRole('button', { name: 'Next' });
    expect(mocks.ePub).toHaveBeenCalledWith('/docs/core/docs/where-there-is-no-doctor.epub');
    expect(mocks.book.renderTo).toHaveBeenCalled();
    expect(mocks.rendition.themes.select).toHaveBeenCalledWith('vault');
    await user.click(screen.getByRole('button', { name: 'Next' }));
    await user.click(screen.getByRole('button', { name: 'Previous' }));
    expect(mocks.rendition.next).toHaveBeenCalledTimes(1);
    expect(mocks.rendition.prev).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: /Text size 100%/ }));
    expect(mocks.rendition.themes.fontSize).toHaveBeenLastCalledWith('125%');
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
});
