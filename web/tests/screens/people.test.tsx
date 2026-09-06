import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Person } from '../../src/api/types';

const people: Person[] = [
  { id: 1, name: 'Sam', age: 7, needs: 'asthma', medications: 'salbutamol inhaler', contacts: '', updated_at: '2026-09-05T10:00:00Z' },
  { id: 2, name: 'Ali', age: null, needs: '', medications: '', contacts: 'Gran 0161 000', updated_at: '2026-09-05T10:00:00Z' },
];

describe('People', () => {
  it('lists who lives here, and keeps the form behind a button', async () => {
    vi.spyOn(api, 'household').mockResolvedValue(people);
    renderRoute('/plan/people');
    expect(await screen.findByRole('heading', { name: 'People', level: 1 })).toBeInTheDocument();
    const list = await screen.findByRole('list', { name: 'Household' });
    expect(await within(list).findByText('Sam')).toBeInTheDocument();
    expect(within(list).getByText('salbutamol inhaler')).toBeInTheDocument();
    expect(screen.getByText(/Medical needs also show on the Medical screen/)).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Add a person' })).toBeNull();
  });

  it('opened directly, Back lands on the household hub, not further back in history', async () => {
    vi.spyOn(api, 'household').mockResolvedValue(people);
    const { router } = renderRoute('/plan/people');
    await screen.findByRole('heading', { name: 'People', level: 1 });
    await userEvent.setup().click(screen.getByRole('button', { name: /Back/ }));
    expect(router.state.location.pathname).toBe('/plan');
  });

  it('says so when nobody is registered, with the button to add the first one', async () => {
    vi.spyOn(api, 'household').mockResolvedValue([]);
    renderRoute('/plan/people');
    const list = await screen.findByRole('list', { name: 'Household' });
    expect(await within(list).findByText(/Nobody registered yet/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add a person' })).toBeInTheDocument();
  });

  it('adds a person behind the button, and hides the form again', async () => {
    vi.spyOn(api, 'household').mockResolvedValue([]);
    const addPerson = vi.spyOn(api, 'addPerson').mockResolvedValue({ ...people[0], id: 3, name: 'Jo' });
    const user = userEvent.setup();
    renderRoute('/plan/people');
    await user.click(await screen.findByRole('button', { name: 'Add a person' }));
    const form = screen.getByRole('form', { name: 'Add a person' });
    await user.type(within(form).getByLabelText('Name'), 'Jo');
    await user.type(within(form).getByLabelText('Age'), '34');
    vi.mocked(api.household).mockResolvedValue([{ ...people[0], id: 3, name: 'Jo', age: 34, needs: '', medications: '' }]);
    await user.click(within(form).getByRole('button', { name: 'Add person' }));
    expect(addPerson).toHaveBeenCalledWith({ name: 'Jo', age: 34, needs: '', medications: '', contacts: '' });
    expect(await screen.findByText('Jo')).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Add a person' })).toBeNull();
  });

  it('cancels back to the list without saving', async () => {
    vi.spyOn(api, 'household').mockResolvedValue(people);
    const addPerson = vi.spyOn(api, 'addPerson');
    const user = userEvent.setup();
    renderRoute('/plan/people');
    await user.click(await screen.findByRole('button', { name: 'Add a person' }));
    await user.click(within(screen.getByRole('form', { name: 'Add a person' })).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form', { name: 'Add a person' })).toBeNull();
    expect(addPerson).not.toHaveBeenCalled();
  });

  it('edits and removes a person from the row', async () => {
    vi.spyOn(api, 'household').mockResolvedValue(people);
    const update = vi.spyOn(api, 'updatePerson').mockResolvedValue(people[0]);
    const remove = vi.spyOn(api, 'deletePerson').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/plan/people');
    await user.click(await screen.findByRole('button', { name: 'Edit Sam' }));
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(update).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'Sam', needs: 'asthma' }));

    await user.click(await screen.findByRole('button', { name: 'Remove Sam' }));
    await user.click(screen.getByRole('button', { name: 'Confirm remove' }));
    expect(remove).toHaveBeenCalledWith(1);
  });
});
