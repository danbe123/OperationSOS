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
    const numbers = screen.getByText(/Emergency/).closest('p') as HTMLElement;
    expect(numbers.textContent).toMatch(/999.*111.*105.*0345 988 1188/);
  });
  it('shows an error state', async () => {
    vi.spyOn(api, 'pages').mockRejectedValue(new Error('nope'));
    renderRoute('/radio');
    expect(await screen.findByText('Pages unavailable: nope')).toBeInTheDocument();
  });
});
