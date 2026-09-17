import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { BookSummary } from '../../src/api/types';

const book = (id: number, title: string, author: string, shelf: string | null = 'PR'): BookSummary =>
  ({ id, title, author, shelf, shelf_name: shelf ? 'English literature' : null, popularity: 1, cover_url: null, epub_url: '/e', html_url: '/h' });

describe('Books', () => {
  beforeEach(() => {
    vi.spyOn(api, 'reading').mockResolvedValue([]);
  });

  it('shows My books first, newest first, and forgets a book on request', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: true });
    const reading = vi.spyOn(api, 'reading')
      .mockResolvedValueOnce([
        { key: 'gutenberg:2701', title: 'Moby-Dick', author: 'Herman Melville', cover_url: null, url: '/book/gutenberg/2701', cfi: 'x', percent: 40.4, updated_at: '2026-09-17T10:00:00Z' },
        { key: 'doc:where-there-is-no-doctor', title: 'Where There Is No Doctor', author: null, cover_url: null, url: '/doc/where-there-is-no-doctor', cfi: 'y', percent: 10, updated_at: '2026-09-17T09:00:00Z' },
      ])
      .mockResolvedValueOnce([]);
    const del = vi.spyOn(api, 'deleteReading').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/library/books');
    const shelf = await screen.findByRole('region', { name: 'My books' });
    const items = within(shelf).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Moby-Dick');
    expect(items[0]).toHaveTextContent('40% read');
    expect(within(items[0]).getByRole('link', { name: /Moby-Dick/ })).toHaveAttribute('href', '/book/gutenberg/2701');
    expect(within(items[1]).getByRole('link', { name: /Where There Is No Doctor/ })).toHaveAttribute('href', '/doc/where-there-is-no-doctor');
    await user.click(within(items[0]).getByRole('button', { name: 'Forget Moby-Dick' }));
    expect(del).toHaveBeenCalledWith('gutenberg:2701');
    await waitFor(() => expect(screen.queryByRole('region', { name: 'My books' })).not.toBeInTheDocument());
    expect(reading).toHaveBeenCalledTimes(2);
  });

  it('lists the popular books, then searches as you type, then filters by shelf', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([{ code: 'PR', name: 'English literature', count: 2 }, { code: 'Q', name: 'Science', count: 1 }]);
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen'), book(2701, 'Moby-Dick', 'Herman Melville')], total: 2, available: true })
      .mockResolvedValueOnce({ items: [book(1232, 'The Prince', 'Niccolo Machiavelli', 'J')], total: 1, available: true })
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen')], total: 1, available: true });
    const user = userEvent.setup();
    renderRoute('/library/books');
    await screen.findByText('Pride and Prejudice');
    expect(screen.getByRole('link', { name: /Pride and Prejudice/ })).toHaveAttribute('href', '/book/gutenberg/1342');
    expect(books).toHaveBeenCalledTimes(1);
    await user.type(screen.getByRole('searchbox', { name: 'Search the books' }), 'prince');
    await screen.findByText('The Prince');
    expect(books).toHaveBeenCalledTimes(2);   // one call for the whole word, not one per letter
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'prince', offset: 0 }));
    await user.clear(screen.getByRole('searchbox', { name: 'Search the books' }));
    await user.click(within(screen.getByRole('group', { name: 'Shelves' })).getByRole('button', { name: /English literature/ }));
    await waitFor(() => expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ shelf: 'PR' })));
  });

  it('pages with Show more', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    const first = Array.from({ length: 40 }, (_, i) => book(i + 1, `Book ${i + 1}`, 'A'));
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: first, total: 41, available: true })
      .mockResolvedValueOnce({ items: [book(41, 'Book 41', 'A')], total: 41, available: true });
    const user = userEvent.setup();
    renderRoute('/library/books');
    await screen.findByText('Book 40');
    expect(screen.getByText('41 books')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show more' }));
    await screen.findByText('Book 41');
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 40 }));
    expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument();
  });

  it('says the collection is not on the box yet', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    renderRoute('/library/books');
    await screen.findByText(/Project Gutenberg is not on this box yet/);
  });
});
