import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { events, makeView, powerOffView, VIEW_NOW } from '../fixtures/api';

function mockBoard(view = powerOffView) {
  vi.spyOn(api, 'situationView').mockResolvedValue(view);
  vi.spyOn(api, 'notes').mockResolvedValue(events);
}

describe('/board', () => {
  // Every duration on the board counts from the stored `since` on the box's clock, so the test's
  // clock is the fixture's: only Date is faked, the timers stay real for user-event.
  beforeEach(() => vi.useFakeTimers({ now: Date.parse(VIEW_NOW), toFake: ['Date'] }));
  afterEach(() => vi.useRealTimers());

  it('shows the conditions, the next three jobs with names, sunset, the bulletin and the log', async () => {
    mockBoard();
    renderRoute('/board');
    const conditions = await screen.findByRole('region', { name: 'What is working' });
    expect(conditions).toHaveTextContent('Power');
    expect(conditions).toHaveTextContent('✕ off');
    expect(conditions).toHaveTextContent('for 1 h');

    const jobs = screen.getByRole('region', { name: 'Next jobs' });
    const items = within(jobs).getAllByRole('listitem');
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent('Fill the bath and every container');
    expect(items[1]).toHaveTextContent('Sam');
    expect(items[0]).toHaveTextContent('nobody yet');

    const facts = await screen.findByRole('region', { name: 'Today' });
    expect(facts).toHaveTextContent('Sunset');
    expect(facts).toHaveTextContent('BBC Radio 4');
    // The across-the-room screen counts services and jobs; there is no cupboard to count down.
    expect(within(facts).queryByRole('list', { name: 'Stock left' })).toBeNull();
    expect(facts).not.toHaveTextContent('days');

    const log = await screen.findByRole('region', { name: 'Last events' });
    expect(within(log).getAllByRole('listitem')).toHaveLength(3);
    // Through the words table: "(phone)" is the engine's suffix, not the household's.
    expect(log).toHaveTextContent('Mains power off since 13:00 on a phone');
    expect(log).not.toHaveTextContent('(phone)');
  });

  it('flies the drill flag and names the scenario', async () => {
    mockBoard(makeView({
      meta: { ...powerOffView.meta, drill: true },
      scenario: { slug: 'grid-collapse', title: 'National grid collapse', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
    }));
    renderRoute('/board');
    expect(await screen.findByRole('heading', { name: 'National grid collapse' })).toBeInTheDocument();
    // the board flies its own flag, and the chrome's drill bar flies one on every screen
    expect(screen.getAllByText(/Drill/).length).toBeGreaterThanOrEqual(1);
    expect(document.querySelector('.board-drill')).toHaveTextContent('Drill');
    expect(document.querySelector('.board-elapsed')).toHaveTextContent('2 h in');
  });

  it('returns Home on a tap anywhere', async () => {
    mockBoard();
    vi.spyOn(api, 'playbooks').mockResolvedValue([]);
    const user = userEvent.setup();
    const { router } = renderRoute('/board');
    await user.click(await screen.findByRole('button', { name: /Board: tap to go back to Now/ }));
    expect(router.state.location.pathname).toBe('/');
  });
});
