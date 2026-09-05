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
    const results = await screen.findByRole('list', { name: 'Results' });
    expect(within(results).getAllByRole('listitem')).toHaveLength(5);
    const lib = await screen.findByRole('region', { name: 'The library' });
    expect(lib).toHaveTextContent('7 items, 6 available on this box.');
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
    expect(await screen.findByRole('region', { name: 'The assistant' })).toBeInTheDocument();
  });
});
