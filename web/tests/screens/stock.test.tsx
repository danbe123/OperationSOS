import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { StockItem, StockResponse } from '../../src/api/types';
import { meter, sortStock } from '../../src/screens/plan/Stock';

const AT = '2026-09-05T10:00:00Z';
const row = (over: Partial<StockItem> & Pick<StockItem, 'id' | 'name' | 'category'>): StockItem => ({
  quantity: 1, unit: '', per_person_day: null, expires: null, notes: '', updated_at: AT,
  days_left: null, expired: false, kit_item: null, ...over,
});

/** Two weeks of water for two would be 84 litres; the cupboard holds twelve, and twelve more that
 * went off in 2020 and count for nothing. */
const stock: StockResponse = {
  people: 2,
  days: { water: 4, food: 6, medicine: 0 },
  items: [
    row({ id: 2, name: 'Rice', category: 'food', quantity: 12, unit: 'person-days', per_person_day: 1, days_left: 6 }),
    row({ id: 1, name: 'Bottled water', category: 'water', quantity: 12, unit: 'L', per_person_day: 3, days_left: 4 }),
    row({ id: 3, name: 'Old bottles', category: 'water', quantity: 12, unit: 'L', per_person_day: 3, expires: '2020-01-01', days_left: 0, expired: true }),
    row({ id: 4, name: 'Torch', category: 'other', quantity: 2, days_left: null }),
  ],
};

function mockStock(over: Partial<StockResponse> = {}) {
  return vi.spyOn(api, 'stock').mockResolvedValue({ ...stock, ...over });
}

describe('The Stock screen', () => {
  it('is a screen of its own, and says who the days are for', async () => {
    mockStock();
    renderRoute('/plan/stock');
    expect(await screen.findByRole('heading', { level: 1, name: 'Stock' })).toBeInTheDocument();
    expect(await screen.findByText(/Days are for 2 on the register\./)).toBeInTheDocument();
    expect(screen.getByText(/3 litres a person a day/)).toBeInTheDocument();
  });

  it('meters water, food and medicine against two weeks', async () => {
    mockStock();
    renderRoute('/plan/stock');
    const meters = await screen.findByRole('list', { name: 'Stock meters' });
    const bars = within(meters).getAllByRole('listitem');
    expect(bars).toHaveLength(3);
    // The expired twelve litres are not held: what is left is twelve, four days of it.
    expect(bars[0]).toHaveTextContent('12 L · 4 days for 2 people · two weeks needs 84 L');
    expect(bars[1]).toHaveTextContent('12 person-days · 6 days for 2 people · two weeks needs 28 person-days');
    expect(bars[2]).toHaveTextContent('0 days of supply · 0 days for 2 people · two weeks needs 28 days of supply');
    const bar = within(meters).getByRole('progressbar', { name: 'Water against two weeks' });
    expect(bar).toHaveAttribute('value', '4');
    expect(bar).toHaveAttribute('max', '14');
    expect(bar).toHaveClass('progress-line');
  });

  it('works the meter out from the rows that still count', () => {
    expect(meter('water', stock)).toEqual({ title: 'Water', held: '12 L', days: 4, need: 'two weeks needs 84 L', fraction: 4 / 14 });
    // A month of water is still a full bar: the meter is against two weeks, and no further.
    expect(meter('water', { ...stock, days: { ...stock.days, water: 30 } }).fraction).toBe(1);
  });

  it('lists the rows in category order, shortest run first', async () => {
    mockStock();
    renderRoute('/plan/stock');
    const list = await screen.findByRole('list', { name: 'Stock items' });
    const rows = within(list).getAllByRole('listitem');
    expect(rows.map((li) => within(li).getByRole('button', { name: /^Change / }).getAttribute('aria-label'))).toEqual([
      'Change Old bottles', 'Change Bottled water', 'Change Rice', 'Change Torch',
    ]);
    expect(sortStock(stock.items).map((i) => i.id)).toEqual([3, 1, 2, 4]);
    // The expired row says so, and the date itself is kept off the row.
    expect(within(rows[0]).getByText('expired')).toHaveClass('badge-danger');
    expect(rows[0]).toHaveTextContent('12 L');
    expect(rows[0]).not.toHaveTextContent('01/01/2020');
    expect(within(rows[1]).getByText('4 days')).toHaveClass('badge-warn');
  });

  it('keeps the row read-first: the edit is behind Change', async () => {
    mockStock();
    const updateStock = vi.spyOn(api, 'updateStock').mockResolvedValue(stock.items[1]);
    renderRoute('/plan/stock');
    const list = await screen.findByRole('list', { name: 'Stock items' });
    const water = within(list).getAllByRole('listitem')[1];
    expect(within(water).queryByLabelText('Quantity of Bottled water')).toBeNull();
    const user = userEvent.setup();
    await user.click(within(water).getByRole('button', { name: 'Change Bottled water' }));
    const quantity = within(water).getByLabelText('Quantity of Bottled water');
    expect(within(water).getByLabelText('Use by for Bottled water')).toBeInTheDocument();
    // The rate is the category's, said as a fact rather than offered as a field.
    expect(water).toHaveTextContent('counts as 3 L per person a day');
    await user.clear(quantity);
    await user.type(quantity, '18');
    await user.click(within(water).getByRole('button', { name: 'Save' }));
    expect(updateStock).toHaveBeenCalledWith(1, { quantity: 18 });
    expect(within(water).queryByLabelText('Quantity of Bottled water')).toBeNull();
  });

  it('adds an item behind a button, at the rate its type carries', async () => {
    mockStock();
    const addStock = vi.spyOn(api, 'addStock').mockResolvedValue(stock.items[0]);
    renderRoute('/plan/stock');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'Add something else' }));
    const form = screen.getByRole('form', { name: 'Add stock' });
    await user.selectOptions(within(form).getByLabelText('Type'), 'fuel');
    await user.type(within(form).getByLabelText('Item'), 'Diesel');
    await user.type(within(form).getByLabelText('Quantity'), '40');
    expect(within(form).getByLabelText('Unit')).toHaveValue('L');
    expect(within(form).queryByLabelText(/per person a day/i)).toBeNull();
    await user.click(within(form).getByRole('button', { name: 'Add item' }));
    // No rate is sent: the API holds the rate for the type.
    expect(addStock).toHaveBeenCalledWith({ name: 'Diesel', category: 'fuel', quantity: 40, unit: 'L', expires: null });
    expect(screen.queryByRole('form', { name: 'Add stock' })).toBeNull();
  });

  it('puts the add form away again on Cancel', async () => {
    mockStock();
    renderRoute('/plan/stock');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'Add something else' }));
    await user.click(within(screen.getByRole('form', { name: 'Add stock' })).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form', { name: 'Add stock' })).toBeNull();
  });
});

describe('Stock rows from a kit', () => {
  it('label the kit and link to it', async () => {
    mockStock({ people: 1, days: { water: 3, food: 4, medicine: 0 }, items: [
      row({ id: 3, name: 'Drinking water in sealed containers', category: 'water', quantity: 9, unit: 'L', per_person_day: 3, days_left: 3, kit_item: 'water/stored-water' }),
      row({ id: 2, name: 'Tins', category: 'food', quantity: 4, unit: 'person-days', per_person_day: 1, days_left: 4, kit_title: null }),
      row({ id: 1, name: 'Torch', category: 'other', quantity: 2, kit_item: 'power-and-light/torch', kit_title: 'Power and light' }),
    ] });
    renderRoute('/plan/stock');
    const list = await screen.findByRole('list', { name: 'Stock items' });
    const rows = within(list).getAllByRole('listitem');
    // A row saved before the API sent a title still names its kit, from the slug.
    expect(within(rows[0]).getByRole('link', { name: 'From the Water kit' })).toHaveAttribute('href', '/kit/water');
    expect(within(rows[1]).queryByRole('link', { name: /kit/ })).toBeNull();
    // The kit's own title, not a slug dressed up: "power-and-light" would have read "Power and light kit" by luck,
    // but "Baby and child" or "Fallout and CBRN" would not.
    expect(within(rows[2]).getByRole('link', { name: 'From the Power and light kit' })).toHaveAttribute('href', '/kit/power-and-light');
  });
});
