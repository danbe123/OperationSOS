import { describe, it, expect, vi } from 'vitest';
import { screen, within, act, fireEvent } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { kitWater } from '../fixtures/api';

describe('Kit', () => {
  it('shows the intro, three tiers with basic open, quantities and the stock line', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    renderRoute('/kit/water');
    expect(await screen.findByRole('heading', { level: 1, name: 'Water' })).toBeInTheDocument();
    expect(screen.getByText('Three litres a person a day is the planning figure.')).toBeInTheDocument();
    const basic = screen.getByRole('group', { name: /Three days/ });
    expect(basic).toHaveAttribute('open');
    expect(screen.getByRole('group', { name: /Two weeks/ })).not.toHaveAttribute('open');
    expect(within(basic).getByText('18 L for 2 people over 3 days')).toBeInTheDocument();
    expect(within(basic).getByText(/18 L in Stock/)).toBeInTheDocument();
    expect(within(basic).getByRole('link', { name: 'Water module' })).toHaveAttribute('href', '/m/water');
    expect(within(basic).getByRole('checkbox', { name: /Drinking water/ })).toBeChecked();
  });

  it('ticks an item and offers Add to Stock prefilled with the scaled quantity', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    const ticked = { ...kitWater, tiers: kitWater.tiers.map((t) => t.id !== 'serious' ? t : { ...t, done: 1, items: t.items.map((i) => ({ ...i, checked: true, updated_at: '2026-09-06T11:00:00+00:00' })) }) };
    const set = vi.spyOn(api, 'setKitItem').mockResolvedValue(ticked);
    renderRoute('/kit/water');
    const serious = await screen.findByRole('group', { name: /Two weeks/ });
    await act(async () => { within(serious).getByText('Two weeks').click(); });
    const box = within(serious).getByRole('checkbox', { name: /Water purification tablets/ });
    await act(async () => { box.click(); });
    expect(set).toHaveBeenCalledWith('water', 'tablets', { checked: true });
    const add = await within(serious).findByRole('button', { name: /Add to Stock/ });
    await act(async () => { add.click(); });
    const form = within(serious).getByRole('form', { name: 'Add to Stock' });
    expect(within(form).getByLabelText('Quantity (packs)')).toHaveValue(1);
    fireEvent.change(within(form).getByLabelText('Use by'), { target: { value: '01/01/2027' } });
    set.mockResolvedValue({ ...ticked, tiers: ticked.tiers.map((t) => t.id !== 'serious' ? t : { ...t, items: t.items.map((i) => ({ ...i, stock_item: { id: 9, quantity: 1, unit: 'packs', expires: '2027-01-01', days_left: null } })) }) });
    await act(async () => { within(form).getByRole('button', { name: 'Save to Stock' }).click(); });
    expect(set).toHaveBeenLastCalledWith('water', 'tablets', { checked: true, stock: { quantity: 1, expires: '2027-01-01' } });
    expect(await within(serious).findByText(/1 packs in Stock/)).toBeInTheDocument();
  });

  it('resets the ticks behind a confirm', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    const reset = vi.spyOn(api, 'resetKit').mockResolvedValue({ ...kitWater, tiers: kitWater.tiers.map((t) => ({ ...t, done: 0, items: t.items.map((i) => ({ ...i, checked: false, updated_at: null })) })) });
    renderRoute('/kit/water');
    await screen.findByRole('heading', { level: 1, name: 'Water' });
    await act(async () => { screen.getByRole('button', { name: 'Reset ticks' }).click(); });
    await act(async () => { screen.getByRole('button', { name: 'Yes, reset' }).click(); });
    expect(reset).toHaveBeenCalledWith('water');
    expect(screen.getByRole('checkbox', { name: /Drinking water/ })).not.toBeChecked();
  });

  it('says when the kit cannot be loaded', async () => {
    vi.spyOn(api, 'kit').mockRejectedValue(new Error('gone'));
    renderRoute('/kit/water');
    expect(await screen.findByText(/Could not load this kit: gone/)).toBeInTheDocument();
  });
});
