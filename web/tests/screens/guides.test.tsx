import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { pages } from '../fixtures/api';

function mockGuides() {
  vi.spyOn(api, 'pages').mockResolvedValue(pages);
}

describe('Guides', () => {
  it('lists the pages and the tools, and leaves the situations to the front door', async () => {
    mockGuides();
    renderRoute('/guides');
    const comms = await screen.findByRole('navigation', { name: 'Phone and radio' });
    expect(comms).toHaveTextContent('PMR446 radio');
    expect(comms.querySelector('svg.icon')).not.toBeNull();
    expect(within(screen.getByRole('navigation', { name: 'Tools' })).getAllByRole('link')).toHaveLength(6);
    // The twenty situations are the front door itself now: no tiles here, and no chip for them.
    expect(screen.queryByRole('navigation', { name: 'Scenarios' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'Situations' })).toBeNull();
    expect(screen.queryByRole('button', { name: /^Situations/ })).toBeNull();
    expect(screen.queryByRole('link', { name: /Nuclear war/ })).toBeNull();
  });

  it('filters everything from one field, and offers the whole box when nothing matches', async () => {
    mockGuides();
    const user = userEvent.setup();
    renderRoute('/guides');
    await screen.findByRole('navigation', { name: 'Phone and radio' });
    await user.type(screen.getByRole('searchbox', { name: 'Filter these guides' }), 'water');
    expect(within(screen.getByRole('navigation', { name: 'Field craft' })).getAllByRole('link')).toHaveLength(1);
    expect(screen.getByRole('status')).toHaveTextContent('3 guides match');
    // A section counts what it is showing, never what it would show with the filter off.
    expect(screen.getByRole('region', { name: 'Field craft' })).toHaveTextContent('1 page matches “water”.');
    await user.clear(screen.getByRole('searchbox', { name: 'Filter these guides' }));
    await user.type(screen.getByRole('searchbox', { name: 'Filter these guides' }), 'zzzz');
    expect(screen.getByRole('link', { name: 'search the whole box' })).toHaveAttribute('href', '/search?q=zzzz');
  });

  it('narrows to one kind of guide from the chips', async () => {
    mockGuides();
    const user = userEvent.setup();
    renderRoute('/guides');
    await screen.findByRole('navigation', { name: 'Phone and radio' });
    await user.click(screen.getByRole('button', { name: /^Tools/ }));
    expect(screen.queryByRole('navigation', { name: 'Phone and radio' })).toBeNull();
    expect(screen.getByRole('navigation', { name: 'Tools' })).toBeInTheDocument();
  });

  it('groups the rebuilding pages under their own heading', async () => {
    mockGuides();
    renderRoute('/guides');
    const rebuild = await screen.findByRole('navigation', { name: 'Rebuilding' });
    expect(within(rebuild).getByRole('link', { name: /The first year/ })).toHaveAttribute('href', '/p/rebuild-first-year');
    expect(screen.getByRole('region', { name: 'Rebuilding' })).toHaveTextContent('2 pages.');
  });

  it('keeps the household plan as a page in Reference', async () => {
    mockGuides();
    renderRoute('/guides');
    const reference = await screen.findByRole('navigation', { name: 'Reference' });
    // The plan is content now, not a screen with flags in it: it is read like any other page.
    expect(within(reference).getByRole('link', { name: /Household plan/ })).toHaveAttribute('href', '/p/household-plan');
  });

  it('shows an error line when the guides fail to load', async () => {
    vi.spyOn(api, 'pages').mockRejectedValue(new Error('boom'));
    renderRoute('/guides');
    expect(await screen.findByText('Pages unavailable: boom')).toBeInTheDocument();
  });
});
