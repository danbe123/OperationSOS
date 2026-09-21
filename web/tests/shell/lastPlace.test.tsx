import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { playbooks } from '../fixtures/api';
import {
  LAST_PLACE_KEY, LAST_PLACE_MAX_AGE_MS, forgetPlace, isWorthRemembering, noteScreenTitle, readPlace, rememberPlace,
} from '../../src/shell/lastPlace';

const NOW = Date.UTC(2026, 8, 21, 12, 0, 0);
afterEach(() => vi.restoreAllMocks());

describe('what is worth coming back to', () => {
  it('is a place to work in, not the front door, the board, the settings or the assistant', () => {
    for (const path of ['/s/grid-collapse', '/s/grid-collapse?tab=first-72-hours', '/m/water', '/p/no-phones', '/medical/card/cpr-adult',
      '/kit/water', '/library/books', '/map?lat=50.9&lon=-1.4', '/notes', '/situation', '/tasks', '/tools/timers',
      '/doc/nrr-2025', '/read/wikipedia/A/Water', '/search?q=bleeding']) {
      expect(isWorthRemembering(path), path).toBe(true);
    }
    for (const path of ['/', '/now', '/board', '/system', '/ai', '/ai?q=x', '/search', '/search?q=', '/starting', '/nowhere-at-all']) {
      expect(isWorthRemembering(path), path).toBe(false);
    }
  });
});

describe('the last place, kept in the browser', () => {
  it('remembers where and when, and gives it back for twelve hours', () => {
    rememberPlace('/s/grid-collapse?tab=first-72-hours', NOW);
    expect(readPlace(NOW + 60_000)).toMatchObject({ path: '/s/grid-collapse?tab=first-72-hours', at: NOW });
    expect(readPlace(NOW + LAST_PLACE_MAX_AGE_MS - 1)).not.toBeNull();
    expect(readPlace(NOW + LAST_PLACE_MAX_AGE_MS)).toBeNull();
  });

  it('does not store the front door or a transient screen, and leaves the old place alone when it is not given a new one', () => {
    rememberPlace('/s/grid-collapse', NOW);
    rememberPlace('/', NOW + 1000);
    rememberPlace('/board', NOW + 2000);
    expect(readPlace(NOW + 3000)?.path).toBe('/s/grid-collapse');
  });

  it('knows the title of the screen it is on, only for that screen', () => {
    rememberPlace('/s/grid-collapse', NOW);
    noteScreenTitle('/s/other', 'Some other screen', NOW);
    expect(readPlace(NOW)?.title).toBeUndefined();
    noteScreenTitle('/s/grid-collapse', 'National grid collapse', NOW);
    expect(readPlace(NOW)?.title).toBe('National grid collapse');
  });

  it('can be forgotten', () => {
    rememberPlace('/s/grid-collapse', NOW);
    forgetPlace();
    expect(readPlace(NOW)).toBeNull();
    expect(localStorage.getItem(LAST_PLACE_KEY)).toBeNull();
  });

  it('survives storage that is not there, and a damaged entry', () => {
    localStorage.setItem(LAST_PLACE_KEY, '{not json');
    expect(readPlace(NOW)).toBeNull();
    localStorage.setItem(LAST_PLACE_KEY, JSON.stringify({ path: 'https://evil.example/', at: NOW }));
    expect(readPlace(NOW)).toBeNull();   // only a path in this app is ever offered
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota'); });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('denied'); });
    expect(() => rememberPlace('/s/x', NOW)).not.toThrow();
    expect(readPlace(NOW)).toBeNull();
    expect(() => forgetPlace()).not.toThrow();
  });
});

describe('Continue where you were, on Now', () => {
  function withPlaybooks() {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
  }
  const chipName = /Continue where you were/;

  it('is offered on a cold start when the last place is recent, and goes there when tapped', async () => {
    withPlaybooks();
    rememberPlace('/s/grid-collapse', Date.now() - 30 * 60_000);
    noteScreenTitle('/s/grid-collapse', 'National grid collapse');
    const user = userEvent.setup();
    const { router } = renderRoute('/');
    const chip = await screen.findByRole('link', { name: chipName });
    expect(chip).toHaveAttribute('href', '/s/grid-collapse');
    expect(chip).toHaveTextContent('National grid collapse');
    expect(router.state.location.pathname).toBe('/');   // never a redirect
    await user.click(chip);
    expect(router.state.location.pathname).toBe('/s/grid-collapse');
  });

  it('is not offered when there is nothing recent to go back to', async () => {
    withPlaybooks();
    rememberPlace('/s/grid-collapse', Date.now() - LAST_PLACE_MAX_AGE_MS - 60_000);
    renderRoute('/');
    await screen.findByRole('heading', { level: 1, name: "What's the situation?" });
    expect(screen.queryByRole('link', { name: chipName })).toBeNull();
  });

  it('can be dismissed, and stays dismissed', async () => {
    withPlaybooks();
    rememberPlace('/s/grid-collapse', Date.now() - 60_000);
    const user = userEvent.setup();
    const first = renderRoute('/');
    await screen.findByRole('link', { name: chipName });
    await user.click(screen.getByRole('button', { name: /Dismiss/ }));
    expect(screen.queryByRole('link', { name: chipName })).toBeNull();
    expect(readPlace(Date.now())).toBeNull();
    first.unmount();
    renderRoute('/');
    await screen.findByRole('heading', { level: 1, name: "What's the situation?" });
    expect(screen.queryByRole('link', { name: chipName })).toBeNull();
  });

  it('is never offered after an ordinary in-app navigation to Now', async () => {
    withPlaybooks();
    const user = userEvent.setup();
    const { router } = renderRoute('/s/grid-collapse');
    await screen.findByRole('navigation', { name: 'Sections' });
    await act(async () => { await router.navigate('/'); });
    await screen.findByRole('heading', { level: 1, name: "What's the situation?" });
    expect(screen.queryByRole('link', { name: chipName })).toBeNull();
    // and going there by the rail after being somewhere else is the same
    await user.click(within(screen.getByRole('navigation', { name: 'Sections' })).getByRole('link', { name: 'Library' }));
    await user.click(within(screen.getByRole('navigation', { name: 'Sections' })).getByRole('link', { name: 'Now' }));
    expect(screen.queryByRole('link', { name: chipName })).toBeNull();
  });

  it('is recorded as the person moves about', async () => {
    withPlaybooks();
    const { router } = renderRoute('/');
    await screen.findByRole('heading', { level: 1, name: "What's the situation?" });
    await act(async () => { await router.navigate('/s/grid-collapse?tab=first-month'); });
    expect(readPlace(Date.now())?.path).toBe('/s/grid-collapse?tab=first-month');
    await act(async () => { await router.navigate('/'); });
    expect(readPlace(Date.now())?.path).toBe('/s/grid-collapse?tab=first-month');   // going home does not forget where they were
  });
});
