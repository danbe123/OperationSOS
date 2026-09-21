import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { library, search, status } from '../fixtures/api';
import { QUICK_FINDS } from '../../src/screens/Find';

describe('Find', () => {
  it('searches: the field first, the sources and the count on one row, the box\'s own guidance first', async () => {
    vi.spyOn(api, 'search').mockResolvedValue(search);
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/search?q=water');
    // No heading: the rail says Find, and the row is a row of results on the kiosk. The tab still says it.
    expect(await screen.findByRole('combobox', { name: 'Search' })).toHaveValue('water');
    expect(screen.queryByRole('heading', { level: 1 })).toBeNull();
    await waitFor(() => expect(document.title).toBe('Find · SOS'));
    // The box's own guidance comes first, under its own heading, and every other source follows in
    // a group of its own: one ranked list put a mirror of somebody's website above the guides.
    // Three matches inside one authored page are one row: the anchors are not different answers.
    const own = await screen.findByRole('region', { name: 'From this box' });
    expect(within(own).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getAllByRole('listitem').filter((li) => li.closest('.results'))).toHaveLength(7);
    // the source is a word before the title, on the same line, not a pill above it
    const first = within(own).getAllByRole('link')[0];
    expect(first.querySelector('.result-line .result-source')).not.toBeNull();
    expect(first.querySelector('.badge')).toBeNull();
    expect(screen.getByText('7 results')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Filter by source' })).toBeInTheDocument();
    // nothing that belongs to the Library is repeated here
    expect(screen.queryByRole('region', { name: 'Browse the library' })).toBeNull();
    expect(screen.queryByRole('navigation', { name: 'Quick finds' })).toBeNull();
  });

  it('before a search: the field, one-tap quick finds, one line of what it searches, and the Library\'s shelves', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 60366, available: true });
    renderRoute('/find');
    const quick = await screen.findByRole('navigation', { name: 'Quick finds' });
    expect(within(quick).getAllByRole('link').map((a) => a.textContent)).toEqual(QUICK_FINDS);
    expect(within(quick).getByRole('link', { name: 'Power cut' })).toHaveAttribute('href', '/search?q=Power%20cut');
    expect(screen.getByText(/A place name or a postcode opens the map/)).toBeInTheDocument();
    // the Library's four shelves, in the room under the field
    const shelves = screen.getByRole('navigation', { name: 'Shelves' });
    expect(within(shelves).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/library/medical', '/library/guides', '/library/books', '/library/sources']);
    expect(screen.queryByRole('heading', { level: 1 })).toBeNull();
  });

  it('carries the theme button beside the field where there is no rail to hold it, on a screen with no head', async () => {
    renderRoute('/find');
    const field = await screen.findByRole('combobox', { name: 'Search' });
    // the test environment is not wide: the rail's footer is not drawn, so the button is here, once, next to the field
    const theme = screen.getAllByRole('button', { name: /^Change the theme/ });
    expect(theme).toHaveLength(1);
    expect(field.closest('.find-top')).toBe(theme[0].closest('.find-top'));
  });

  it('offers the assistant under the results, only when it is ready', async () => {
    vi.spyOn(api, 'search').mockResolvedValue(search);
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, ai: { state: 'ready', model: 'qwen', message: null } });
    renderRoute('/search?q=water');
    const ask = await screen.findByRole('region', { name: 'Ask the assistant' });
    expect(within(ask).getByRole('link', { name: /Ask the assistant/ })).toHaveAttribute('href', '/ai?q=water');
  });

  it('keeps the assistant off the screen before a search, and when it is off', async () => {
    renderRoute('/find');
    await screen.findByRole('navigation', { name: 'Quick finds' });
    expect(screen.queryByRole('region', { name: 'Ask the assistant' })).toBeNull();
  });
});
