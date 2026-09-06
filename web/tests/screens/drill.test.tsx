import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { drillSummary } from '../../src/situation/drill';
import { condition, events, makeView, pages, playbooks, powerOffView, view } from '../fixtures/api';

const drilling = makeView({
  meta: { ...view.meta, drill: true },
  scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
  conditions: { power: condition('power', 'off') } as never,
  tasks: powerOffView.tasks,
});

describe('drillSummary', () => {
  it('counts the ticked jobs and keeps the events since the drill started', () => {
    const s = drillSummary(drilling, events);
    expect(s).toMatchObject({ elapsed_s: 7200, done: 1, total: 4, scenario: 'National grid collapse' });
    // the engine's own "Drill ended: N tasks done in M minutes" line is dropped: the debrief counts
    // the same thing itself, and printing both put two disagreeing counts of one fact side by side
    expect(s.events.map((e) => e.id)).toEqual([44, 43, 42]);
    expect(drillSummary(drilling, [...events, { ...events[0], id: 45, title: 'Drill ended: 0 tasks done in 120 minutes (drill)' }]).events.map((e) => e.id)).toEqual([44, 43, 42]);
    expect(drillSummary(drilling, events, 1).events.map((e) => e.id)).toEqual([44]);
    // an event from before the drill's clock is not part of its story
    const older = [{ ...events[0], id: 1, updated_at: '2026-09-06T09:00:00.000Z' }];
    expect(drillSummary(drilling, older).events).toEqual([]);
  });
});

describe('the drill chrome', () => {
  it('is one row in the band on every screen, and ends with a summary of what happened', async () => {
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    vi.spyOn(api, 'situationView').mockResolvedValue(drilling);
    vi.spyOn(api, 'notes').mockResolvedValue(events);
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
    expect(await screen.findByText(/jobs ticked/)).toHaveTextContent('Drill ended: National grid collapse. 2 h in, 1 of 4 jobs ticked.');
    const log = screen.getByRole('list', { name: 'What happened in the drill' });
    expect(within(log).getAllByRole('listitem')).toHaveLength(3);
    // the log speaks the household's words, not the engine's suffixes
    expect(log).toHaveTextContent('Mains power off since 13:00 on a phone');
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByText(/Drill ended/)).toBeNull();
  });

  it('says nothing when no drill is running', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    await screen.findByRole('region', { name: 'Situation' });
    expect(screen.queryByRole('button', { name: 'End drill' })).toBeNull();
  });
});
