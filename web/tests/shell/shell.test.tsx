import { describe, it, expect, vi } from 'vitest';
import { screen, within, act, waitFor } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { condition, makeView, page, playbooks, powerOffView, view } from '../fixtures/api';
import { activeDestination, DESTINATIONS } from '../../src/shell/destinations';

describe('the shell', () => {
  it('carries the same five destinations, in the same order, on every screen', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    renderRoute('/');
    const nav = screen.getByRole('navigation', { name: 'Sections' });
    const list = nav.querySelector('.mainnav-list') as HTMLElement;
    expect(within(list).getAllByRole('link').map((a) => a.textContent)).toEqual(['Now', 'Guides', 'Medical', 'Map', 'Find']);
    expect(within(nav).getByRole('link', { name: 'Now' })).toHaveAttribute('aria-current', 'page');
    expect(within(nav).getByRole('link', { name: 'Guides' })).toHaveAttribute('href', '/guides');
    expect(within(nav).getByRole('link', { name: 'Find' })).toHaveAttribute('href', '/search');
  });

  it('lights the destination a screen belongs to', () => {
    expect(activeDestination('/s/grid-collapse')?.label).toBe('Guides');
    expect(activeDestination('/tools/timers')?.label).toBe('Guides');
    expect(activeDestination('/medical/card/cpr-adult')?.label).toBe('Medical');
    expect(activeDestination('/tasks')?.label).toBe('Now');
    expect(activeDestination('/library')?.label).toBe('Find');
    expect(activeDestination('/system')).toBeNull();
    expect(DESTINATIONS).toHaveLength(5);
  });

  it('gives each screen a title, Back to where you came from, and one theme button', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    const { router } = renderRoute('/p/pmr446');
    expect(await screen.findByRole('heading', { level: 1, name: 'PMR446 radio' })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('PMR446 radio · SOS'));
    expect(screen.getAllByRole('button', { name: /Theme: Vault/ })).toHaveLength(1);
    await act(async () => { screen.getByRole('button', { name: /Back/ }).click(); });
    expect(router.state.location.pathname).toBe('/');
  });
});

describe('the situation band', () => {
  it('carries what is wrong, the clock, the jobs and the way to the sheet', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      ...powerOffView,
      scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
    }));
    renderRoute('/p/pmr446');
    const band = await screen.findByRole('group', { name: 'Situation now' });
    const links = within(band).getAllByRole('link');
    expect(links.map((a) => a.textContent?.trim())).toEqual([
      expect.stringContaining('National grid collapse'), 'Power✕ off', 'Mobile▲ patchy', '▲ 3 to do', 'Situation',
    ]);
    expect(within(band).getByRole('link', { name: 'Mains power: off for 1 h' })).toHaveAttribute('href', '/situation#power');
    expect(within(band).getByRole('link', { name: 'Situation' })).toHaveAttribute('href', '/situation');
  });

  it('stays away while everything works', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('heading', { level: 1, name: 'PMR446 radio' })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Situation now' })).toBeNull();
  });

  it('is there on Now too: the band says the same thing on every screen', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue([]);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    expect(await screen.findByRole('group', { name: 'Situation now' })).toHaveTextContent('Power');
  });

  it('flies the drill flag on every screen', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({ meta: { ...view.meta, drill: true }, conditions: { power: condition('power', 'off') } as never }));
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('group', { name: 'Situation now' })).toHaveTextContent('Drill');
  });
});
