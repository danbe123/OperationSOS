import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { library } from '../fixtures/api';

describe('Library', () => {
  it('lists categories with counts, item cards, and filters by category chip', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const user = userEvent.setup();
    renderRoute('/library');
    expect(await screen.findByText('7 items, 6 available')).toBeInTheDocument();
    const chips = screen.getByRole('group', { name: 'Categories' });
    expect(within(chips).getAllByRole('button').map((b) => b.textContent)).toEqual(['Medical (3)', 'UK official (1)', 'Reference (1)', 'Maps (1)', 'Books (1)']);
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(5);
    expect(within(screen.getByRole('list', { name: 'Books' })).getByText('On external drive (not connected)')).toBeInTheDocument();
    await user.click(within(chips).getByRole('button', { name: 'Reference (1)' }));
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Open' })).toHaveAttribute('href', '/read/wikipedia_en_100_mini_2026-01/A/Main_Page');
    await user.click(within(chips).getByRole('button', { name: 'Reference (1)' }));
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(5);
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
