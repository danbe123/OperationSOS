import { describe, it, expect, vi } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { condition, playbooks, powerOffView, view } from '../fixtures/api';

describe('Now', () => {
  it('puts the services under the tiles: a tap says a service is off, a second tap says it is back', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    const viewQ = vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const set = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('power', 'off'));
    const user = userEvent.setup();
    renderRoute('/');
    const row = await screen.findByRole('navigation', { name: 'Services' });
    const buttons = within(row).getAllByRole('button');
    expect(buttons.map((b) => b.textContent)).toEqual(['Poweron', 'Wateron', 'Mobileon', 'Landlineon', 'Interneton', 'Gason', 'Heatingon', 'Roadson', 'Shopson', 'Sewageon']);
    expect(buttons[0]).toHaveAttribute('aria-pressed', 'false');
    // The tiles come first: the row sits under them.
    const tiles = await screen.findByRole('navigation', { name: 'Scenarios' });
    expect(tiles.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    viewQ.mockResolvedValue(powerOffView);
    await user.click(buttons[0]);
    expect(set).toHaveBeenCalledWith('power', expect.objectContaining({ state: 'off', since: expect.any(String) }));
    // The tap registers that the service is off and nothing else: the screen stays where it was,
    // with the same tiles and the same row, and the button says so.
    const after = await screen.findByRole('navigation', { name: 'Services' });
    await waitFor(() => expect(within(after).getByRole('button', { name: /Mains power: off/ })).toHaveAttribute('aria-pressed', 'true'));
    await user.click(within(after).getByRole('button', { name: /Mains power: off/ }));
    expect(set).toHaveBeenLastCalledWith('power', expect.objectContaining({ state: 'working' }));
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

  it('stays the front door once something is off, and points at the sheet for the rest', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    // The question, the tiles and the row are exactly where they were: a household that tapped
    // Power to say the power was off was taken to a briefing it had not asked for, and the button
    // it had just pressed was gone off the screen.
    expect(await screen.findByRole('heading', { level: 1, name: "What's the situation?" })).toBeInTheDocument();
    expect(within(await screen.findByRole('navigation', { name: 'Scenarios' })).getAllByRole('link')).toHaveLength(20);
    const row = screen.getByRole('navigation', { name: 'Services' });
    const power = within(row).getByRole('button', { name: /Mains power: off/ });
    expect(power).toHaveAttribute('aria-pressed', 'true');
    expect(power).toHaveTextContent('off');
    // One line under the row is the whole of what the front door says about it.
    expect(screen.getByText(/2 services off\./)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'What to do now' })).toHaveAttribute('href', '/situation');
    // and none of the briefing is on it
    for (const name of ['Right now', 'Coming up', 'The box thinks', 'Read']) {
      expect(screen.queryByRole('region', { name })).toBeNull();
    }
    expect(screen.queryByRole('button', { name: 'Read aloud' })).toBeNull();
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
