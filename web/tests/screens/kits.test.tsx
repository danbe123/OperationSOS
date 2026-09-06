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
  it('lists relevant kits as tiles and the rest under Not needed', async () => {
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    renderRoute('/kit');
    expect(await screen.findByRole('heading', { level: 1, name: 'Kit' })).toBeInTheDocument();
    const grid = screen.getByRole('navigation', { name: 'Kits' });
    expect(within(grid).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/kit/water']);
    expect(within(grid).getByText('Basic 1/2 · Serious 0/1 · Full 0/1')).toBeInTheDocument();
    const rest = screen.getByRole('navigation', { name: 'Not needed for this household' });
    expect(within(rest).getByRole('link', { name: /Baby and child/ })).toHaveAttribute('href', '/kit/baby-child');
    expect(screen.getByText(/Ticks are shared/)).toBeInTheDocument();
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
