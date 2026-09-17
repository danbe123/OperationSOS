import { describe, it, expect, vi } from 'vitest';
import { act, screen, waitFor, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { kitsHave, kitsResponse, kitWater } from '../fixtures/api';
import { kitStatus } from '../../src/screens/Kits';

describe('kitStatus', () => {
  it('says which tier is being worked on and how far, in the words a household uses', () => {
    expect(kitStatus(kitsResponse.kits[0].tiers)).toBe('Three days: 1 of 2');
    expect(kitStatus({ basic: { done: 2, total: 2 }, serious: { done: 1, total: 3 }, full: { done: 0, total: 1 } })).toBe('Three days ✓ · Two weeks: 1 of 3');
    expect(kitStatus({ basic: { done: 2, total: 2 }, serious: { done: 3, total: 3 }, full: { done: 0, total: 1 } })).toBe('Two weeks ✓ · No help coming: 0 of 1');
    expect(kitStatus({ basic: { done: 2, total: 2 }, serious: { done: 3, total: 3 }, full: { done: 1, total: 1 } })).toBe('Everything packed');
    // a kit with no serious or full tier is judged on what it has
    expect(kitStatus({ basic: { done: 1, total: 1 }, serious: { done: 0, total: 0 }, full: { done: 0, total: 0 } })).toBe('Everything packed');
  });
});

describe('Kits', () => {
  it('lists every kit as a tile, with nothing set aside as not needed', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    renderRoute('/kit');
    expect(await screen.findByRole('heading', { level: 1, name: 'Kit' })).toBeInTheDocument();
    const grid = screen.getByRole('navigation', { name: 'Kits' });
    expect(within(grid).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/kit/water', '/kit/baby-child']);
    expect(within(grid).getByText('Three days: 1 of 2')).toBeInTheDocument();
    // where the whole house stands, one bar a tier, over the tiles
    const ready = screen.getByRole('region', { name: 'How ready you are' });
    expect(within(ready).getByRole('progressbar', { name: 'Three days: 1 of 3 packed' })).toBeInTheDocument();
    expect(within(ready).getByRole('progressbar', { name: 'Two weeks: 0 of 1 packed' })).toBeInTheDocument();
    expect(within(ready).getByRole('progressbar', { name: 'No help coming: 0 of 1 packed' })).toBeInTheDocument();
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

  it('keeps the stepper and the kit tiles on the Kits tab, with Kits the tab that is open', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    const have = vi.spyOn(api, 'kitsHave').mockResolvedValue(kitsHave);
    renderRoute('/kit');
    const tabs = await screen.findByRole('tablist', { name: 'Kit' });
    expect(within(tabs).getByRole('tab', { name: 'Kits' })).toHaveAttribute('aria-selected', 'true');
    expect(within(tabs).getByRole('tab', { name: 'What you have' })).toHaveAttribute('aria-selected', 'false');
    expect(screen.getByRole('group', { name: 'How many people' })).toHaveTextContent('For 2 people');
    expect(screen.getByRole('navigation', { name: 'Kits' })).toBeInTheDocument();
    // The other tab is not read until it is opened: the overview is one request, as it always was.
    expect(have).not.toHaveBeenCalled();
  });

  it('shows every ticked thing on the What you have tab, kit by kit, with its quantity', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    vi.spyOn(api, 'kitsHave').mockResolvedValue(kitsHave);
    const { router } = renderRoute('/kit');
    const tab = await screen.findByRole('tab', { name: 'What you have' });
    await act(async () => { tab.click(); });
    expect(await screen.findByRole('heading', { name: 'What you have marked' })).toBeInTheDocument();
    // The tab is the hash, so this screen can be linked to and comes back where it was left.
    expect(router.state.location.hash).toBe('#have');
    expect(screen.queryByRole('group', { name: 'How many people' })).toBeNull();
    expect(screen.getByText(/For 2 people/)).toBeInTheDocument();

    const [water, baby] = screen.getAllByRole('table');
    expect(screen.getByRole('link', { name: /Water/ })).toHaveAttribute('href', '/kit/water');
    expect(within(water).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Item', 'Quantity']);
    expect(within(water).getAllByRole('row').slice(1).map((r) => within(r).getAllByRole('cell').map((c) => c.textContent)))
      .toEqual([['18 L for 2 people over 3 days'], ['1 pack']]);
    expect(within(water).getByRole('rowheader', { name: /Drinking water in sealed containers/ })).toHaveTextContent('basic');
    expect(within(water).getByRole('rowheader', { name: /Water purification tablets/ })).toHaveTextContent('serious');
    expect(within(baby).getByRole('rowheader', { name: /Nappies/ })).toBeInTheDocument();
    expect(within(baby).getByRole('cell', { name: '36 for 2 people over 3 days' })).toBeInTheDocument();
    expect(screen.getByText('3 items across 2 kits')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Print$/ })).toBeInTheDocument();
  });

  it('opens on What you have when the link carries the hash', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    vi.spyOn(api, 'kitsHave').mockResolvedValue(kitsHave);
    renderRoute('/kit#have');
    expect(await screen.findByRole('heading', { name: 'What you have marked' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'What you have' })).toHaveAttribute('aria-selected', 'true');
  });

  it('says what to do when nothing is ticked, and links back to the kits', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    vi.spyOn(api, 'kitsHave').mockResolvedValue({ people: 2, kits: [] });
    renderRoute('/kit#have');
    expect(await screen.findByText(/Nothing ticked yet\. Open a kit and tick what you have\./)).toBeInTheDocument();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.queryByText(/items across/)).toBeNull();
    const back = screen.getByRole('link', { name: 'Back to the kits' });
    expect(back).toHaveAttribute('href', '/kit');
    await act(async () => { back.click(); });
    expect(await screen.findByRole('group', { name: 'How many people' })).toBeInTheDocument();
  });

  it('says when what you have cannot be loaded', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    vi.spyOn(api, 'kitsHave').mockRejectedValue(new Error('boom'));
    renderRoute('/kit#have');
    expect(await screen.findByText(/What you have is unavailable: boom/)).toBeInTheDocument();
  });

  it('says when kits cannot be loaded', async () => {
    vi.spyOn(api, 'kits').mockRejectedValue(new Error('boom'));
    renderRoute('/kit');
    expect(await screen.findByText(/Kits unavailable: boom/)).toBeInTheDocument();
  });
});
