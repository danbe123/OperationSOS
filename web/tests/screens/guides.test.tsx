import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { pages, playbooks } from '../fixtures/api';

function mockGuides() {
  vi.spyOn(api, 'playbooks').mockResolvedValue([...playbooks].reverse());
  vi.spyOn(api, 'pages').mockResolvedValue(pages);
}

describe('Guides', () => {
  it('lists the twenty situations in order with their icons, then the pages and the tools', async () => {
    mockGuides();
    renderRoute('/guides');
    const grid = await screen.findByRole('navigation', { name: 'Scenarios' });
    const tiles = within(grid).getAllByRole('link');
    expect(tiles).toHaveLength(20);
    expect(tiles[0]).toHaveTextContent('Nuclear war');
    expect(tiles[0]).toHaveAttribute('href', '/s/nuclear-war');
    expect(tiles[19]).toHaveTextContent('The long rebuild');
    expect(tiles[0].querySelector('svg.icon')).not.toBeNull();
    expect(screen.getByRole('navigation', { name: 'Phone and radio' })).toHaveTextContent('PMR446 radio');
    expect(within(screen.getByRole('navigation', { name: 'Tools' })).getAllByRole('link')).toHaveLength(6);
  });

  it('filters everything from one field, and offers the whole box when nothing matches', async () => {
    mockGuides();
    const user = userEvent.setup();
    renderRoute('/guides');
    await screen.findByRole('navigation', { name: 'Scenarios' });
    await user.type(screen.getByRole('searchbox', { name: 'Filter these guides' }), 'flood');
    expect(within(screen.getByRole('navigation', { name: 'Scenarios' })).getAllByRole('link')).toHaveLength(1);
    expect(screen.getByRole('status')).toHaveTextContent('2 guides match');
    // A section counts what it is showing, never what it would show with the filter off.
    expect(screen.getByRole('region', { name: 'Situations' })).toHaveTextContent('1 situation matches “flood”.');
    await user.clear(screen.getByRole('searchbox', { name: 'Filter these guides' }));
    await user.type(screen.getByRole('searchbox', { name: 'Filter these guides' }), 'zzzz');
    expect(screen.getByRole('link', { name: 'search the whole box' })).toHaveAttribute('href', '/search?q=zzzz');
  });

  it('narrows to one kind of guide from the chips', async () => {
    mockGuides();
    const user = userEvent.setup();
    renderRoute('/guides');
    await screen.findByRole('navigation', { name: 'Scenarios' });
    await user.click(screen.getByRole('button', { name: /^Tools/ }));
    expect(screen.queryByRole('navigation', { name: 'Scenarios' })).toBeNull();
    expect(screen.getByRole('navigation', { name: 'Tools' })).toBeInTheDocument();
  });

  it('shows an error line when the guides fail to load', async () => {
    vi.spyOn(api, 'playbooks').mockRejectedValue(new Error('boom'));
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    renderRoute('/guides');
    expect(await screen.findByText('Guides unavailable: boom')).toBeInTheDocument();
  });
});
