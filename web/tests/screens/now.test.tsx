import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { modules, playbooks, powerOffView, view } from '../fixtures/api';

describe('Now', () => {
  beforeEach(() => { vi.spyOn(api, 'modules').mockResolvedValue(modules); });

  it('puts a row of topic buttons under the tiles, in the guides\' order, each opening its guide', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    const row = await screen.findByRole('navigation', { name: 'Guides by topic' });
    const links = within(row).getAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['Water', 'Food', 'Power', 'Communications']);
    expect(links[2]).toHaveAttribute('href', '/m/power');
    expect(links[2].querySelector('svg.icon')).not.toBeNull();
    // The tiles come first: the row sits under them.
    const tiles = await screen.findByRole('navigation', { name: 'Scenarios' });
    expect(tiles.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('is the front door: the question and the situations, with no app bar of its own', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    // Nothing is wrong with the services, so the front door asks the household the one question the
    // box is for, and every answer is on the screen.
    expect(await screen.findByRole('heading', { level: 1, name: "What's the situation?" })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("What's the situation? · SOS"));
    // no Back on the front door
    expect(screen.queryByRole('button', { name: /Back/ })).toBeNull();
    // Nothing about a register, a cupboard, a score or the machine itself: the kit ticks are on
    // /kit, the drill on /situation, and how a phone joins the box on /system.
    expect(screen.queryByRole('region', { name: 'Start here' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'The box' })).toBeNull();
    expect(screen.queryByTestId('status-strip')).toBeNull();
    expect(screen.queryByRole('region', { name: 'Household and stock' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'How ready you are' })).toBeNull();
  });

  it('/now is the same screen as /', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/now');
    expect(await screen.findByRole('heading', { level: 1, name: "What's the situation?" })).toBeInTheDocument();
  });

  it('puts every situation on the front door, in order, each a tile into its guide', async () => {
    // The box hands them back in any order; the screen sorts them by the order it was given.
    vi.spyOn(api, 'playbooks').mockResolvedValue([...playbooks].reverse());
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    const grid = await screen.findByRole('navigation', { name: 'Scenarios' });
    const tiles = within(grid).getAllByRole('link');
    expect(tiles).toHaveLength(20);
    expect(tiles[0]).toHaveTextContent('Nuclear war');
    expect(tiles[0]).toHaveTextContent('A nuclear strike on the UK.');
    expect(tiles[0]).toHaveAttribute('href', '/s/nuclear-war');
    expect(tiles[0].querySelector('svg.icon')).not.toBeNull();
    expect(tiles[3]).toHaveAttribute('href', '/s/grid-collapse');
    expect(tiles[19]).toHaveTextContent('The long rebuild');
    expect(tiles[19]).toHaveAttribute('href', '/s/long-rebuild');
  });

  it('a tile opens the situation guide', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const user = userEvent.setup();
    const { router } = renderRoute('/');
    const grid = await screen.findByRole('navigation', { name: 'Scenarios' });
    await user.click(within(grid).getByRole('link', { name: /Pandemic/ }));
    expect(router.state.location.pathname).toBe('/s/pandemic');
  });

  it('says it is reading while the situations are on their way', async () => {
    vi.spyOn(api, 'playbooks').mockReturnValue(new Promise(() => {}));
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    expect(await screen.findByText('Reading…')).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Scenarios' })).toBeNull();
  });

  it('says so, with a way to try again, when the situations cannot be read', async () => {
    const playbooksQ = vi.spyOn(api, 'playbooks').mockRejectedValue(new Error('boom'));
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const user = userEvent.setup();
    renderRoute('/');
    expect(await screen.findByText(/The box cannot read the guides: boom/)).toBeInTheDocument();
    playbooksQ.mockResolvedValue(playbooks);
    await user.click(screen.getByRole('button', { name: /Try again/ }));
    const grid = await screen.findByRole('navigation', { name: 'Scenarios' });
    expect(within(grid).getAllByRole('link')).toHaveLength(20);
  });

  it('leads with what to do once something is off', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const now = await screen.findByRole('region', { name: 'Right now' });
    expect(await screen.findByRole('heading', { level: 1, name: 'Power off, mobile patchy' })).toBeInTheDocument();
    expect(within(now).getAllByRole('listitem')).toHaveLength(3);
    expect(within(now).getByRole('link', { name: /All of them/ })).toHaveAttribute('href', '/tasks');
    // The situation itself is the answer to the question, so the tiles that ask it stand down.
    expect(screen.queryByRole('navigation', { name: 'Scenarios' })).toBeNull();
    expect(await screen.findByRole('region', { name: 'Coming up' })).toHaveTextContent('Fridge food unsafe');
    expect(screen.getByRole('region', { name: 'The box thinks' })).toHaveTextContent('Mobile network — probably off');
    expect(screen.getByRole('region', { name: 'Read' })).toHaveTextContent('Right now');
  });

  it('says so, and still offers the situations, when the engine cannot be read', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockRejectedValue(new Error('boom'));
    renderRoute('/');
    expect(await screen.findByText(/The box cannot read the situation/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Try again/ })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeInTheDocument();
    // The guides do not need the engine, so the front door still answers the question.
    expect(within(await screen.findByRole('navigation', { name: 'Scenarios' })).getAllByRole('link')).toHaveLength(20);
  });
});
