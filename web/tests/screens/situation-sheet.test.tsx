import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { condition, makeView, playbooks, powerOffView, view } from '../fixtures/api';

const rowFor = (rows: HTMLElement, id: string) => rows.querySelector(`#${id}`) as HTMLElement;

/** What the box knows about a service — who set it, the note, the day-old prompt — is behind Details. */
async function openDetails(rows: HTMLElement, id: string) {
  await userEvent.setup().click(within(rowFor(rows, id)).getByRole('button', { name: 'Details' }));
}

describe('The situation sheet', () => {
  it('puts the three states on every row, with the one the box is holding pressed', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    expect(within(rows).getAllByRole('listitem')).toHaveLength(10);
    expect(rows).toHaveTextContent('Everything is working. Open a service to say it has gone.');
    // No door in front of the door: the answer is on the row, not one tap behind a "Change" button.
    expect(within(rows).queryByRole('button', { name: /Change/ })).toBeNull();
    for (const name of ['Mains power', 'Water supply', 'Sewage and drains']) {
      const group = within(rows).getByRole('group', { name });
      expect(within(group).getAllByRole('button').map((b) => b.textContent?.trim()), name).toEqual(['✓Working', 'Patchy', 'Off']);
      expect(within(group).getByRole('button', { name: 'Working' }), name).toHaveAttribute('aria-pressed', 'true');
    }
    expect(screen.getByRole('link', { name: 'Print report' })).toHaveAttribute('href', '/api/situation/report');
    expect(screen.getByRole('link', { name: 'Print report' })).toHaveAttribute('target', '_blank');
  });

  it('asks when it started on the row that was changed, and nowhere else', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const set = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const user = userEvent.setup();
    const rows = await screen.findByRole('region', { name: 'What is working' });
    await user.click(within(within(rows).getByRole('group', { name: 'Mains power' })).getByRole('button', { name: 'Off' }));

    const when = within(rows).getByRole('group', { name: 'Mains power: since when?' });
    expect(within(when).getAllByRole('button').map((b) => b.textContent?.trim())).toEqual(['Just now', 'About an hour ago', 'Earlier', 'Save', 'Cancel']);
    // The question is asked about the one service somebody touched, not about all ten.
    expect(within(rows).queryByRole('group', { name: 'Water supply: since when?' })).toBeNull();

    await user.click(within(when).getByRole('button', { name: 'About an hour ago' }));
    await user.click(within(when).getByRole('button', { name: 'Save' }));
    expect(set).toHaveBeenCalledTimes(1);
    const [id, body] = set.mock.calls[0];
    expect(id).toBe('power');
    expect(body.state).toBe('off');
    expect(body.note).toBe('');
    expect(body.expected_updated_at).toBe(view.conditions.power.updated_at);
    expect(Date.now() - Date.parse(body.since as string)).toBeGreaterThan(3_500_000);
    expect(Date.now() - Date.parse(body.since as string)).toBeLessThan(3_700_000);
    // and the question goes once it has been answered
    expect(within(rows).queryByRole('group', { name: 'Mains power: since when?' })).toBeNull();
  });

  it('changes nothing when the question is cancelled', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const set = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const user = userEvent.setup();
    const rows = await screen.findByRole('region', { name: 'What is working' });
    await user.click(within(within(rows).getByRole('group', { name: 'Mains power' })).getByRole('button', { name: 'Off' }));
    await user.click(within(within(rows).getByRole('group', { name: 'Mains power: since when?' })).getByRole('button', { name: 'Cancel' }));
    expect(within(rows).queryByRole('group', { name: 'Mains power: since when?' })).toBeNull();
    expect(set).not.toHaveBeenCalled();
    expect(within(within(rows).getByRole('group', { name: 'Mains power' })).getByRole('button', { name: 'Working' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('offers a typed-in time under "Earlier"', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const set = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const user = userEvent.setup();
    const rows = await screen.findByRole('region', { name: 'What is working' });
    await user.click(within(within(rows).getByRole('group', { name: 'Mains power' })).getByRole('button', { name: 'Off' }));
    const when = within(rows).getByRole('group', { name: 'Mains power: since when?' });
    await user.click(within(when).getByRole('button', { name: 'Earlier' }));
    // In the order this country writes dates in and on a 24-hour clock.
    const field = within(when).getByLabelText(/Mains power: time it started/);
    await user.clear(field);
    await user.type(field, '06/09/2026 09:30');
    await user.click(within(when).getByRole('button', { name: 'Save' }));
    expect(set.mock.calls[0][1].since).toBe(new Date('2026-09-06T09:30').toISOString());
  });

  it('keeps who set it, the note and the stale prompt behind Details', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      conditions: { power: condition('power', 'off', { stale: true, for_s: 90_000, set_by: 'kiosk', updated_at: '2026-09-05T10:00:00.000Z' }) } as never,
    }));
    const confirm = vi.spyOn(api, 'confirmCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    const row = rowFor(rows, 'power');
    expect(row).not.toHaveTextContent('Set from kiosk at');
    expect(within(row).queryByRole('status')).toBeNull();
    expect(within(row).queryByLabelText('Mains power: note')).toBeNull();
    expect(within(row).getByRole('button', { name: 'Details' })).toHaveAttribute('aria-expanded', 'false');

    await openDetails(rows, 'power');
    expect(within(row).getByRole('button', { name: 'Details' })).toHaveAttribute('aria-expanded', 'true');
    expect(row).toHaveTextContent('Set from kiosk at');
    expect(within(row).getByLabelText('Mains power: note')).toBeInTheDocument();
    expect(within(row).getByRole('button', { name: 'Save note' })).toBeInTheDocument();
    expect(within(row).getByRole('status')).toHaveTextContent('Still off?');
    await userEvent.setup().click(within(row).getByRole('button', { name: 'Confirm, still off' }));
    expect(confirm).toHaveBeenCalledWith('power');
  });

  it('marks the chosen state with the symbol, and puts it on nothing else', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    expect(rows).toHaveTextContent('2 of 10 not working. Open a service to say it has changed.');
    // A tick, a triangle and a cross on all three buttons at once said nothing about which one the
    // box is holding: the symbol belongs to the answer, not to the options.
    for (const [name, symbol] of [['Mains power', '✕'], ['Mobile network', '▲'], ['Water supply', '✓']] as const) {
      const group = within(rows).getByRole('group', { name });
      const glyphs = group.querySelectorAll('.state-glyph');
      expect(glyphs, name).toHaveLength(1);
      expect(glyphs[0].textContent).toBe(symbol);
      expect(glyphs[0].closest('button')).toHaveAttribute('aria-pressed', 'true');
      // and the glyph is decoration: a screen reader still hears the bare word.
      expect(within(group).getByRole('button', { name: 'Off' })).toBeInTheDocument();
    }
    // The chosen button also carries the classes the sunken fill and the inset edge hang on.
    const off = within(within(rows).getByRole('group', { name: 'Mains power' })).getByRole('button', { name: 'Off' });
    expect(off.className.split(' ')).toEqual(expect.arrayContaining(['state-btn', 'state-set', 'state-danger']));
  });

  it('says nobody has set a condition nobody has set, rather than "Set from at ."', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      conditions: { gas: condition('gas', 'working', { set_by: '', updated_at: '', since: null }) } as never,
    }));
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    await openDetails(rows, 'gas');
    expect(rowFor(rows, 'gas')).toHaveTextContent('Nobody has set this yet.');
    expect(rowFor(rows, 'gas')).not.toHaveTextContent('Set from');
    // and a row somebody has set still says who and when, in British words
    await openDetails(rows, 'power');
    expect(rowFor(rows, 'power')).toHaveTextContent(/Set from phone at [A-Z][a-z]+day \d{1,2} [A-Z][a-z]+, \d\d:\d\d\./);
  });

  it('warns instead of overwriting when another phone got there first', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'setCondition').mockRejectedValue(new ApiError(409, 'conflict'));
    renderRoute('/situation');
    const user = userEvent.setup();
    const rows = await screen.findByRole('region', { name: 'What is working' });
    await user.click(within(within(rows).getByRole('group', { name: 'Water supply' })).getByRole('button', { name: 'Off' }));
    await user.click(within(within(rows).getByRole('group', { name: 'Water supply: since when?' })).getByRole('button', { name: 'Save' }));
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
    expect(await screen.findByRole('group', { name: 'Situation now' })).toHaveTextContent('Drill');
    await user.click(screen.getByRole('button', { name: 'End drill' }));
    expect(end).toHaveBeenCalled();
  });

  it('opens at the condition the chip named, with its details out', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/situation#water');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    expect(within(rowFor(rows, 'water')).getByRole('button', { name: 'Details' })).toHaveAttribute('aria-expanded', 'true');
    expect(within(rowFor(rows, 'water')).getByLabelText('Water supply: note')).toBeInTheDocument();
    expect(within(rowFor(rows, 'power')).getByRole('button', { name: 'Details' })).toHaveAttribute('aria-expanded', 'false');
    expect(rowFor(rows, 'power')).toHaveClass('cond-row-danger');
  });
});
