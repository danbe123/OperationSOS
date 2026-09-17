import { describe, it, expect, vi } from 'vitest';
import { screen, within, act } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { kitWater } from '../fixtures/api';

describe('Kit', () => {
  it('shows the three tiers as one switch with the first unpacked tier open, the quantities and the ticks', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    renderRoute('/kit/water');
    expect(await screen.findByRole('heading', { level: 1, name: 'Water' })).toBeInTheDocument();
    const tabs = screen.getByRole('tablist', { name: 'Tiers' });
    expect(within(tabs).getAllByRole('tab').map((t) => t.textContent)).toEqual(['Three days1 of 2', 'Two weeks0 of 1', 'No help coming0 of 1']);
    expect(within(tabs).getByRole('tab', { name: /Three days/ })).toHaveAttribute('aria-selected', 'true');
    const basic = screen.getByRole('tabpanel', { name: /Three days/ });
    expect(screen.queryByRole('tabpanel', { name: /Two weeks/ })).toBeNull();   // hidden until picked; on the page for the printer
    expect(screen.getByText('1 of 4 packed.')).toBeInTheDocument();
    expect(within(basic).getByText('18 L for 2 people over 3 days')).toBeInTheDocument();
    expect(within(basic).getByRole('link', { name: 'Water module: Drinking water in sealed containers' })).toHaveAttribute('href', '/m/water');
    expect(within(basic).getByRole('checkbox', { name: /Drinking water/ })).toBeChecked();
    // Nothing is handed off into a cupboard the box no longer keeps.
    expect(screen.queryByText(/in Stock/)).toBeNull();
    expect(screen.queryByRole('button', { name: /Add to Stock/ })).toBeNull();
  });

  it('says who the quantities are for, and sends that question back to the kit list', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    renderRoute('/kit/water');
    await screen.findByRole('heading', { level: 1, name: 'Water' });
    const quantities = screen.getByText(/Quantities are for/);
    // The number is the setting, and the way to change it is the stepper on the kit list.
    expect(within(quantities).getByRole('link', { name: '2 people' })).toHaveAttribute('href', '/kit');
    expect(quantities).not.toHaveTextContent('register');
  });

  it('puts the list first and the reasoning under it, and links a citation inside a why', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    renderRoute('/kit/water');
    await screen.findByRole('heading', { level: 1, name: 'Water' });
    const quantities = screen.getByText(/Quantities are for/);
    const basic = screen.getByRole('tabpanel', { name: /Three days/ });
    const full = document.getElementById('tier-full')!;   // on the page for the printer, hidden until picked
    const why = screen.getByRole('heading', { level: 2, name: 'Why these things' });
    // The sentence about who the quantities are for stays above the first tier; the intro moves below the last.
    expect(quantities.compareDocumentPosition(basic) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(full.compareDocumentPosition(why) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText('Three litres a person a day is the planning figure.')).toBeInTheDocument();
    // A why is inline HTML, so its citation is a link on the row rather than raw Markdown.
    expect(within(basic).getByRole('link', { name: 'Prepare' })).toHaveAttribute('href', '/read/prepare_uk/prepare');
    expect(within(basic).queryByText(/\[Prepare\]/)).toBeNull();
    expect(within(basic).getByText('Rotate every year.')).toBeInTheDocument();
  });

  it('ticks an item, and sends the box the tick and nothing else', async () => {
    vi.spyOn(api, 'kit').mockResolvedValue(kitWater);
    const ticked = { ...kitWater, tiers: kitWater.tiers.map((t) => t.id !== 'serious' ? t : { ...t, done: 1, items: t.items.map((i) => ({ ...i, checked: true, updated_at: '2026-09-06T11:00:00+00:00' })) }) };
    const set = vi.spyOn(api, 'setKitItem').mockResolvedValue(ticked);
    renderRoute('/kit/water');
    const tabs = await screen.findByRole('tablist', { name: 'Tiers' });
    await act(async () => { within(tabs).getByRole('tab', { name: /Two weeks/ }).click(); });
    const serious = screen.getByRole('tabpanel', { name: /Two weeks/ });
    expect(screen.queryByRole('tabpanel', { name: /Three days/ })).toBeNull();
    const box = within(serious).getByRole('checkbox', { name: /Water purification tablets/ });
    await act(async () => { box.click(); });
    expect(set).toHaveBeenCalledWith('water', 'tablets', { checked: true });
    expect(within(serious).getByRole('checkbox', { name: /Water purification tablets/ })).toBeChecked();
    expect(within(serious).queryByRole('button', { name: /Add to Stock/ })).toBeNull();
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
