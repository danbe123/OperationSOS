import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { BookSummary } from '../../src/api/types';

const book = (id: number, title: string, author: string, shelf: string | null = 'PR'): BookSummary =>
  ({ id, title, author, shelf, shelf_name: shelf ? 'English literature' : null, popularity: 1, cover_url: null, epub_url: '/e', html_url: '/h' });
const shelves = [{ code: 'PR', name: 'English literature', count: 9654 }, { code: 'Q', name: 'Science', count: 2291 }];

describe('Books', () => {
  beforeEach(() => {
    vi.spyOn(api, 'reading').mockResolvedValue([]);
  });

  it('puts the books you are reading first, newest first, as covers with how far you are, and forgets one on request', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: true });
    const reading = vi.spyOn(api, 'reading')
      .mockResolvedValueOnce([
        { key: 'gutenberg:2701', title: 'Moby-Dick', author: 'Herman Melville', cover_url: '/c.jpg', url: '/book/gutenberg/2701', cfi: 'x', percent: 40.4, updated_at: '2026-09-17T10:00:00Z' },
        { key: 'doc:where-there-is-no-doctor', title: 'Where There Is No Doctor', author: null, cover_url: null, url: '/doc/where-there-is-no-doctor', cfi: 'y', percent: 10, updated_at: '2026-09-17T09:00:00Z' },
      ])
      .mockResolvedValueOnce([]);
    const del = vi.spyOn(api, 'deleteReading').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/library/books');
    const strip = await screen.findByRole('list', { name: 'Continue reading' });
    const items = within(strip).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Moby-Dick');
    expect(items[0]).toHaveTextContent('40% read');
    expect(within(items[0]).getByRole('link', { name: /Moby-Dick/ })).toHaveAttribute('href', '/book/gutenberg/2701');
    expect(items[0].querySelector('img')).toHaveAttribute('src', '/c.jpg');
    // a guide without a cover gets a spine with its title on it, the same size, so the strip has no hole
    expect(within(items[1]).getByRole('link', { name: /Where There Is No Doctor/ })).toHaveAttribute('href', '/doc/where-there-is-no-doctor');
    expect(items[1].querySelector('.book-spine')).toHaveTextContent('Where There Is No Doctor');
    await user.click(within(items[0]).getByRole('button', { name: 'Forget Moby-Dick' }));
    expect(del).toHaveBeenCalledWith('gutenberg:2701');
    await waitFor(() => expect(screen.queryByRole('list', { name: 'Continue reading' })).not.toBeInTheDocument());
    expect(reading).toHaveBeenCalledTimes(2);
  });

  it('is a front: the shelves as tiles, the most-read books as covers, and one search', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue(shelves);
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen'), book(2701, 'Moby-Dick', 'Herman Melville')], total: 60366, available: true })
      .mockResolvedValueOnce({ items: [book(1232, 'The Prince', 'Niccolo Machiavelli', 'J')], total: 1, available: true });
    const user = userEvent.setup();
    const { router } = renderRoute('/library/books');
    const front = await screen.findByRole('list', { name: 'Most read' });
    expect(within(front).getByRole('link', { name: /Pride and Prejudice/ })).toHaveAttribute('href', '/book/gutenberg/1342');
    expect(books).toHaveBeenCalledTimes(1);
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 12, offset: 0 }));
    // the shelves are tiles that lead to the shelf, not chips that filter in place
    const tiles = screen.getByRole('navigation', { name: 'Shelves' });
    expect(within(tiles).getByRole('link', { name: /English literature/ })).toHaveAttribute('href', '/library/books?shelf=PR');
    expect(within(tiles).getByRole('link', { name: /English literature/ })).toHaveTextContent('9,654 books');
    expect(screen.getByRole('link', { name: /All 60,366 books/ })).toHaveAttribute('href', '/library/books?all=1');
    // the screen's own search is the only one: no "Search the box" above it
    expect(screen.queryByRole('link', { name: /Search the box/ })).toBeNull();
    await user.type(screen.getByRole('searchbox', { name: 'Search the books' }), 'prince');
    await screen.findByRole('link', { name: /The Prince/ });
    expect(books).toHaveBeenCalledTimes(2);   // one call for the whole word, not one per letter
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'prince', offset: 0, limit: 40 }));
    expect(router.state.location.search).toBe('?q=prince');
    expect(screen.getByText('1 book for “prince”')).toBeInTheDocument();
  });

  it('shows the front twelve shelves and the rest on request', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue(Array.from({ length: 39 }, (_, i) => ({ code: `S${i}`, name: `Shelf ${i + 1}`, count: 100 - i })));
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: true });
    const user = userEvent.setup();
    renderRoute('/library/books');
    const tiles = await screen.findByRole('navigation', { name: 'Shelves' });
    expect(within(tiles).getAllByRole('link')).toHaveLength(12);
    await user.click(screen.getByRole('button', { name: 'All 39 shelves' }));
    expect(within(tiles).getAllByRole('link')).toHaveLength(39);
  });

  it('a shelf is a grid of covers, most read first or A to Z, a page at a time', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue(shelves);
    const first = Array.from({ length: 40 }, (_, i) => book(i + 1, `Book ${i + 1}`, 'A'));
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: first, total: 41, available: true })
      .mockResolvedValueOnce({ items: [book(41, 'Book 41', 'A')], total: 41, available: true })
      .mockResolvedValueOnce({ items: [book(41, 'Book 41', 'A')], total: 41, available: true });
    const user = userEvent.setup();
    renderRoute('/library/books?shelf=PR');
    await screen.findByRole('link', { name: /Book 40/ });
    await waitFor(() => expect(document.title).toBe('English literature · SOS'));
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ shelf: 'PR', sort: 'popular', limit: 40, offset: 0 }));
    expect(screen.getByText('41 books')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back/ })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show more' }));
    await screen.findByRole('link', { name: /Book 41/ });
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 40 }));
    expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument();
    const order = screen.getByRole('group', { name: 'Order' });
    expect(within(order).getByRole('link', { name: 'Most read' })).toHaveAttribute('aria-current', 'page');
    await user.click(within(order).getByRole('link', { name: 'A to Z' }));
    await waitFor(() => expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ shelf: 'PR', sort: 'title', offset: 0 })));
  });

  it('says the collection is not on the box yet', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    renderRoute('/library/books');
    await screen.findByText(/Project Gutenberg is not on this box yet/);
  });
});
