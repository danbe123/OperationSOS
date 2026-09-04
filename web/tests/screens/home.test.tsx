import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { playbooks } from '../fixtures/api';

describe('Home', () => {
  it('shows the five big tiles in order, the 20 scenario tiles with icons, and the status strip', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue([...playbooks].reverse());
    renderRoute('/');
    const main = screen.getByRole('navigation', { name: 'Main sections' });
    const bigTitles = within(main).getAllByRole('link').map((a) => a.textContent?.trim());
    expect(bigTitles).toEqual(['MedicalQuick cards, NHS', 'MapsUK and Ireland, offline', 'LibraryWikipedia, manuals, books', 'Phone and radioNumbers, PMR446, what works', 'PlanHousehold plan, notes, pins']);
    expect(within(main).getByRole('link', { name: /Maps/ })).toHaveAttribute('href', '/map');
    expect(within(main).getByRole('link', { name: /Phone and radio/ })).toHaveAttribute('href', '/radio');
    const grid = await screen.findByRole('navigation', { name: 'Scenarios' });
    const tiles = within(grid).getAllByRole('link');
    expect(tiles).toHaveLength(20);
    expect(tiles[0]).toHaveTextContent('Nuclear war');
    expect(tiles[0]).toHaveAttribute('href', '/s/nuclear-war');
    expect(tiles[19]).toHaveTextContent('The long rebuild');
    expect(tiles[0].querySelector('svg.icon')).not.toBeNull();
    expect(screen.getByRole('heading', { name: 'What is happening?' })).toBeInTheDocument();
    expect(await screen.findByTestId('status-strip')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Search' })).toBeInTheDocument();
  });

  it('shows an error line when playbooks fail to load', async () => {
    vi.spyOn(api, 'playbooks').mockRejectedValue(new Error('boom'));
    renderRoute('/');
    expect(await screen.findByText('Playbooks unavailable: boom')).toBeInTheDocument();
  });
});
