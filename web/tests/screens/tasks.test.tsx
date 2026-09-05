import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { powerOffView } from '../fixtures/api';

const people = [
  { id: 1, name: 'Sam', age: 41, needs: '', medications: '', contacts: '', updated_at: '2026-09-01T10:00:00Z' },
  { id: 2, name: 'Alex', age: 12, needs: 'asthma', medications: 'salbutamol', contacts: '', updated_at: '2026-09-01T10:00:00Z' },
];

describe('Tasks', () => {
  it('groups the jobs into buckets, hides the done ones and counts what is left', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    vi.spyOn(api, 'household').mockResolvedValue(people);
    renderRoute('/tasks');
    const now = await screen.findByRole('region', { name: 'Now' });
    expect(within(now).getAllByRole('listitem')).toHaveLength(2);
    expect(within(now).getByText('Pumped supplies fail once the power has been off a day.')).toBeInTheDocument();
    expect(within(now).getByRole('link', { name: 'Read more: Fill the bath and every container' })).toHaveAttribute('href', '/m/water');
    expect(screen.getByRole('region', { name: 'Within the hour' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Today' })).toBeNull();          // its only task is done
    expect(screen.getByText('3 to do, 1 done.')).toBeInTheDocument();
    expect(screen.getByText('3 to do')).toHaveClass('task-count');
  });

  it('shows the done ones on request, struck through', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    vi.spyOn(api, 'household').mockResolvedValue(people);
    renderRoute('/tasks');
    await userEvent.setup().click(await screen.findByRole('checkbox', { name: 'Show done' }));
    const today = screen.getByRole('region', { name: 'Today' });
    expect(within(today).getByRole('listitem')).toHaveClass('task-done');
    expect(within(today).getByRole('checkbox', { name: /Knock on both neighbours/ })).toBeChecked();
  });

  it('assigns a task to somebody in the household', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    vi.spyOn(api, 'household').mockResolvedValue(people);
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[0], person: 'Alex' });
    renderRoute('/tasks');
    const select = await screen.findByRole('combobox', { name: 'Who is doing: Fill the bath and every container' });
    expect(within(select).getAllByRole('option').map((o) => o.textContent)).toEqual(['Nobody yet', 'Sam', 'Alex']);
    await userEvent.setup().selectOptions(select, 'Alex');
    expect(set).toHaveBeenCalledWith('fill-bath', { person: 'Alex' });
    expect(await screen.findByRole('combobox', { name: 'Who is doing: Fill the bath and every container' })).toHaveValue('Alex');
  });

  it('ticks a task off', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    vi.spyOn(api, 'household').mockResolvedValue(people);
    const set = vi.spyOn(api, 'setTask').mockResolvedValue({ ...powerOffView.tasks[2], done: true });
    renderRoute('/tasks');
    await userEvent.setup().click(await screen.findByRole('checkbox', { name: /Get cash out/ }));
    expect(set).toHaveBeenCalledWith('cash', { done: true });
    expect(await screen.findByText('2 to do, 2 done.')).toBeInTheDocument();
  });

  it('says so when there is nothing to do', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue({ ...powerOffView, tasks: [] });
    vi.spyOn(api, 'household').mockResolvedValue([]);
    renderRoute('/tasks');
    expect(await screen.findByText(/Nothing to do/)).toBeInTheDocument();
  });
});
