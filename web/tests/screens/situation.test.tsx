import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { playbook, playbooks, status } from '../fixtures/api';

describe('Situation clock', () => {
  it('starts the clock from the playbook and marks the current phase tab', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    vi.spyOn(api, 'situation').mockResolvedValue({ slug: null });
    const startedAt = new Date(Date.now() - 20 * 3600 * 1000).toISOString();
    const start = vi.spyOn(api, 'startSituation').mockResolvedValue({ slug: 'grid-collapse', title: 'National grid collapse', started_at: startedAt, elapsed_s: 72000, phase: 'first-72-hours' });
    renderRoute('/s/grid-collapse');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'This has started' }));
    expect(start).toHaveBeenCalledWith('grid-collapse');
    expect(await screen.findByRole('status')).toHaveTextContent('20 h in, first 72 hours');
    const tabs = screen.getByRole('tablist', { name: 'Sections' });
    const now = within(tabs).getByRole('tab', { name: /First 72 hours/ });
    expect(now).toHaveAttribute('aria-current', 'time');
    expect(within(now).getByText('now')).toBeInTheDocument();
    expect(within(tabs).getByRole('tab', { name: 'Right now' })).not.toHaveAttribute('aria-current');
  });

  it('asks before replacing another active situation and can end one', async () => {
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    vi.spyOn(api, 'situation').mockResolvedValue({ slug: 'storms-flooding', title: 'Severe storms and flooding', started_at: new Date().toISOString(), elapsed_s: 10, phase: 'right-now' });
    const start = vi.spyOn(api, 'startSituation').mockResolvedValue({ slug: 'grid-collapse', title: 'National grid collapse', started_at: new Date().toISOString(), elapsed_s: 0, phase: 'right-now' });
    const end = vi.spyOn(api, 'endSituation').mockResolvedValue({ slug: null });
    renderRoute('/s/grid-collapse');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'This has started' }));
    expect(start).not.toHaveBeenCalled();
    expect(screen.getByText(/replaces the active situation \(Severe storms and flooding\)/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm start' }));
    expect(start).toHaveBeenCalledWith('grid-collapse');
    await user.click(await screen.findByRole('button', { name: 'End situation' }));
    await user.click(screen.getByRole('button', { name: 'Confirm end' }));
    expect(end).toHaveBeenCalled();
    expect(await screen.findByRole('button', { name: 'This has started' })).toBeInTheDocument();
  });

  it('shows the active situation on Home', async () => {
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, situation: { slug: 'grid-collapse', started_at: new Date(Date.now() - 5 * 3600 * 1000).toISOString() } });
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    renderRoute('/');
    const card = await screen.findByRole('link', { name: /Active situation/ });
    expect(card).toHaveAttribute('href', '/s/grid-collapse');
    expect(card).toHaveTextContent('5 h in, right now');
    expect(card).toHaveTextContent('National grid collapse');
  });
});
