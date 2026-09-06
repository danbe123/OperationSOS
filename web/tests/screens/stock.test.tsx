import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { StockItem } from '../../src/api/types';
import { Stock } from '../../src/screens/plan/Stock';

/* Stock has no screen of its own yet — the Household hub links to `/plan/stock`, which the Stock
 * screen claims — so the section is mounted on a route of its own here. */
function renderStock() {
  return renderRoute('/stock', { routes: [{ path: '/stock', element: <Stock /> }] });
}

const water: StockItem = { id: 1, name: 'Bottled water', category: 'water', quantity: 24, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: 4, kit_item: null };
const rice: StockItem = { id: 2, name: 'Rice', category: 'food', quantity: 5, unit: 'kg', per_person_day: null, expires: '2020-01-01', notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: null, kit_item: null };

describe('Stock', () => {
  it('shows the days left, the badges and who the days are for', async () => {
    vi.spyOn(api, 'stock').mockResolvedValue({ people: 2, days: { water: 4, food: 0, medicine: 0 }, items: [water, rice] });
    renderStock();
    const summary = await screen.findByRole('list', { name: 'Stock summary' });
    expect(summary).toHaveTextContent('Water 4 days');
    const items = screen.getByRole('list', { name: 'Stock items' });
    expect(within(items).getByText('4 days')).toHaveClass('badge-warn');
    expect(within(items).getByText('expired')).toHaveClass('badge-danger');
    expect(screen.getByText(/Days left are for 2 people/)).toBeInTheDocument();
  });

  it('adds an item through the form', async () => {
    vi.spyOn(api, 'stock').mockResolvedValue({ people: 2, days: { water: 4, food: 0, medicine: 0 }, items: [water, rice] });
    const addStock = vi.spyOn(api, 'addStock').mockResolvedValue({ ...water, id: 3, name: 'Diesel', category: 'fuel', per_person_day: null });
    renderStock();
    const user = userEvent.setup();
    const stockForm = await screen.findByRole('form', { name: 'Add stock' });
    await user.selectOptions(within(stockForm).getByLabelText('Type'), 'fuel');
    await user.type(within(stockForm).getByLabelText('Item'), 'Diesel');
    await user.type(within(stockForm).getByLabelText('Quantity'), '40');
    await user.click(within(stockForm).getByRole('button', { name: 'Add item' }));
    expect(addStock).toHaveBeenCalledWith({ name: 'Diesel', category: 'fuel', quantity: 40, unit: 'L', per_person_day: null, expires: null });
  });
});

describe('Stock rows from a kit', () => {
  it('label the kit and link to it', async () => {
    vi.spyOn(api, 'stock').mockResolvedValue({ people: 1, days: { water: 3, food: 4, medicine: 0 }, items: [
      { id: 1, name: 'Torch', category: 'other', quantity: 2, unit: '', per_person_day: null, expires: null, notes: '', updated_at: '2026-09-06T10:00:00+00:00', days_left: null, kit_item: 'power-and-light/torch', kit_title: 'Power and light' },
      { id: 2, name: 'Tins', category: 'food', quantity: 4, unit: 'days of meals', per_person_day: 1, expires: null, notes: '', updated_at: '2026-09-06T10:00:00+00:00', days_left: 4, kit_item: null, kit_title: null },
      { id: 3, name: 'Drinking water in sealed containers', category: 'water', quantity: 9, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-06T10:00:00+00:00', days_left: 3, kit_item: 'water/stored-water' },
    ] });
    renderStock();
    await screen.findByRole('list', { name: 'Stock summary' }); // waits for stock data to have loaded
    const list = screen.getByRole('list', { name: 'Stock items' });
    const rows = within(list).getAllByRole('listitem');
    // The kit's own title, not a slug dressed up: "power-and-light" would have read "Power and light kit" by luck,
    // but "Baby and child" or "Fallout and CBRN" would not.
    expect(within(rows[0]).getByRole('link', { name: 'From the Power and light kit' })).toHaveAttribute('href', '/kit/power-and-light');
    expect(within(rows[1]).queryByRole('link', { name: /kit/ })).toBeNull();
    // A row saved before the API sent a title still names its kit, from the slug.
    expect(within(rows[2]).getByRole('link', { name: 'From the Water kit' })).toHaveAttribute('href', '/kit/water');
  });
});
