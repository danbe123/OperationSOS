import { describe, it, expect, vi } from 'vitest';
import { act, screen, waitFor, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { kitsResponse, kitWater } from '../fixtures/api';
import { tierLine } from '../../src/screens/Kits';

describe('tierLine', () => {
  it('reads basic, serious and full as done over total', () => {
    expect(tierLine(kitsResponse.kits[0].tiers)).toBe('Basic 1/2 · Serious 0/1 · Full 0/1');
  });
});

describe('Kits', () => {
  it('lists every kit as a tile, with nothing set aside as not needed', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    renderRoute('/kit');
    expect(await screen.findByRole('heading', { level: 1, name: 'Kit' })).toBeInTheDocument();
    const grid = screen.getByRole('navigation', { name: 'Kits' });
    expect(within(grid).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/kit/water', '/kit/baby-child']);
    expect(within(grid).getByText('Basic 1/2 · Serious 0/1 · Full 0/1')).toBeInTheDocument();
    // Without a register there is nothing to test a kit against, so no kit is put in a "not needed" pile.
    expect(screen.queryByRole('navigation', { name: 'Not needed for this household' })).toBeNull();
    expect(screen.queryByText(/register/i)).toBeNull();
    expect(screen.getByText(/Ticks are shared/)).toBeInTheDocument();
  });

  it('is the one thing the box asks: how many people, on a stepper that saves and re-scales', async () => {
    const kits = vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    const setPeople = vi.spyOn(api, 'setPeople').mockResolvedValue({ people: 3 });
    renderRoute('/kit');
    const stepper = await screen.findByRole('group', { name: 'How many people' });
    expect(stepper).toHaveTextContent('For 2 people');
    kits.mockResolvedValue({ ...kitsResponse, people: 3 });
    await act(async () => { within(stepper).getByRole('button', { name: 'More' }).click(); });
    expect(setPeople).toHaveBeenCalledWith(3);
    // The quantities on every kit come from the box, so the list is read again rather than guessed at.
    await waitFor(() => expect(kits).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/For 3 people/)).toBeInTheDocument();
  });

  it('never asks the box for nobody, and says the count in words a person reads', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue({ ...kitsResponse, people: 1 });
    const setPeople = vi.spyOn(api, 'setPeople').mockResolvedValue({ people: 1 });
    renderRoute('/kit');
    const stepper = await screen.findByRole('group', { name: 'How many people' });
    expect(stepper).toHaveTextContent('For 1 person');
    expect(within(stepper).getByRole('button', { name: 'Fewer' })).toBeDisabled();
    await act(async () => { within(stepper).getByRole('button', { name: 'Fewer' }).click(); });
    expect(setPeople).not.toHaveBeenCalled();
  });

  it('says so when the count cannot be saved, and keeps the number the box last gave', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    vi.spyOn(api, 'setPeople').mockRejectedValue(new Error('boom'));
    renderRoute('/kit');
    const stepper = await screen.findByRole('group', { name: 'How many people' });
    await act(async () => { within(stepper).getByRole('button', { name: 'More' }).click(); });
    expect(await screen.findByText(/Could not save how many people: boom/)).toBeInTheDocument();
    expect(await screen.findByText(/For 2 people/)).toBeInTheDocument();
  });

  it('offers Print every kit only once there are kits to print', async () => {
    let release: (r: typeof kitsResponse) => void = () => {};
    vi.spyOn(api, 'kits').mockReturnValue(new Promise((resolve) => { release = resolve; }));
    const kit = vi.spyOn(api, 'kit').mockImplementation(async (slug) => ({ ...kitWater, slug, title: slug }));
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    renderRoute('/kit');
    const button = await screen.findByRole('button', { name: /Print every kit/ });
    // Nothing has arrived: the button used to sit there live and do nothing at all when tapped.
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-disabled', 'true');
    await act(async () => { button.click(); });
    expect(kit).not.toHaveBeenCalled();

    await act(async () => { release(kitsResponse); });
    await waitFor(() => expect(button).toBeEnabled());
    expect(button).toHaveAttribute('aria-disabled', 'false');
    await act(async () => { button.click(); });
    expect(kit).toHaveBeenCalledTimes(kitsResponse.kits.length);
    await waitFor(() => expect(print).toHaveBeenCalled());
    print.mockRestore();
  });

  it('says when kits cannot be loaded', async () => {
    vi.spyOn(api, 'kits').mockRejectedValue(new Error('boom'));
    renderRoute('/kit');
    expect(await screen.findByText(/Kits unavailable: boom/)).toBeInTheDocument();
  });
});
