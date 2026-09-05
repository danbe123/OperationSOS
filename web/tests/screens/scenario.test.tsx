import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { splitModules } from '../../src/screens/Scenario';
import { playbook } from '../fixtures/api';

afterEach(() => vi.useRealTimers());

describe('splitModules', () => {
  it('splits on both marker forms, with or without a <p> wrapper', () => {
    expect(splitModules('<p>a</p><p>{{module:water}}</p><p>b</p><div data-module="power"></div>')).toEqual([
      '<p>a</p>', { module: 'water' }, '<p>b</p>', { module: 'power' },
    ]);
    expect(splitModules('<p>plain</p>')).toEqual(['<p>plain</p>']);
  });
});

describe('Scenario', () => {
  it('shows the six section tabs in order, Right now by default, with modules as accordions', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    renderRoute('/s/grid-collapse');
    const tabs = await screen.findByRole('tablist');
    expect(within(tabs).getAllByRole('tab').map((t) => t.textContent)).toEqual(['Right now', 'First 72 hours', 'First month', 'Long term', 'UK specifics', 'Go deeper']);
    expect(within(tabs).getByRole('tab', { name: 'Right now' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText(/Switch off the cooker/)).toBeInTheDocument();
    const water = screen.getByText('Water', { selector: 'summary' }).closest('details')!;
    expect(water).not.toHaveAttribute('open');
    expect(within(water).getByText('Store 3 litres per person per day.')).toBeInTheDocument();
    expect(screen.queryByText(/Keep the freezer shut: 48 hours/)).toBeNull();
  });

  it('tabs are reflected in ?tab= and the data-module marker form works', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    const user = userEvent.setup();
    const { router } = renderRoute('/s/grid-collapse');
    await user.click(await screen.findByRole('tab', { name: 'First 72 hours' }));
    expect(router.state.location.search).toBe('?tab=first-72-hours');
    expect(screen.getByText(/Keep the freezer shut: 48 hours/)).toBeInTheDocument();
    expect(screen.getByText('Power', { selector: 'summary' })).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'Go deeper' }));
    expect(screen.getByRole('link', { name: 'Electrical grid' })).toHaveAttribute('href', '/read/wikipedia_en_100_mini_2026-01/A/Electrical_grid');
    await user.click(screen.getByRole('tab', { name: 'Right now' }));
    expect(router.state.location.search).toBe('');
  });

  it('renders the shared checklist, sources with as-at dates and the reviewed date', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    renderRoute('/s/grid-collapse');
    expect(await screen.findByTestId('checklist-summary')).toHaveTextContent(/1 of 3 done/);
    expect(screen.getByText('National Risk Register 2025')).toBeInTheDocument();
    expect(screen.getByText(/as at 2025-01-16/)).toBeInTheDocument();
    expect(screen.getByText(/Reviewed 2026-09-10/)).toBeInTheDocument();
  });

  it('refetches every 15 s and on focus so ticks from other phones appear', async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    renderRoute('/s/grid-collapse');
    await act(async () => {});
    expect(spy).toHaveBeenCalledTimes(1);
    await act(async () => { vi.advanceTimersByTime(15_000); });
    expect(spy).toHaveBeenCalledTimes(2);
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    expect(spy).toHaveBeenCalledTimes(3);
  });

  it('hides Print in kiosk mode and shows it otherwise', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    const a = renderRoute('/s/grid-collapse', { kiosk: true });
    await screen.findByRole('tablist');
    expect(screen.queryByRole('button', { name: /Print/ })).toBeNull();
    a.unmount();
    renderRoute('/s/grid-collapse');
    await screen.findByRole('tablist');
    expect(screen.getByRole('button', { name: /Print/ })).toBeInTheDocument();
  });

  it('shows an error when the playbook is missing', async () => {
    vi.spyOn(api, 'playbook').mockRejectedValue(new Error('not found'));
    renderRoute('/s/nope');
    expect(await screen.findByText('Could not load this guide: not found')).toBeInTheDocument();
  });
});
