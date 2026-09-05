import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { condition, makeView, playbooks, powerOffView, view } from '../fixtures/api';

describe('The situation sheet', () => {
  it('lists all ten conditions with three states each, and a print link', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'Conditions' });
    expect(within(rows).getAllByRole('listitem')).toHaveLength(10);
    const power = within(rows).getByRole('group', { name: 'Mains power' });
    expect(within(power).getAllByRole('button').map((b) => b.textContent?.trim())).toEqual(['✓ Working', '▲ Patchy', '✕ Off']);
    expect(within(power).getByRole('button', { name: /Working/ })).toHaveAttribute('aria-pressed', 'true');
    expect(within(rows).getByRole('group', { name: 'Sewage and drains' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Print report' })).toHaveAttribute('href', '/api/situation/report');
    expect(screen.getByRole('link', { name: 'Print report' })).toHaveAttribute('target', '_blank');
  });

  it('sets a state with the chosen since time and the row it was based on', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const set = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('Mains power: since'), 'hour');
    await user.click(within(screen.getByRole('group', { name: 'Mains power' })).getByRole('button', { name: /Off/ }));
    expect(set).toHaveBeenCalledTimes(1);
    const [id, body] = set.mock.calls[0];
    expect(id).toBe('power');
    expect(body.state).toBe('off');
    expect(body.expected_updated_at).toBe(view.conditions.power.updated_at);
    expect(Date.now() - Date.parse(body.since as string)).toBeGreaterThan(3_500_000);
  });

  it('says who set it and offers Confirm when a state has gone stale', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      conditions: { power: condition('power', 'off', { stale: true, for_s: 90_000, set_by: 'kiosk', updated_at: '2026-09-05T10:00:00.000Z' }) } as never,
    }));
    const confirm = vi.spyOn(api, 'confirmCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const row = (await screen.findByRole('region', { name: 'Conditions' })).querySelector('#power') as HTMLElement;
    expect(row).toHaveTextContent('Set from kiosk at');
    expect(within(row).getByRole('status')).toHaveTextContent('Still off?');
    await userEvent.setup().click(within(row).getByRole('button', { name: 'Confirm, still off' }));
    expect(confirm).toHaveBeenCalledWith('power');
  });

  it('warns instead of overwriting when another phone got there first', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'setCondition').mockRejectedValue(new ApiError(409, 'conflict'));
    renderRoute('/situation');
    await userEvent.setup().click(within(await screen.findByRole('group', { name: 'Water supply' })).getByRole('button', { name: /Off/ }));
    expect(await screen.findByText(/Water supply was changed on another device/)).toBeInTheDocument();
  });

  it('starts and ends the clock', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const start = vi.spyOn(api, 'startSituation').mockResolvedValue({ slug: 'grid-collapse', title: 'National grid collapse', started_at: new Date().toISOString(), elapsed_s: 0, phase: 'right-now' });
    renderRoute('/situation');
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('Situation to start'), 'grid-collapse');
    await user.click(screen.getByRole('button', { name: 'Start the clock' }));
    expect(start).toHaveBeenCalledWith('grid-collapse');
  });

  it('runs a drill and ends it', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const drilling = makeView({ meta: { ...view.meta, drill: true }, conditions: { power: condition('power', 'off') } as never });
    const start = vi.spyOn(api, 'startDrill').mockResolvedValue(drilling);
    const end = vi.spyOn(api, 'endDrill').mockResolvedValue(view);
    renderRoute('/situation');
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('Drill scenario'), 'grid-collapse');
    await user.selectOptions(screen.getByLabelText('Drill started'), '12');
    await user.click(screen.getByRole('button', { name: 'Start drill' }));
    expect(start).toHaveBeenCalledWith({ scenario: 'grid-collapse', conditions: { power: 'off' }, hours_ago: 12 });
    expect(await screen.findByText(/Drill in progress/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'End drill' }));
    expect(end).toHaveBeenCalled();
  });

  it('opens at the condition the chip named', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/situation#water');
    const rows = await screen.findByRole('region', { name: 'Conditions' });
    expect(rows.querySelector('#water')).not.toBeNull();
    expect(rows.querySelector('#power')).toHaveClass('cond-row-danger');
  });
});
