import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { nhsAtoZ } from '../../src/screens/Medical';
import { cards, library, nhsItem, nhsMedicinesItem, extItem } from '../fixtures/api';

describe('nhsAtoZ', () => {
  it('derives the conditions and medicines paths from the nhs_uk reader home', () => {
    expect(nhsAtoZ([nhsItem])).toEqual({ conditions: '/read/nhs_uk/www.nhs.uk/conditions/', medicines: '/read/nhs_uk/www.nhs.uk/medicines/', note: null });
  });
  it('falls back to the Kiwix medicines ZIM when nhs_uk is missing', () => {
    expect(nhsAtoZ([nhsMedicinesItem])).toEqual({ conditions: null, medicines: '/read/nhs_medicines/A/index', note: 'NHS conditions not installed' });
  });
  it('reports the drive label when nhs_uk is on a missing drive', () => {
    expect(nhsAtoZ([{ ...nhsItem, tier: 'extended', available: false, url: null, drive_label: 'On external drive (not connected)' }])).toEqual({ conditions: null, medicines: null, note: 'On external drive (not connected)' });
    expect(nhsAtoZ([extItem])).toEqual({ conditions: null, medicines: null, note: 'NHS not installed' });
  });
});

describe('Medical', () => {
  it('lists quick cards, NHS A to Z tiles and the medical library', async () => {
    vi.spyOn(api, 'cards').mockResolvedValue([...cards].reverse());
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/medical');
    const grid = await screen.findByRole('navigation', { name: 'Quick cards' });
    const links = within(grid).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/medical/card/cpr-adult', '/medical/card/severe-bleeding', '/medical/card/choking']);
    const nhs = await screen.findByRole('navigation', { name: 'NHS A to Z' });
    expect(within(nhs).getByRole('link', { name: /Conditions A to Z/ })).toHaveAttribute('href', '/read/nhs_uk/www.nhs.uk/conditions/');
    expect(within(nhs).getByRole('link', { name: /Medicines A to Z/ })).toHaveAttribute('href', '/read/nhs_uk/www.nhs.uk/medicines/');
    const lib = screen.getByRole('list', { name: 'Medical library' });
    expect(within(lib).getAllByRole('listitem')).toHaveLength(3);
  });

  it('greys the NHS tiles with the drive label when unavailable', async () => {
    vi.spyOn(api, 'cards').mockResolvedValue(cards);
    vi.spyOn(api, 'library').mockResolvedValue({ categories: [{ id: 'medical', title: 'Medical', items: [{ ...nhsItem, tier: 'extended', available: false, url: null, drive_label: 'On external drive (not connected)' }] }] });
    renderRoute('/medical');
    const nhs = await screen.findByRole('navigation', { name: 'NHS A to Z' });
    expect(within(nhs).queryAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/medical/dose']);   // the dose tool never depends on the drive
    expect(within(nhs).getAllByText('On external drive (not connected)')).toHaveLength(2);
  });
});

describe('Medical card groups', () => {
  it('groups the cards, the first minute first, and filters them by title or summary', async () => {
    vi.spyOn(api, 'cards').mockResolvedValue([...cards, { slug: 'new-card', title: 'Something new', icon: 'book', order: 40, html: '<p>x</p>' }]);
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/medical');
    const nav = await screen.findByRole('navigation', { name: 'Quick cards' });
    expect(within(nav).getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual(['The first minute', 'More cards']);
    const first = within(nav).getByRole('region', { name: 'The first minute' });
    expect(within(first).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/medical/card/cpr-adult', '/medical/card/severe-bleeding', '/medical/card/choking']);
    expect(within(first).getByText('Collapsed, unresponsive and not breathing normally.')).toBeInTheDocument();
    expect(within(first).getByRole('link', { name: /CPR \(adult\)/ })).toHaveClass('quick-card-urgent');
    expect(within(nav).getByRole('link', { name: /Something new/ })).not.toHaveClass('quick-card-urgent');
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(screen.getByRole('searchbox', { name: 'Find a card' }), { target: { value: 'soaks' } });
    expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/medical/card/severe-bleeding']);
    fireEvent.change(screen.getByRole('searchbox', { name: 'Find a card' }), { target: { value: 'zzz' } });
    expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
  });
});
