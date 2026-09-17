import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { library, pages } from '../fixtures/api';
import { TOOL_TILES } from '../../src/screens/Tools';

describe('Library hub', () => {
  beforeEach(() => {
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    vi.spyOn(api, 'library').mockResolvedValue(library);
  });

  it('is three shelves as tiles, each saying what is on it', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 60366, available: true });
    renderRoute('/library');
    const shelves = await screen.findByRole('navigation', { name: 'Shelves' });
    const links = within(shelves).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/library/guides', '/library/books', '/library/collections']);
    expect(await within(shelves).findByText(`${pages.length} pages and ${TOOL_TILES.length} tools, written for this box`)).toBeInTheDocument();
    expect(await within(shelves).findByText('60,366 books to read, Project Gutenberg')).toBeInTheDocument();
    expect(await within(shelves).findByText('8 items, 7 on this box')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Back' })).not.toBeInTheDocument();
  });

  it('greys the Books shelf when the collection is not on the box', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    renderRoute('/library');
    const shelves = await screen.findByRole('navigation', { name: 'Shelves' });
    expect(await within(shelves).findByText('Project Gutenberg is not on this box yet')).toBeInTheDocument();
    expect(within(shelves).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/library/guides', '/library/collections']);
  });

  it('sends the old Guides address to its shelf', async () => {
    const { router } = renderRoute('/guides');
    expect(await screen.findByRole('searchbox', { name: 'Filter these guides' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/library/guides');
  });

  it('sends the old Books address to its shelf', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    vi.spyOn(api, 'reading').mockResolvedValue([]);
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    const { router } = renderRoute('/books');
    await screen.findByText(/Project Gutenberg is not on this box yet/);
    expect(router.state.location.pathname).toBe('/library/books');
  });
});

describe('Collections', () => {
  it('lists categories with counts, item cards, and filters by category chip', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const user = userEvent.setup();
    renderRoute('/library/collections');
    expect(await screen.findByText('8 items, 7 available on this box.')).toBeInTheDocument();
    const chips = screen.getByRole('group', { name: 'Categories' });
    expect(within(chips).getAllByRole('button').map((b) => b.textContent)).toEqual(['Medical (3)', 'UK official (1)', 'Practical (1)', 'Reference (1)', 'Maps (1)', 'Books (1)']);
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(6);
    expect(within(screen.getByRole('list', { name: 'Books' })).getByText('On external drive (not connected)')).toBeInTheDocument();
    await user.click(within(chips).getByRole('button', { name: 'Reference (1)' }));
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Open' })).toHaveAttribute('href', '/read/wikipedia_en_100_mini_2026-01/A/Main_Page');
    await user.click(within(chips).getByRole('button', { name: 'Reference (1)' }));
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(6);
  });

  it('scrolls to the item named in the hash', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const scroll = vi.spyOn(Element.prototype, 'scrollIntoView');
    renderRoute('/library/collections#item-nrr-2025');
    await screen.findByText('National Risk Register 2025');
    expect(scroll).toHaveBeenCalled();
    expect((scroll.mock.instances[0] as unknown as Element).id).toBe('item-nrr-2025');
  });

  it('shows an error state', async () => {
    vi.spyOn(api, 'library').mockRejectedValue(new Error('db locked'));
    renderRoute('/library/collections');
    expect(await screen.findByText('Library unavailable: db locked')).toBeInTheDocument();
  });
});
