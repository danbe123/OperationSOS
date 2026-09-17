import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { BookDetail } from '../../src/api/types';

const mocks = vi.hoisted(() => {
  const rendition = { display: vi.fn(async () => undefined), next: vi.fn(), prev: vi.fn(), on: vi.fn(), off: vi.fn(), themes: { register: vi.fn(), select: vi.fn(), fontSize: vi.fn() }, hooks: { content: { register: vi.fn() } } };
  const book = { renderTo: vi.fn(() => rendition), destroy: vi.fn(), spine: { length: 3 } };
  return { rendition, book, ePub: vi.fn(() => book) };
});
vi.mock('epubjs', () => ({ default: mocks.ePub }));

const pride: BookDetail = {
  id: 1342, title: 'Pride and Prejudice', author: 'Jane Austen', shelf: 'PR', shelf_name: 'English literature', popularity: 100,
  cover_url: '/kiwix/content/gutenberg_en_all/covers/1342_cover_image.jpg',
  epub_url: '/kiwix/content/gutenberg_en_all/Pride%20and%20Prejudice.1342.epub',
  html_url: '/read/gutenberg_en_all/Pride%20and%20Prejudice.1342.html',
  available: true, position: { cfi: 'epubcfi(/6/4!/4/2/2)', percent: 12.5 },
};

describe('Book', () => {
  beforeEach(() => {
    mocks.ePub.mockClear();
    mocks.rendition.display.mockClear();
  });

  it('opens the EPUB from the ZIM at the remembered place, with the author beside the controls', async () => {
    vi.spyOn(api, 'book').mockResolvedValue(pride);
    renderRoute('/book/gutenberg/1342');
    await screen.findByRole('button', { name: 'Next' });
    await waitFor(() => expect(mocks.ePub).toHaveBeenCalledWith(pride.epub_url));
    await waitFor(() => expect(mocks.rendition.display).toHaveBeenCalledWith('epubcfi(/6/4!/4/2/2)'));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Pride and Prejudice');
    expect(screen.getByText('Jane Austen')).toBeInTheDocument();
  });

  it('sends a book with no EPUB to the Kiwix reader page', async () => {
    vi.spyOn(api, 'book').mockResolvedValue({ ...pride, id: 11339, epub_url: null, html_url: '/read/gutenberg_en_all/Aesop.11339.html', position: null });
    const { router } = renderRoute('/book/gutenberg/11339');
    await waitFor(() => expect(router.state.location.pathname).toBe('/read/gutenberg_en_all/Aesop.11339.html'));
  });

  it('says so when the collection is not on the box', async () => {
    vi.spyOn(api, 'book').mockResolvedValue({ ...pride, available: false });
    renderRoute('/book/gutenberg/1342');
    await screen.findByText(/Project Gutenberg is not on this box/);
    expect(mocks.ePub).not.toHaveBeenCalled();
  });

  it('reports a book that is not in the catalogue', async () => {
    vi.spyOn(api, 'book').mockRejectedValue(new Error('Book not found'));
    renderRoute('/book/gutenberg/999');
    await screen.findByText(/Could not open this book: Book not found/);
  });
});
