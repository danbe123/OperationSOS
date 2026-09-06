import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, within, act, waitFor } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { condition, makeView, page, playbooks, powerOffView, view, VIEW_NOW } from '../fixtures/api';
import { activeDestination, DESTINATIONS } from '../../src/shell/destinations';

describe('the shell', () => {
  it('carries the same six destinations, in the same order, on every screen', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    renderRoute('/');
    const nav = screen.getByRole('navigation', { name: 'Sections' });
    const list = nav.querySelector('.mainnav-list') as HTMLElement;
    expect(within(list).getAllByRole('link').map((a) => a.textContent)).toEqual(['Now', 'Guides', 'Kit', 'Medical', 'Map', 'Find']);
    expect(within(nav).getByRole('link', { name: 'Now' })).toHaveAttribute('aria-current', 'page');
    expect(within(nav).getByRole('link', { name: 'Guides' })).toHaveAttribute('href', '/guides');
    expect(within(nav).getByRole('link', { name: 'Kit' })).toHaveAttribute('href', '/kit');
    expect(within(nav).getByRole('link', { name: 'Find' })).toHaveAttribute('href', '/search');
  });

  it('lights the destination a screen belongs to', () => {
    expect(activeDestination('/s/grid-collapse')?.label).toBe('Guides');
    expect(activeDestination('/tools/timers')?.label).toBe('Guides');
    expect(activeDestination('/medical/card/cpr-adult')?.label).toBe('Medical');
    expect(activeDestination('/tasks')?.label).toBe('Now');
    expect(activeDestination('/library')?.label).toBe('Find');
    expect(activeDestination('/kit/water')?.label).toBe('Kit');
    expect(activeDestination('/system')).toBeNull();
    expect(DESTINATIONS).toHaveLength(6);
  });

  it('gives each screen a title, Back to where you came from, and one theme button', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    const { router } = renderRoute('/p/pmr446');
    expect(await screen.findByRole('heading', { level: 1, name: 'PMR446 radio' })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('PMR446 radio · SOS'));
    expect(screen.getAllByRole('button', { name: /Change the theme. Vault now/ })).toHaveLength(1);
    await act(async () => { screen.getByRole('button', { name: /Back/ }).click(); });
    expect(router.state.location.pathname).toBe('/');
  });
});

describe('the situation band', () => {
  beforeEach(() => vi.useFakeTimers({ now: Date.parse(VIEW_NOW), toFake: ['Date'] }));
  afterEach(() => vi.useRealTimers());

  it('carries what is wrong, the clock, the jobs and the way to the sheet, in one row', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      ...powerOffView,
      scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
    }));
    renderRoute('/p/pmr446');
    const band = await screen.findByRole('group', { name: 'Situation now' });
    const links = within(band).getAllByRole('link');
    // One row at every width: on a phone with a scenario running there is no room for a chip, so
    // the two conditions fold into one control that says how many and opens the sheet. The count
    // of jobs is not dressed as a condition.
    expect(links.map((a) => a.textContent?.trim())).toEqual([
      expect.stringContaining('National grid collapse'), '2 things off', '3 to do', 'Situation',
    ]);
    expect(within(band).getByRole('link', { name: '2 things off' })).toHaveAttribute('href', '/situation');
    expect(within(band).getByRole('link', { name: 'Situation' })).toHaveAttribute('href', '/situation');
  });

  it('shows the chips it has room for on the kiosk, and folds the rest', async () => {
    const narrow = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes('min-width: 700px'), media: query, addEventListener: () => {}, removeEventListener: () => {},
    })) as unknown as typeof window.matchMedia;
    try {
      vi.spyOn(api, 'page').mockResolvedValue(page);
      vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
        ...powerOffView,
        scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
      }));
      renderRoute('/p/pmr446');
      const band = await screen.findByRole('group', { name: 'Situation now' });
      // The band says how long, counted from the instant the box stored.
      expect(within(band).getByRole('link', { name: 'Mains power: off for 1 h' })).toHaveAttribute('href', '/situation#power');
      expect(within(band).getByRole('link', { name: '+1 more' })).toHaveAttribute('href', '/situation');
      expect(within(band).queryByRole('link', { name: /Mobile network/ })).toBeNull();
    } finally {
      window.matchMedia = narrow;
    }
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
    // On a phone the band carries the count; Now's own heading names the services.
    expect(await screen.findByRole('group', { name: 'Situation now' })).toHaveTextContent('2 things off');
  });

  it('flies the drill flag on every screen', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({ meta: { ...view.meta, drill: true }, conditions: { power: condition('power', 'off') } as never }));
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('group', { name: 'Situation now' })).toHaveTextContent('Drill');
  });
});
