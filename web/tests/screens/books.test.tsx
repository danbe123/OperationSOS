import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { BookSummary } from '../../src/api/types';

const book = (id: number, title: string, author: string, shelf: string | null = 'PR'): BookSummary =>
  ({ id, title, author, shelf, shelf_name: shelf ? 'English literature' : null, popularity: 1, cover_url: null, epub_url: '/e', html_url: '/h' });

describe('Books', () => {
  it('lists the popular books, then searches as you type, then filters by shelf', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([{ code: 'PR', name: 'English literature', count: 2 }, { code: 'Q', name: 'Science', count: 1 }]);
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen'), book(2701, 'Moby-Dick', 'Herman Melville')], total: 2, available: true })
      .mockResolvedValueOnce({ items: [book(1232, 'The Prince', 'Niccolo Machiavelli', 'J')], total: 1, available: true })
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen')], total: 1, available: true });
    const user = userEvent.setup();
    renderRoute('/books');
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
    renderRoute('/books');
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
    renderRoute('/books');
    await screen.findByText(/Project Gutenberg is not on this box yet/);
  });
});
