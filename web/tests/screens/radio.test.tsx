import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { pages } from '../fixtures/api';

describe('Radio', () => {
  it('lists the comms pages in order with the emergency numbers line', async () => {
    vi.spyOn(api, 'pages').mockResolvedValue([...pages].reverse());
    renderRoute('/radio');
    const nav = await screen.findByRole('navigation', { name: 'Comms pages' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/p/pmr446', '/p/uk-numbers', '/p/what-still-works']);
    const numbers = screen.getByRole('region', { name: 'Numbers to ring' });
    expect(numbers.textContent).toMatch(/999.*111.*105.*0345 988 1188/);
    // One 999 line, the same on every screen that carries one.
    expect(screen.getByText(/Life-threatening emergency/)).toBeInTheDocument();
  });
  it('shows an error state', async () => {
    vi.spyOn(api, 'pages').mockRejectedValue(new Error('nope'));
    renderRoute('/radio');
    expect(await screen.findByText('Pages unavailable: nope')).toBeInTheDocument();
  });
});
