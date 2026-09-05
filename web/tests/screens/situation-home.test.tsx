import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { condition, makeView, playbooks, powerOffView, view } from '../fixtures/api';

describe('Home: the situation strip', () => {
  it('shows the readiness score and the biggest gap in peacetime', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    const strip = await screen.findByRole('region', { name: 'Situation' });
    expect(strip).toHaveTextContent('Everything is working');
    expect(within(strip).getByLabelText('Readiness')).toHaveTextContent('62');
    expect(within(strip).getByRole('link', { name: 'Water: 1.5 days for 3 people' })).toHaveAttribute('href', '/plan#stock');
    expect(within(strip).getByLabelText('Gaps to close')).toHaveTextContent('worth 12 points');
    expect(within(strip).queryByRole('group', { name: 'What is working' })).toBeNull();
  });

  it('shows a chip per household condition, its colour, its symbol and how long', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const chips = await screen.findByRole('group', { name: 'What is working' });
    const links = within(chips).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('aria-label'))).toEqual([
      'Mains power: off for 1 h', 'Water supply: working', 'Mobile network: patchy for 1 h',
      'Landline and 999: working', 'Internet: working',
    ]);
    expect(links[0]).toHaveClass('cond-danger');
    expect(links[0]).toHaveTextContent('✕ off');
    expect(links[1]).toHaveClass('cond-ok');
    expect(links[2]).toHaveClass('cond-warn');
    expect(links[0]).toHaveAttribute('href', '/situation#power');
  });

  it('names the scenario and its clock, and flies the drill flag', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      meta: { ...view.meta, drill: true },
      scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
      conditions: { power: condition('power', 'off') } as never,
    }));
    renderRoute('/');
    const strip = await screen.findByRole('region', { name: 'Situation' });
    expect(strip).toHaveTextContent('DRILL');
    expect(within(strip).getByRole('link', { name: 'National grid collapse' })).toHaveAttribute('href', '/s/grid-collapse');
    expect(strip).toHaveTextContent('2 h in, right now');
  });

  it('puts the map first when the modes say so', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({ modes: { ...view.modes, map_first: true } }));
    renderRoute('/');
    const tools = await screen.findByRole('navigation', { name: 'Main sections' });
    expect(within(tools).getAllByRole('link')[0]).toHaveAttribute('href', '/map');
  });
});

describe('Home: the briefing', () => {
  it('offers the box\'s guess with Accept and Not now', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const accept = vi.spyOn(api, 'acceptInferred').mockResolvedValue(condition('mobile', 'off'));
    renderRoute('/');
    const block = await screen.findByRole('region', { name: 'The box thinks' });
    expect(block).toHaveTextContent('Mobile network is probably off');
    expect(block).toHaveTextContent('Masts run about 8 hours on battery.');
    await userEvent.setup().click(within(block).getByRole('button', { name: 'Accept' }));
    expect(accept).toHaveBeenCalledWith('mobile', 'power-off-mobile-off');
    expect(screen.queryByRole('region', { name: 'The box thinks' })).toBeNull();
  });

  it('dismisses a guess with Not now without writing anything', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const accept = vi.spyOn(api, 'acceptInferred');
    renderRoute('/');
    const block = await screen.findByRole('region', { name: 'The box thinks' });
    await userEvent.setup().click(within(block).getByRole('button', { name: 'Not now' }));
    expect(screen.queryByRole('region', { name: 'The box thinks' })).toBeNull();
    expect(accept).not.toHaveBeenCalled();
  });

  it('counts down the forecast due in the next day only', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const coming = await screen.findByRole('region', { name: 'Coming up' });
    const items = within(coming).getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Fridge food unsafe');
    expect(items[0]).toHaveTextContent('in 3 h');
    expect(items[1]).toHaveTextContent('Freezer food unsafe');
    expect(items[1]).toHaveTextContent('in 23 h');
    expect(items[1].querySelector('.badge-danger')).not.toBeNull();
    expect(within(items[1]).getByRole('link', { name: 'Read more' })).toHaveAttribute('href', '/m/food');
  });

  it('lists the now and hour tasks with names, and ticks one', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[0], done: true });
    renderRoute('/');
    const block = await screen.findByRole('region', { name: 'Do this now' });
    const items = within(block).getAllByRole('listitem');
    expect(items.map((li) => li.querySelector('.task-title')?.textContent)).toEqual([
      'Fill the bath and every container', 'Keep the fridge and freezer shut', 'Get cash out while the shops take cards',
    ]);
    expect(items[1]).toHaveTextContent('Sam');
    await userEvent.setup().click(within(block).getByRole('checkbox', { name: /Fill the bath/ }));
    expect(set).toHaveBeenCalledWith('fill-bath', { done: true });
    expect(await within(block).findByRole('checkbox', { name: /Fill the bath/ })).toBeChecked();
  });

  it('links the reading and names the next bulletin', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const reading = await screen.findByRole('region', { name: 'Read this' });
    expect(within(reading).getByRole('link', { name: 'Right now' })).toHaveAttribute('href', '/s/grid-collapse#right-now');
    expect(within(reading).getByRole('link', { name: 'Power' })).toHaveAttribute('href', '/m/power');
    expect(screen.getByText(/Next bulletin: BBC Radio 4, 198 kHz LW/)).toBeInTheDocument();
  });
});
