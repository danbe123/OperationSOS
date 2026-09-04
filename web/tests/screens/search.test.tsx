import { describe, it, expect, vi } from 'vitest';
import { screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { search } from '../fixtures/api';

describe('Search screen', () => {
  it('searches ?q=, lists results with source badges and navigates on click', async () => {
    const spy = vi.spyOn(api, 'search').mockResolvedValue(search);
    const { router } = renderRoute('/search?q=water');
    expect(await screen.findByText('Water is an inorganic compound.')).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith('water', { sources: undefined });
    const list = screen.getByRole('list', { name: 'Results' });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(5);
    expect(within(items[0]).getByText('Playbook')).toHaveClass('badge');
    expect(within(items[4]).getByRole('link')).toHaveTextContent('National Risk Register 2025, page 12');
    await act(async () => { within(items[1]).getByRole('link').click(); });
    expect(router.state.location.pathname).toBe('/read/wikipedia_en_100_mini_2026-01/A/Water');
  });

  it('filter chips come from groups and add ?sources=', async () => {
    const spy = vi.spyOn(api, 'search').mockResolvedValue(search);
    const user = userEvent.setup();
    const { router } = renderRoute('/search?q=water');
    const chips = await screen.findByRole('group', { name: 'Filter by source' });
    expect(within(chips).getAllByRole('button').map((b) => b.textContent)).toEqual(['Playbook (1)', 'Wikipedia (1)', 'NHS (1)', 'Place (1)', 'UK official (1)']);
    await user.click(within(chips).getByRole('button', { name: 'NHS (1)' }));
    expect(router.state.location.search).toBe('?q=water&sources=nhs');
    expect(spy).toHaveBeenLastCalledWith('water', { sources: ['nhs'] });
    expect(within(chips).getByRole('button', { name: 'NHS (1)' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('shows the partial notice, the empty state and the error state', async () => {
    vi.spyOn(api, 'search').mockResolvedValueOnce({ ...search, partial: true });
    const first = renderRoute('/search?q=water');
    expect(await screen.findByText(/Some sources timed out/)).toBeInTheDocument();
    first.unmount();

    vi.spyOn(api, 'search').mockResolvedValueOnce({ ...search, q: 'zzz', query: 'zzz', results: [], groups: [] });
    const second = renderRoute('/search?q=zzz');
    expect(await screen.findByText(/Nothing found for “zzz”/)).toBeInTheDocument();
    second.unmount();

    vi.spyOn(api, 'search').mockRejectedValueOnce(new Error('kiwix down'));
    renderRoute('/search?q=water');
    expect(await screen.findByText('Search failed: kiwix down')).toBeInTheDocument();
  });

  it('does not search without a query', async () => {
    const spy = vi.spyOn(api, 'search').mockResolvedValue(search);
    renderRoute('/search');
    await act(async () => {});
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByRole('combobox', { name: 'Search' })).toHaveFocus();
  });
});
