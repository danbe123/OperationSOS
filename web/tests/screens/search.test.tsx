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
    // The engine's <b> marks render as bold text, never as the tags themselves.
    const snippet = (await screen.findByText(/is an inorganic compound/)).closest('.result-snippet') as HTMLElement;
    expect(snippet).toHaveTextContent('Water is an inorganic compound.');
    expect(within(snippet).getByText('Water').tagName).toBe('B');
    expect(screen.queryByText(/<b>/)).toBeNull();
    // A mirrored page's survey prompt and footer are not a snippet: the row prints without one.
    expect(screen.queryByText(/Help us improve our website/)).toBeNull();
    expect(spy).toHaveBeenCalledWith('water', { sources: undefined });
    // Every result is in the group of the source it came from, the box's own first, and the three
    // matches inside one authored page are one row.
    const items = screen.getAllByRole('listitem').filter((li) => li.closest('.results'));
    expect(items).toHaveLength(7);
    // "Playbook" is the box's word; a household reads "Guide" — a word before the title, not a pill above it.
    expect(within(items[0]).getByText('Guide')).toHaveClass('result-source');
    // the query's word is marked in a title
    expect(within(items[0]).getByRole('link').querySelector('.result-title mark')).toHaveTextContent('Water');
    // everything that is not the box's own is one list in the engine's order, the source a word before each title
    const library = screen.getByRole('region', { name: 'From the library' });
    expect(within(library).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual([
      '/read/wikipedia_en_100_mini_2026-01/A/Water', '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', '/read/nhs_uk/www.nhs.uk/conditions/anticoagulants/side-effects/',
      '/map?lat=50.88&lon=-1.03&z=13&label=Waterlooville', '/doc/nrr-2025#page=12',
    ]);
    expect(within(library).getByRole('link', { name: /National Risk Register 2025, page 12/ })).toHaveTextContent('UK official');
    expect(screen.queryByRole('region', { name: 'UK official' })).toBeNull();
    const wiki = within(library).getAllByRole('link')[0];
    await act(async () => { wiki.click(); });
    expect(router.state.location.pathname).toBe('/read/wikipedia_en_100_mini_2026-01/A/Water');
  });

  it('filter chips come from groups and add ?sources=', async () => {
    const spy = vi.spyOn(api, 'search').mockResolvedValue(search);
    const user = userEvent.setup();
    const { router } = renderRoute('/search?q=water');
    const chips = await screen.findByRole('group', { name: 'Filter by source' });
    // The chips count the very rows underneath them, the box's own group leads, and past one row
    // of them the rest wait behind one control rather than pushing the first result off the screen.
    expect(within(chips).getAllByRole('button').map((b) => b.textContent)).toEqual(['From this box 2', 'Wikipedia 1', 'NHS 2', 'Place 1', 'More (1)']);
    await user.click(within(chips).getByRole('button', { name: 'More (1)' }));
    expect(within(chips).getAllByRole('button').map((b) => b.textContent)).toEqual(['From this box 2', 'Wikipedia 1', 'NHS 2', 'Place 1', 'UK official 1', 'Fewer']);
    await user.click(within(chips).getByRole('button', { name: 'NHS 2' }));
    expect(router.state.location.search).toBe('?q=water&sources=nhs');
    expect(spy).toHaveBeenLastCalledWith('water', { sources: ['nhs'] });
    expect(within(chips).getByRole('button', { name: 'NHS 2' })).toHaveAttribute('aria-pressed', 'true');
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
