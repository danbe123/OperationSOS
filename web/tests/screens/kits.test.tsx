import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { kitsResponse } from '../fixtures/api';
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

  it('says when kits cannot be loaded', async () => {
    vi.spyOn(api, 'kits').mockRejectedValue(new Error('boom'));
    renderRoute('/kit');
    expect(await screen.findByText(/Kits unavailable: boom/)).toBeInTheDocument();
  });
});
