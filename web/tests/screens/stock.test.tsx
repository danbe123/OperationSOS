import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { householdPlan } from '../fixtures/api';

describe('Stock rows from a kit', () => {
  it('label the kit and link to it', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(householdPlan);
    vi.spyOn(api, 'household').mockResolvedValue([]);
    vi.spyOn(api, 'neighbours').mockResolvedValue([]);
    vi.spyOn(api, 'notes').mockResolvedValue([]);
    vi.spyOn(api, 'stock').mockResolvedValue({ people: 1, items: [
      { id: 1, name: 'Drinking water in sealed containers', category: 'water', quantity: 9, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-06T10:00:00+00:00', days_left: 3, kit_item: 'water/stored-water' },
      { id: 2, name: 'Tins', category: 'food', quantity: 4, unit: 'days of meals', per_person_day: 1, expires: null, notes: '', updated_at: '2026-09-06T10:00:00+00:00', days_left: 4, kit_item: null },
    ] });
    renderRoute('/plan');
    await screen.findByRole('list', { name: 'Stock summary' }); // waits for stock data to have loaded
    const list = screen.getByRole('list', { name: 'Stock items' });
    const rows = within(list).getAllByRole('listitem');
    expect(within(rows[0]).getByRole('link', { name: 'From the Water kit' })).toHaveAttribute('href', '/kit/water');
    expect(within(rows[1]).queryByRole('link', { name: /kit/ })).toBeNull();
  });
});
