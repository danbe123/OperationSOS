import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { drillSummary } from '../../src/situation/drill';
import { condition, events, makeView, pages, playbooks, powerOffView, view } from '../fixtures/api';

/* What the log looks like while a drill runs: the box tags everything the drill did, and the
 * household's own morning carries on being recorded beside it. The debrief is about the first kind
 * only — round 2's version listed a real power cut under "What happened in the drill". */
const drillEvents = [
  { ...events[0], id: 44, title: 'Mains power off since 13:00 (phone)' },
  { ...events[1], id: 43, title: 'Fill the bath ticked by Sam (drill)' },
  { ...events[2], id: 42, title: 'Drill started: National grid collapse (drill)' },
];

const drilling = makeView({
  meta: { ...view.meta, drill: true },
  scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
  conditions: { power: condition('power', 'off') } as never,
  tasks: powerOffView.tasks,
});

describe('drillSummary', () => {
  it('counts the ticked jobs and keeps the events since the drill started', () => {
    const s = drillSummary(drilling, drillEvents);
    expect(s).toMatchObject({ elapsed_s: 7200, total: 4, scenario: 'National grid collapse' });
    // the household's real power cut is not something that happened in the drill
    expect(s.events.map((e) => e.id)).toEqual([43, 42]);
    // the engine's own "Drill ended: N tasks done in M minutes" line is dropped: the debrief counts
    // the same thing itself, and printing both put two disagreeing counts of one fact side by side
    expect(drillSummary(drilling, [...drillEvents, { ...events[0], id: 45, title: 'Drill ended: 0 tasks done in 120 minutes (drill)' }]).events.map((e) => e.id)).toEqual([43, 42]);
    expect(drillSummary(drilling, drillEvents, 1).events.map((e) => e.id)).toEqual([43]);
    // an event from before the drill's clock is not part of its story
    const older = [{ ...drillEvents[1], id: 1, updated_at: '2026-09-06T09:00:00.000Z' }];
    expect(drillSummary(drilling, older).events).toEqual([]);
  });
});

describe('the drill chrome', () => {
  it('is one row in the band on every screen, and ends with a summary of what happened', async () => {
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    vi.spyOn(api, 'situationView').mockResolvedValue(drilling);
    vi.spyOn(api, 'notes').mockResolvedValue(drillEvents);
    const end = vi.spyOn(api, 'endDrill').mockResolvedValue(view);
    const user = userEvent.setup();
    renderRoute('/radio');
    // The drill costs the screen one row: the band's own chip and the way out of it, not a banner.
    const band = await screen.findByRole('group', { name: 'Situation now' });
    expect(band).toHaveTextContent('Drill');
    expect(band).toHaveTextContent('National grid collapse');
    await user.click(within(band).getByRole('button', { name: 'End drill' }));
    expect(end).toHaveBeenCalled();
    // one count of the jobs and one phrasing of the clock
    // the debrief is a dialog, not a 326 px panel that pushes the rail off a 480 px screen
    const debrief = await screen.findByRole('dialog', { name: 'How the drill went' });
    expect(debrief).toHaveTextContent('National grid collapse, 2 h in.');
    expect(debrief).toHaveTextContent(/jobs ticked during it|Nothing was ticked/);
    const log = within(debrief).getByRole('list', { name: 'What happened in the drill' });
    expect(within(log).getAllByRole('listitem')).toHaveLength(2);
    // the drill's own log, in the household's words, with the tag the list itself already carries
    expect(log).toHaveTextContent('Fill the bath ticked by Sam');
    expect(log).not.toHaveTextContent('in the drill');
    expect(log).not.toHaveTextContent('Mains power off');
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog', { name: 'How the drill went' })).toBeNull();
  });

  it('says nothing when no drill is running', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    await screen.findByRole('region', { name: 'Situation' });
    expect(screen.queryByRole('button', { name: 'End drill' })).toBeNull();
  });
});
