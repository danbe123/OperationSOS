import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { makeView, neighbours, powerOffView, view } from '../fixtures/api';

function mockStreet(over: { neighbours?: typeof neighbours } = {}) {
  vi.spyOn(api, 'neighbours').mockResolvedValue(over.neighbours ?? neighbours);
}

describe('Neighbours', () => {
  it('lists the street with what each one needs and can do, and the printable list', async () => {
    mockStreet();
    renderRoute('/plan/neighbours');
    expect(await screen.findByRole('heading', { name: 'Neighbours', level: 1 })).toBeInTheDocument();
    const rows = await screen.findByRole('list', { name: 'Neighbours' });
    // The street screen is fetched on demand, so the street arrives after the screen does.
    const items = await within(rows).findAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Joan Reeve');
    expect(items[0]).toHaveTextContent('14 Mill Lane');
    expect(items[0]).toHaveTextContent('oxygen concentrator');
    expect(items[1]).toHaveTextContent('nurse, has a petrol generator');
    expect(screen.getByRole('link', { name: /Printable street list/ })).toHaveAttribute('href', '/api/street-list');
    expect(screen.queryByRole('form', { name: 'Add a neighbour' })).toBeNull();
  });

  it('says so when nobody is on the list yet, with the button to add the first one', async () => {
    mockStreet({ neighbours: [] });
    renderRoute('/plan/neighbours');
    const rows = await screen.findByRole('list', { name: 'Neighbours' });
    expect(await within(rows).findByText(/Nobody on the street list yet/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add a neighbour' })).toBeInTheDocument();
  });

  it('adds, edits and removes a neighbour, with the form behind the button', async () => {
    mockStreet({ neighbours: [] });
    const add = vi.spyOn(api, 'addNeighbour').mockResolvedValue(neighbours[0]);
    const update = vi.spyOn(api, 'updateNeighbour').mockResolvedValue(neighbours[0]);
    const remove = vi.spyOn(api, 'deleteNeighbour').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/plan/neighbours');
    await user.click(await screen.findByRole('button', { name: 'Add a neighbour' }));
    const form = screen.getByRole('form', { name: 'Add a neighbour' });
    await user.type(within(form).getByRole('textbox', { name: 'Neighbour name' }), 'Joan Reeve');
    await user.type(within(form).getByRole('textbox', { name: 'Neighbour address' }), '14 Mill Lane');
    vi.mocked(api.neighbours).mockResolvedValue(neighbours);
    await user.click(within(form).getByRole('button', { name: 'Add neighbour' }));
    expect(add).toHaveBeenCalledWith(expect.objectContaining({ name: 'Joan Reeve', address: '14 Mill Lane' }));
    expect(screen.queryByRole('form', { name: 'Add a neighbour' })).toBeNull();

    await user.click(await screen.findByRole('button', { name: 'Edit Joan Reeve' }));
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(update).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'Joan Reeve' }));

    await user.click(screen.getByRole('button', { name: 'Remove Joan Reeve' }));
    await user.click(screen.getByRole('button', { name: 'Confirm remove' }));
    expect(remove).toHaveBeenCalledWith(1);
  });

  it('flags who to check on, and lists what the street can do, from the View', async () => {
    mockStreet();
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      ...powerOffView,
      neighbours: {
        check_on: [{ id: 'neighbour:joan-reeve', name: 'Joan Reeve', address: '14 Mill Lane', needs: 'oxygen concentrator', contacts: '07700 900123', title: 'Knock on Joan Reeve, 14 Mill Lane', why: 'oxygen concentrator', rule: 'neighbour-check-joan-reeve', link: null, bucket: 'today', done: false }],
        skills: [{ name: 'Ade Okafor', address: '18 Mill Lane', skill: 'nurse', text: 'a nurse two doors down', contacts: '07700 900456', why: 'On the street list.', rule: 'neighbour-skill-ade-okafor', link: null }],
      },
    }));
    renderRoute('/plan/neighbours');
    const items = within(await screen.findByRole('list', { name: 'Neighbours' })).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('check on');
    expect(items[1]).not.toHaveTextContent('check on');
    expect(screen.getByRole('region', { name: 'What the street can do' })).toHaveTextContent('a nurse two doors down');
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
