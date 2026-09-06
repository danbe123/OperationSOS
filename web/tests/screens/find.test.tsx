import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { library, search, status } from '../fixtures/api';

describe('Find', () => {
  it('searches, and offers the library behind the results', async () => {
    vi.spyOn(api, 'search').mockResolvedValue(search);
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/search?q=water');
    expect(await screen.findByRole('heading', { level: 1, name: 'Find' })).toBeInTheDocument();
    // The box's own guidance comes first, under its own heading, and every other source follows in
    // a group of its own: one ranked list put a mirror of somebody's website above the guides.
    // Three matches inside one authored page are one row: the anchors are not different answers.
    const own = await screen.findByRole('region', { name: 'From this box' });
    expect(within(own).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getAllByRole('listitem').filter((li) => li.closest('.results'))).toHaveLength(7);
    const lib = await screen.findByRole('region', { name: 'Browse the library' });
    expect(lib).toHaveTextContent('8 items, 7 available on this box.');
    expect(within(lib).getByRole('link', { name: /Open the library/ })).toHaveAttribute('href', '/library');
  });

  it('/find is the same screen as /search', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/find');
    expect(await screen.findByRole('heading', { level: 1, name: 'Find' })).toBeInTheDocument();
    expect(screen.getByText(/Search Wikipedia, the NHS pages/)).toBeInTheDocument();
  });

  it('offers the assistant only when it is ready', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, ai: { state: 'ready', model: 'qwen', message: null } });
    renderRoute('/find');
    expect(await screen.findByRole('region', { name: 'Ask the assistant' })).toBeInTheDocument();
  });
});
