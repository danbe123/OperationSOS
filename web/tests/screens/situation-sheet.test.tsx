import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { condition, makeView, playbooks, powerOffView, view } from '../fixtures/api';
import { localInput } from '../../src/situation/since';

/** A service that is working is one line until somebody asks for its form. */
async function openRow(rows: HTMLElement, id: string) {
  await userEvent.setup().click(within(rows.querySelector(`#${id}`) as HTMLElement).getByRole('button', { name: /Change/ }));
}

describe('The situation sheet', () => {
  it('lists all ten conditions with three states each, and a print link', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    expect(within(rows).getAllByRole('listitem')).toHaveLength(10);
    // Ten working services are ten lines, not ten forms: the sheet says so, and no form is open.
    expect(rows).toHaveTextContent('Everything is working. Open a service to say it has gone.');
    expect(within(rows).queryByRole('group', { name: 'Mains power' })).toBeNull();
    await openRow(rows, 'power');
    const power = within(rows).getByRole('group', { name: 'Mains power' });
    expect(within(power).getAllByRole('button').map((b) => b.textContent?.trim())).toEqual(['✓Working', 'Patchy', 'Off']);
    expect(within(power).getByRole('button', { name: 'Working' })).toHaveAttribute('aria-pressed', 'true');
    // One open at a time.
    await openRow(rows, 'sewage');
    expect(within(rows).getByRole('group', { name: 'Sewage and drains' })).toBeInTheDocument();
    expect(within(rows).queryByRole('group', { name: 'Mains power' })).toBeNull();
    expect(screen.getByRole('link', { name: 'Print report' })).toHaveAttribute('href', '/api/situation/report');
    expect(screen.getByRole('link', { name: 'Print report' })).toHaveAttribute('target', '_blank');
  });

  it('sets a state with the chosen since time and the row it was based on', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const set = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('power', 'off'));
    renderRoute('/situation');
    const user = userEvent.setup();
    await openRow(await screen.findByRole('region', { name: 'What is working' }), 'power');
    await user.selectOptions(screen.getByLabelText('Mains power: since'), 'hour');
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
    const row = (await screen.findByRole('region', { name: 'What is working' })).querySelector('#power') as HTMLElement;
    expect(row).toHaveTextContent('Set from kiosk at');
    expect(within(row).getByRole('status')).toHaveTextContent('Still off?');
    await userEvent.setup().click(within(row).getByRole('button', { name: 'Confirm, still off' }));
    expect(confirm).toHaveBeenCalledWith('power');
  });


  it('marks the chosen state with the symbol, and puts it on nothing else', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    // What is not working is always open; the water, which is, opens on request.
    expect(rows).toHaveTextContent('2 of 10 not working. Open a service to say it has changed.');
    await openRow(rows, 'water');
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

  it('opens the since picker on the time the box is already telling everyone about', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    const anHourAgo = new Date(Date.now() - 3_600_000).toISOString();
    const oddly = new Date(Date.now() - 3 * 3_600_000 - 2_220_000).toISOString();
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      conditions: {
        power: condition('power', 'off', { since: anHourAgo, updated_at: anHourAgo }),
        water: condition('water', 'off', { since: oddly, updated_at: oddly }),
      } as never,
    }));
    renderRoute('/situation');
    // The heading two lines above says "off for 1 h"; the control used to say "Just now".
    expect(await screen.findByLabelText('Mains power: since')).toHaveValue('hour');
    // Nothing round fits the water, so the box offers the time itself rather than a near-enough lie,
    // in the order this country writes dates in and on a 24-hour clock.
    expect(screen.getByLabelText('Water supply: since')).toHaveValue('custom');
    expect(screen.getByLabelText(/Water supply: time it started/)).toHaveValue(localInput(oddly));
    expect(localInput(oddly)).toMatch(/^\d\d\/\d\d\/\d{4} \d\d:\d\d$/);
    // A condition nobody has changed opens on "Just now": the picker is for the change about to be made.
    await openRow(screen.getByRole('region', { name: 'What is working' }), 'gas');
    expect(screen.getByLabelText('Gas: since')).toHaveValue('now');
  });

  it('says nobody has set a condition nobody has set, rather than "Set from at ."', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      conditions: { gas: condition('gas', 'working', { set_by: '', updated_at: '', since: null }) } as never,
    }));
    renderRoute('/situation');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    await openRow(rows, 'gas');
    expect(rows.querySelector('#gas')).toHaveTextContent('Nobody has set this yet.');
    expect(rows.querySelector('#gas')).not.toHaveTextContent('Set from');
    // and a row somebody has set still says who and when, in British words
    await openRow(rows, 'power');
    expect(rows.querySelector('#power')).toHaveTextContent(/Set from phone at [A-Z][a-z]+day \d{1,2} [A-Z][a-z]+, \d\d:\d\d\./);
  });

  it('warns instead of overwriting when another phone got there first', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'setCondition').mockRejectedValue(new ApiError(409, 'conflict'));
    renderRoute('/situation');
    await openRow(await screen.findByRole('region', { name: 'What is working' }), 'water');
    await userEvent.setup().click(within(screen.getByRole('group', { name: 'Water supply' })).getByRole('button', { name: /Off/ }));
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

  it('opens at the condition the chip named', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/situation#water');
    const rows = await screen.findByRole('region', { name: 'What is working' });
    expect(rows.querySelector('#water')).not.toBeNull();
    expect(rows.querySelector('#power')).toHaveClass('cond-row-danger');
  });
});
