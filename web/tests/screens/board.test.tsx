import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { BoardView } from '../../src/situation/BoardView';
import { condition, events, makeView, powerOffView, VIEW_NOW } from '../fixtures/api';

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

  it('returns Home from the Back button, and not from a tap on the board itself', async () => {
    mockBoard();
    vi.spyOn(api, 'playbooks').mockResolvedValue([]);
    const user = userEvent.setup();
    const { router } = renderRoute('/board');
    // The whole screen used to be the way back, which is why nothing on it could be touched.
    await user.click(await screen.findByRole('region', { name: 'Today' }));
    expect(router.state.location.pathname).toBe('/board');
    await user.click(screen.getByRole('button', { name: 'Back to Now' }));
    expect(router.state.location.pathname).toBe('/');
  });

  it('shows all ten services, and a tap turns one off and reads the situation again', async () => {
    mockBoard();
    const save = vi.spyOn(api, 'setCondition').mockResolvedValue(condition('water', 'off'));
    const user = userEvent.setup();
    renderRoute('/board');
    const conditions = await screen.findByRole('region', { name: 'What is working' });
    expect(within(conditions).getAllByRole('button')).toHaveLength(10);
    // Off is the pressed state, on the board as on the front door.
    expect(within(conditions).getByRole('button', { name: 'Mains power: off' })).toHaveAttribute('aria-pressed', 'true');

    const water = within(conditions).getByRole('button', { name: 'Water supply: on' });
    expect(water).toHaveAttribute('aria-pressed', 'false');
    const reads = vi.mocked(api.situationView).mock.calls.length;
    await user.click(water);
    expect(save).toHaveBeenCalledTimes(1);
    expect(save.mock.calls[0][0]).toBe('water');
    expect(save.mock.calls[0][1]).toMatchObject({ state: 'off', expected_updated_at: powerOffView.conditions.water.updated_at });
    expect(vi.mocked(api.situationView).mock.calls.length).toBeGreaterThan(reads);
  });

  it('ticks a job where it stands, and undoes it', async () => {
    mockBoard();
    const bath = powerOffView.tasks[0];
    const save = vi.spyOn(api, 'setTask')
      .mockImplementation((id, patch) => Promise.resolve({ ...bath, id, done: patch.done ?? false, done_at: patch.done ? VIEW_NOW : null }));
    const user = userEvent.setup();
    renderRoute('/board');
    const jobs = await screen.findByRole('region', { name: 'Next jobs' });
    await user.click(within(jobs).getByRole('button', { name: `Tick: ${bath.title}` }));
    expect(save).toHaveBeenCalledWith('fill-bath', { done: true });
    // The row stays where it was, struck through, with an Undo beside it.
    const done = await within(jobs).findByRole('button', { name: `Untick: ${bath.title}` });
    expect(done).toHaveAttribute('aria-pressed', 'true');
    expect(done.closest('li')).toHaveClass('board-job-done');

    await user.click(within(jobs).getByRole('button', { name: `Undo: ${bath.title}` }));
    expect(save).toHaveBeenLastCalledWith('fill-bath', { done: false });
    expect(await within(jobs).findByRole('button', { name: `Tick: ${bath.title}` })).toBeInTheDocument();
    expect(within(jobs).queryByRole('button', { name: `Undo: ${bath.title}` })).toBeNull();
  });

  it('links to the rest of the jobs', async () => {
    mockBoard();
    renderRoute('/board');
    const jobs = await screen.findByRole('region', { name: 'Next jobs' });
    expect(within(jobs).getByRole('link', { name: 'All tasks' })).toHaveAttribute('href', '/tasks');
  });

  it('leaves the idle overlay a board nobody can touch', async () => {
    mockBoard();
    renderRoute('/', { routes: [{ path: '/', element: <div className="idle-board"><BoardView /></div> }] });
    const conditions = await screen.findByRole('region', { name: 'What is working' });
    expect(conditions).toHaveTextContent('Power');
    expect(within(conditions).queryAllByRole('button')).toHaveLength(0);
    const jobs = screen.getByRole('region', { name: 'Next jobs' });
    expect(jobs).toHaveTextContent('Fill the bath and every container');
    expect(within(jobs).queryAllByRole('button')).toHaveLength(0);
    expect(within(jobs).queryByRole('link', { name: 'All tasks' })).toBeNull();
  });
});
