import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { makeView, neighbours, page, powerOffView, stockResponse, view } from '../fixtures/api';

function mockPlan(over: { neighbours?: typeof neighbours } = {}) {
  vi.spyOn(api, 'page').mockResolvedValue(page);
  vi.spyOn(api, 'household').mockResolvedValue([]);
  vi.spyOn(api, 'stock').mockResolvedValue(stockResponse);
  vi.spyOn(api, 'notes').mockResolvedValue([]);
  vi.spyOn(api, 'neighbours').mockResolvedValue(over.neighbours ?? neighbours);
}

describe('Neighbours', () => {
  it('lists the street with what each one needs and can do, and the printable list', async () => {
    mockPlan();
    renderRoute('/plan');
    const section = await screen.findByRole('region', { name: 'Neighbours' });
    const rows = within(section).getByRole('list', { name: 'Neighbours' });
    // The plan is one of the screens the shell fetches on demand, so the street arrives after it.
    const items = await within(rows).findAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Joan Reeve');
    expect(items[0]).toHaveTextContent('14 Mill Lane');
    expect(items[0]).toHaveTextContent('oxygen concentrator');
    expect(items[1]).toHaveTextContent('nurse, has a petrol generator');
    expect(within(section).getByRole('link', { name: /Printable street list/ })).toHaveAttribute('href', '/api/street-list');
  });

  it('says so when nobody is on the list yet', async () => {
    mockPlan({ neighbours: [] });
    renderRoute('/plan');
    const section = await screen.findByRole('region', { name: 'Neighbours' });
    expect(section).toHaveTextContent('Nobody on the street list yet');
  });

  it('adds, edits and removes a neighbour', async () => {
    mockPlan({ neighbours: [] });
    const add = vi.spyOn(api, 'addNeighbour').mockResolvedValue(neighbours[0]);
    const update = vi.spyOn(api, 'updateNeighbour').mockResolvedValue(neighbours[0]);
    const remove = vi.spyOn(api, 'deleteNeighbour').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/plan');
    const section = await screen.findByRole('region', { name: 'Neighbours' });
    const form = within(section).getByRole('form', { name: 'Add a neighbour' });
    await user.type(within(form).getByRole('textbox', { name: 'Neighbour name' }), 'Joan Reeve');
    await user.type(within(form).getByRole('textbox', { name: 'Neighbour address' }), '14 Mill Lane');
    vi.mocked(api.neighbours).mockResolvedValue(neighbours);
    await user.click(within(form).getByRole('button', { name: 'Add neighbour' }));
    expect(add).toHaveBeenCalledWith(expect.objectContaining({ name: 'Joan Reeve', address: '14 Mill Lane' }));

    await user.click(await within(section).findByRole('button', { name: 'Edit Joan Reeve' }));
    await user.click(within(section).getByRole('button', { name: 'Save' }));
    expect(update).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'Joan Reeve' }));

    await user.click(within(section).getByRole('button', { name: 'Remove Joan Reeve' }));
    await user.click(within(section).getByRole('button', { name: 'Confirm remove' }));
    expect(remove).toHaveBeenCalledWith(1);
  });

  it('flags who to check on, and lists what the street can do, from the View', async () => {
    mockPlan();
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      ...powerOffView,
      neighbours: {
        check_on: [{ id: 'neighbour:joan-reeve', name: 'Joan Reeve', address: '14 Mill Lane', needs: 'oxygen concentrator', contacts: '07700 900123', title: 'Knock on Joan Reeve, 14 Mill Lane', why: 'oxygen concentrator', rule: 'neighbour-check-joan-reeve', link: null, bucket: 'today', done: false }],
        skills: [{ name: 'Ade Okafor', address: '18 Mill Lane', skill: 'nurse', text: 'a nurse two doors down', contacts: '07700 900456', why: 'On the street list.', rule: 'neighbour-skill-ade-okafor', link: null }],
      },
    }));
    renderRoute('/plan');
    const section = await screen.findByRole('region', { name: 'Neighbours' });
    const items = within(within(section).getByRole('list', { name: 'Neighbours' })).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('check on');
    expect(items[1]).not.toHaveTextContent('check on');
    expect(within(section).getByRole('region', { name: 'What the street can do' })).toHaveTextContent('a nurse two doors down');
  });

  it('renders the knock-on-the-door job once, on the task list', async () => {
    vi.spyOn(api, 'household').mockResolvedValue([]);
    const checkTask = { id: 'neighbour:joan-reeve', title: 'Knock on Joan Reeve, 14 Mill Lane', bucket: 'today' as const, why: 'oxygen concentrator', link: null, person: null, done: false, done_at: null, source: 'rule:neighbours' };
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({ ...view, tasks: [checkTask] }));
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...checkTask, done: true });
    renderRoute('/tasks');
    const tick = await screen.findByRole('checkbox', { name: /Knock on Joan Reeve/ });
    await userEvent.setup().click(tick);
    expect(set).toHaveBeenCalledWith('neighbour:joan-reeve', { done: true });
  });
});
