import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { library } from '../fixtures/api';

describe('Library', () => {
  beforeEach(() => {
    vi.spyOn(api, 'reading').mockResolvedValue([]);
  });

  it('shows My books first, newest first, and forgets a book on request', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const reading = vi.spyOn(api, 'reading')
      .mockResolvedValueOnce([
        { key: 'gutenberg:2701', title: 'Moby-Dick', author: 'Herman Melville', cover_url: null, url: '/book/gutenberg/2701', cfi: 'x', percent: 40.4, updated_at: '2026-09-17T10:00:00Z' },
        { key: 'doc:where-there-is-no-doctor', title: 'Where There Is No Doctor', author: null, cover_url: null, url: '/doc/where-there-is-no-doctor', cfi: 'y', percent: 10, updated_at: '2026-09-17T09:00:00Z' },
      ])
      .mockResolvedValueOnce([]);
    const del = vi.spyOn(api, 'deleteReading').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/library');
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

  it('lists categories with counts, item cards, and filters by category chip', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const user = userEvent.setup();
    renderRoute('/library');
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
    renderRoute('/library#item-nrr-2025');
    await screen.findByText('National Risk Register 2025');
    expect(scroll).toHaveBeenCalled();
    expect((scroll.mock.instances[0] as unknown as Element).id).toBe('item-nrr-2025');
  });

  it('shows an error state', async () => {
    vi.spyOn(api, 'library').mockRejectedValue(new Error('db locked'));
    renderRoute('/library');
    expect(await screen.findByText('Library unavailable: db locked')).toBeInTheDocument();
  });
});
