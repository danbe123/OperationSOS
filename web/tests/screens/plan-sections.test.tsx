import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Person, StockItem } from '../../src/api/types';
import { householdPlan, notes } from '../fixtures/api';

const people: Person[] = [
  { id: 1, name: 'Sam', age: 7, needs: 'asthma', medications: 'salbutamol inhaler', contacts: '', updated_at: '2026-09-05T10:00:00Z' },
  { id: 2, name: 'Ali', age: null, needs: '', medications: '', contacts: 'Gran 0161 000', updated_at: '2026-09-05T10:00:00Z' },
];
const water: StockItem = { id: 1, name: 'Bottled water', category: 'water', quantity: 24, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: 4, kit_item: null };
const rice: StockItem = { id: 2, name: 'Rice', category: 'food', quantity: 5, unit: 'kg', per_person_day: null, expires: '2020-01-01', notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: null, kit_item: null };
const events = [
  { id: 30, kind: 'event' as const, title: 'Heard sirens', body: '', lat: null, lon: null, updated_at: '2026-09-05T11:30:00Z' },
  { id: 29, kind: 'event' as const, title: 'Water off', body: '', lat: null, lon: null, updated_at: '2026-09-05T10:15:00Z' },
];

function mockAll() {
  vi.spyOn(api, 'page').mockResolvedValue(householdPlan);
  vi.spyOn(api, 'notes').mockImplementation(async (kind) => (kind === 'event' ? events : notes.filter((n) => !kind || n.kind === kind)));
  vi.spyOn(api, 'household').mockResolvedValue(people);
  vi.spyOn(api, 'stock').mockResolvedValue({ people: 2, items: [water, rice] });
}

describe('Plan sections', () => {
  it('shows the household, stock days left with badges, and the event log newest first', async () => {
    mockAll();
    renderRoute('/plan');
    const household = await screen.findByRole('list', { name: 'Household' });
    expect(await within(household).findByText('Sam')).toBeInTheDocument();
    expect(within(household).getByText('salbutamol inhaler')).toBeInTheDocument();
    const summary = await screen.findByRole('list', { name: 'Stock summary' });
    expect(summary).toHaveTextContent('Water 4 days');
    const items = screen.getByRole('list', { name: 'Stock items' });
    expect(within(items).getByText('4 days')).toHaveClass('badge-warn');
    expect(within(items).getByText('expired')).toHaveClass('badge-danger');
    expect(screen.getByText(/Days left are for 2 people/)).toBeInTheDocument();
    const log = screen.getByRole('list', { name: 'Event log' });
    expect(within(log).getAllByRole('listitem').map((li) => li.textContent)).toEqual([expect.stringContaining('Heard sirens'), expect.stringContaining('Water off')]);
  });

  it('adds a person, an item and a log entry through the forms', async () => {
    mockAll();
    const addPerson = vi.spyOn(api, 'addPerson').mockResolvedValue({ ...people[0], id: 3, name: 'Jo' });
    const addStock = vi.spyOn(api, 'addStock').mockResolvedValue({ ...water, id: 3, name: 'Diesel', category: 'fuel', per_person_day: null });
    const createNote = vi.spyOn(api, 'createNote').mockResolvedValue(events[0]);
    renderRoute('/plan');
    const user = userEvent.setup();
    const personForm = await screen.findByRole('form', { name: 'Add a person' });
    await user.type(within(personForm).getByLabelText('Name'), 'Jo');
    await user.type(within(personForm).getByLabelText('Age'), '34');
    await user.click(within(personForm).getByRole('button', { name: 'Add person' }));
    expect(addPerson).toHaveBeenCalledWith({ name: 'Jo', age: 34, needs: '', medications: '', contacts: '' });

    const stockForm = screen.getByRole('form', { name: 'Add stock' });
    await user.selectOptions(within(stockForm).getByLabelText('Type'), 'fuel');
    await user.type(within(stockForm).getByLabelText('Item'), 'Diesel');
    await user.type(within(stockForm).getByLabelText('Quantity'), '40');
    await user.click(within(stockForm).getByRole('button', { name: 'Add item' }));
    expect(addStock).toHaveBeenCalledWith({ name: 'Diesel', category: 'fuel', quantity: 40, unit: 'L', per_person_day: null, expires: null });

    const logForm = screen.getByRole('form', { name: 'Log an event' });
    await user.type(within(logForm).getByLabelText('What happened'), 'Gave Sam 5ml paracetamol');
    await user.click(within(logForm).getByRole('button', { name: 'Log it' }));
    expect(createNote).toHaveBeenCalledWith({ kind: 'event', title: 'Gave Sam 5ml paracetamol' });
  });
});

describe('Medical household panel', () => {
  it('lists people with needs or medications', async () => {
    vi.spyOn(api, 'household').mockResolvedValue(people);
    renderRoute('/medical');
    const panel = await screen.findByRole('region', { name: 'Household medical needs' });
    expect(panel).toHaveTextContent('Sam');
    expect(panel).toHaveTextContent('asthma');
    expect(panel).not.toHaveTextContent('Ali');
    expect(within(panel).getByRole('link', { name: /Edit the register/ })).toHaveAttribute('href', '/plan#household');
  });
});
