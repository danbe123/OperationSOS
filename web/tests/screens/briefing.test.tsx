import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { condition, playbooks, powerOffView } from '../fixtures/api';

function mockNow() {
  vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
  vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
}

describe('Now: the briefing', () => {
  it("offers the box's guess with Accept and Not now", async () => {
    mockNow();
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
    mockNow();
    const accept = vi.spyOn(api, 'acceptInferred');
    renderRoute('/');
    const block = await screen.findByRole('region', { name: 'The box thinks' });
    await userEvent.setup().click(within(block).getByRole('button', { name: 'Not now' }));
    expect(screen.queryByRole('region', { name: 'The box thinks' })).toBeNull();
    expect(accept).not.toHaveBeenCalled();
  });

  it('counts down the forecast due in the next day only', async () => {
    mockNow();
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

  it('lists the now and hour jobs with names, and ticks one', async () => {
    mockNow();
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[0], done: true });
    renderRoute('/');
    const block = await screen.findByRole('region', { name: 'Right now' });
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
    mockNow();
    renderRoute('/');
    const reading = await screen.findByRole('region', { name: 'Read this' });
    expect(within(reading).getByRole('link', { name: 'Right now' })).toHaveAttribute('href', '/s/grid-collapse#right-now');
    expect(within(reading).getByRole('link', { name: 'Power' })).toHaveAttribute('href', '/m/power');
    expect(reading).toHaveTextContent('Next bulletin: BBC Radio 4, 198 kHz LW');
  });
});
