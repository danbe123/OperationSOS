import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { playbook } from '../fixtures/api';

describe('Situation clock', () => {
  it('starts the clock from the playbook and marks the current phase tab', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    vi.spyOn(api, 'situation').mockResolvedValue({ slug: null });
    const startedAt = new Date(Date.now() - 20 * 3600 * 1000).toISOString();
    const start = vi.spyOn(api, 'startSituation').mockResolvedValue({ slug: 'grid-collapse', title: 'National grid collapse', started_at: startedAt, elapsed_s: 72000, phase: 'first-72-hours' });
    renderRoute('/s/grid-collapse');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /Start the clock/ }));
    expect(start).toHaveBeenCalledWith('grid-collapse');
    // The slot that held Start now says how long it has been running and which phase that is; ending is behind it.
    expect(await screen.findByRole('status')).toHaveTextContent('20 h in');
    expect(screen.getByRole('button', { name: '20 h in, first 72 hours' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'End situation' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /20 h in/ }));
    expect(screen.getByRole('button', { name: 'End situation' })).toBeInTheDocument();
    expect(screen.getByText(/Started \d\d:\d\d/)).toBeInTheDocument();
    const tabs = screen.getByRole('tablist', { name: 'Sections' });
    const now = within(tabs).getByRole('tab', { name: /First 72 hours/ });
    expect(now).toHaveAttribute('aria-current', 'time');
    expect(now.querySelector('.tab-now')).not.toBeNull();   // a dot, not a badge: the tab row keeps its shape
    expect(within(tabs).getByRole('tab', { name: 'Right now' })).not.toHaveAttribute('aria-current');
  });

  it('asks before replacing another active situation and can end one', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    vi.spyOn(api, 'situation').mockResolvedValue({ slug: 'storms-flooding', title: 'Severe storms and flooding', started_at: new Date().toISOString(), elapsed_s: 10, phase: 'right-now' });
    const start = vi.spyOn(api, 'startSituation').mockResolvedValue({ slug: 'grid-collapse', title: 'National grid collapse', started_at: new Date().toISOString(), elapsed_s: 0, phase: 'right-now' });
    const end = vi.spyOn(api, 'endSituation').mockResolvedValue({ slug: null });
    renderRoute('/s/grid-collapse');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /Start the clock/ }));
    expect(start).not.toHaveBeenCalled();
    expect(screen.getByText(/replaces the situation that is running \(Severe storms and flooding\)/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(start).toHaveBeenCalledWith('grid-collapse');
    await user.click(await screen.findByRole('button', { name: /just started/ }));
    await user.click(screen.getByRole('button', { name: 'End situation' }));
    await user.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(end).toHaveBeenCalled();
    expect(await screen.findByRole('button', { name: /Start the clock/ })).toBeInTheDocument();
  });
});
