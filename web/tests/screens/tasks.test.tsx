import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { powerOffView } from '../fixtures/api';

describe('Tasks', () => {
  it('groups the jobs into buckets, hides the done ones and counts what is left', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/tasks');
    const now = await screen.findByRole('region', { name: 'Right now' });
    expect(within(now).getAllByRole('listitem')).toHaveLength(2);
    expect(within(now).getByText('Pumped supplies fail once the power has been off a day.')).toBeInTheDocument();
    expect(within(now).getByRole('link', { name: 'Read more: Fill the bath and every container' })).toHaveAttribute('href', '/m/water');
    expect(screen.getByRole('region', { name: 'Within the hour' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Today' })).toBeNull();          // its only task is done
    expect(screen.getByText('3 to do, 1 done.')).toHaveClass('task-count');
  });

  it('shows the done ones on request, struck through', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/tasks');
    // The filter is a chip, not a tick: a filter and a job must not look like the same control.
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Show done' }));
    const today = screen.getByRole('region', { name: 'Today' });
    expect(within(today).getByRole('listitem')).toHaveClass('task-done');
    expect(within(today).getByRole('checkbox', { name: /Find the wind-up radio/ })).toBeChecked();
  });

  it('takes a name for a job, typed in, with nobody to pick from first', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[0], person: 'Alex' });
    renderRoute('/tasks');
    // A name, not a register: the box asks nobody to type the household in before a job can be given out.
    const who = await screen.findByRole('textbox', { name: 'Who is doing this: Fill the bath and every container' });
    expect(screen.queryByRole('combobox', { name: /Who is doing/ })).toBeNull();
    const user = userEvent.setup();
    await user.type(who, 'Alex');
    await user.tab();
    expect(set).toHaveBeenCalledWith('fill-bath', { person: 'Alex' });
    // Once the job has a name on it, the box says the name rather than asking again.
    expect(await screen.findByText('Alex')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'Who is doing this: Fill the bath and every container' })).toBeNull();
  });

  it('takes the name on Enter too, and does not save an empty one', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[0], person: 'Jo' });
    renderRoute('/tasks');
    const who = await screen.findByRole('textbox', { name: 'Who is doing this: Fill the bath and every container' });
    const user = userEvent.setup();
    await user.click(who);
    await user.tab();
    expect(set).not.toHaveBeenCalled();
    await user.type(who, 'Jo{Enter}');
    expect(set).toHaveBeenCalledWith('fill-bath', { person: 'Jo' });
  });

  it('does not ask who is doing a job that already has a name on it', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/tasks');
    await screen.findByRole('region', { name: 'Right now' });
    expect(screen.queryByRole('textbox', { name: 'Who is doing this: Keep the fridge and freezer shut' })).toBeNull();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });

  it('ticks a task off', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[2], done: true });
    renderRoute('/tasks');
    await userEvent.setup().click(await screen.findByRole('checkbox', { name: /Get cash out/ }));
    expect(set).toHaveBeenCalledWith('cash', { done: true });
    expect(await screen.findByText('2 to do, 2 done.')).toBeInTheDocument();
  });

  it('says so when there is nothing to do', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue({ ...powerOffView, tasks: [] });
    renderRoute('/tasks');
    expect(await screen.findByText(/Nothing to do/)).toBeInTheDocument();
  });
});
