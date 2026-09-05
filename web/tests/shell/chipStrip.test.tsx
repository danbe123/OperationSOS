import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { condition, makeView, page, playbook, powerOffView, view } from '../fixtures/api';

describe('The chrome chip strip', () => {
  it('carries what is wrong, the clock and the way back on a content screen', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      ...powerOffView,
      scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
    }));
    renderRoute('/p/pmr446');
    const strip = await screen.findByRole('group', { name: 'Situation now' });
    const chips = within(strip).getAllByRole('link');
    expect(chips.map((a) => a.textContent?.trim())).toEqual([
      expect.stringContaining('National grid collapse'), 'Power✕ off', 'Mobile▲ patchy', '3 to do', 'Situation',
    ]);
    expect(within(strip).getByRole('link', { name: 'Mains power: off for 1 h' })).toHaveAttribute('href', '/situation#power');
    expect(within(strip).getByRole('link', { name: 'Situation' })).toHaveAttribute('href', '/situation');
  });

  it('stays away while everything works, and off Home and the sheet', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('heading', { name: 'PMR446 radio' })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Situation now' })).toBeNull();
  });

  it('is not repeated on Home, which shows the whole strip', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue([]);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    await screen.findByRole('region', { name: 'Situation' });
    expect(screen.queryByRole('group', { name: 'Situation now' })).toBeNull();
  });

  it('flies the drill flag on every screen', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({ meta: { ...view.meta, drill: true }, conditions: { power: condition('power', 'off') } as never }));
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('group', { name: 'Situation now' })).toHaveTextContent('DRILL');
  });
});

describe('When the phones are down', () => {
  it('warns once on a content screen and points at the alternatives', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      conditions: { mobile: condition('mobile', 'off'), landline: condition('landline', 'off') } as never,
      modes: { ...view.modes, calls: 'hidden' },
    }));
    renderRoute('/p/pmr446');
    const notice = await screen.findByRole('status');
    expect(notice).toHaveTextContent('Phone numbers on this page will not connect');
    expect(within(notice).getByRole('link', { name: 'Getting help without phones' })).toHaveAttribute('href', '/p/no-phones');
  });

  it('says nothing while the calls mode is shown', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/s/grid-collapse');
    expect(await screen.findByRole('heading', { name: 'Do this first' })).toBeInTheDocument();
    expect(screen.queryByText(/will not connect/)).toBeNull();
  });
});
