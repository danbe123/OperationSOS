import { useCallback, useEffect, useReducer, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Condition, ConditionId, ConditionState, Task } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { notify } from '../components/Notice';
import { Icon } from '../icons';
import { describeElapsed, phaseFor } from '../tools/situation';
import '../screens/board.css';
import { withTask } from './apply';
import { boardSunset, nextTasks } from './board';
import { ago, clockTime, CONDITION_IDS, CONDITION_INFO, HOME_CONDITION_IDS, sinceDuration, STATE_SYMBOL, STATE_TONE, stateWord } from './conditions';
import { bulletinWords, eventTitle } from '../api/words';
import { nowTitle } from './nowTitle';
import { useSituation } from './SituationProvider';
import { UndoTick, UNDO_MS } from './Tick';

export const BOARD_REFRESH_MS = 30_000;

function timeOfDay(at: number): string {
  return new Date(at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

/** The jobs ticked on the board in the last ten seconds. `nextTasks` drops a job the moment it is
 * done, so without this the row would vanish under the finger that ticked it; instead it stays
 * where it is, struck through, with an Undo beside it, exactly as a tick behaves everywhere else in
 * the box. */
function useRecentTicks(ms: number = UNDO_MS) {
  const [ids, setIds] = useState<string[]>([]);
  const timers = useRef(new Map<string, number>());
  useEffect(() => {
    const running = timers.current;
    return () => { running.forEach((t) => window.clearTimeout(t)); running.clear(); };
  }, []);
  const forget = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t !== undefined) { window.clearTimeout(t); timers.current.delete(id); }
    setIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev));
  }, []);
  const remember = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t !== undefined) window.clearTimeout(t);
    timers.current.set(id, window.setTimeout(() => forget(id), ms));
    setIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
  }, [forget, ms]);
  return { ids, remember, forget };
}

/** The kiosk's standing screen: what is off, what is next, and when the light goes.
 * Big type for a 7-inch screen across the room; everything on it refreshes itself.
 *
 * `interactive` turns the board into the control panel it is on `/board`: every service is a button
 * that turns it off or on, and every job is a button that ticks it. The idle overlay leaves it
 * false — the screen a sleeping kiosk shows is read only, and a household waking the box must not
 * change the situation with the touch that woke it. `action` is the screen's own button (Back to
 * Now), which belongs at the top of the board's header rather than in a bar above it. */
export function BoardView({ interactive = false, action }: { interactive?: boolean; action?: ReactNode } = {}) {
  const { view, refresh, apply } = useSituation();
  const events = useQuery(() => api.notes('event'), [], { intervalMs: BOARD_REFRESH_MS });
  const [, tick] = useReducer((x: number) => x + 1, 0);
  const [busyCondition, setBusyCondition] = useState<ConditionId | null>(null);
  const [busyTask, setBusyTask] = useState<string | null>(null);
  const ticks = useRecentTicks();
  useEffect(() => {
    const id = window.setInterval(tick, BOARD_REFRESH_MS);
    return () => window.clearInterval(id);
  }, []);

  const now = Date.now();
  if (!view) return <div className="board board-waiting"><p>Reading the situation…</p></div>;
  const scenario = view.scenario;

  /* The same request the front door's service buttons send, in the same shape: the board is another
     way into the one switch, not a second one. */
  const flip = async (c: Condition) => {
    const next: ConditionState = c.state === 'working' ? 'off' : 'working';
    setBusyCondition(c.id);
    try {
      await api.setCondition(c.id, { state: next, since: new Date().toISOString(), expected_updated_at: c.updated_at });
      await refresh();
    } catch (e) {
      notify(`Could not change ${CONDITION_INFO[c.id].title}: ${errorMessage(e)}`);
    } finally {
      setBusyCondition(null);
    }
  };

  const tickJob = async (t: Task, done: boolean) => {
    setBusyTask(t.id);
    try {
      const saved = await api.setTask(t.id, { done });
      apply(withTask(view, saved));
      if (done) ticks.remember(t.id); else ticks.forget(t.id);
    } catch (e) {
      notify(`Could not save "${t.title}": ${errorMessage(e)}`);
    } finally {
      setBusyTask(null);
    }
  };

  /* Read only, the board is a glance: the five services the front door shows, plus anything else
     that has gone wrong. A board you can touch has to show all ten, or there is no way to tell it
     the gas has gone off. */
  const others = (Object.keys(view.conditions) as ConditionId[])
    .filter((id) => !HOME_CONDITION_IDS.includes(id) && view.conditions[id]?.state !== 'working');
  const shown = interactive ? CONDITION_IDS : [...HOME_CONDITION_IDS, ...others];
  const nextIds = new Set(nextTasks(view.tasks).map((t) => t.id));
  const jobs = interactive
    ? view.tasks.filter((t) => nextIds.has(t.id) || ticks.ids.includes(t.id))
    : nextTasks(view.tasks);
  const sunset = boardSunset(view, now);
  const bulletin = view.bulletins.next;
  // Three lines, not five: the log was the bottom third of the across-the-room screen, in the
  // smallest type on it, and the tiles above it were being clipped to make room.
  const log = (events.data ?? []).slice(0, 3);

  return (
    <div className={interactive ? 'board board-live' : 'board'}>
      <header className="board-head">
        {action}
        {view.meta.drill && <span className="badge badge-warn board-drill"><span aria-hidden="true">⚑</span> Drill</span>}
        {/* A glance screen must never say "Something is off" and leave the household to find out
            what: the headline names it, in the same words the front door uses. */}
        <h1 className="board-title">{scenario ? scenario.title : nowTitle(view)}</h1>
        {scenario && <p className="board-elapsed">{describeElapsed(scenario.elapsed_s)}, {phaseFor(scenario.elapsed_s).title.toLowerCase()}</p>}
        <p className="board-now">{timeOfDay(now)}</p>
      </header>

      <div className="board-cols">
        <section className={interactive ? 'board-conditions board-conditions-all' : 'board-conditions'} aria-label="What is working">
          {shown.map((id) => {
            const c = view.conditions[id];
            if (!c) return null;
            const info = CONDITION_INFO[id];
            const tone = STATE_TONE[c.state];
            const off = c.state !== 'working';
            const face = (
              <>
                <span className="board-cond-name"><Icon name={info.icon} size={26} /> {info.short}</span>
                <span className="cond-state"><span aria-hidden="true">{STATE_SYMBOL[c.state]}</span> {stateWord(id, c.state)}</span>
                <span className="cond-for">{sinceDuration(c, now)}</span>
              </>
            );
            if (!interactive) return <div key={id} className={`board-cond cond-${tone}`}>{face}</div>;
            return (
              <button
                key={id} type="button" className={`board-cond cond-${tone}`}
                aria-pressed={off} aria-label={`${info.title}: ${stateWord(id, c.state)}`}
                title={off ? `${info.title} is ${stateWord(id, c.state)}. Tap when it is ${stateWord(id, 'working')} again.` : `${info.title} is ${stateWord(id, 'working')}. Tap if it has gone ${stateWord(id, 'off')}.`}
                disabled={busyCondition === id} onClick={() => void flip(c)}
              >
                {face}
              </button>
            );
          })}
        </section>

        <section className="board-tasks" aria-label="Next jobs">
          <h2>Next</h2>
          {jobs.length === 0 ? (
            <p className="muted">Nothing outstanding.</p>
          ) : (
            <ol className={interactive ? 'board-task-list board-jobs' : 'board-task-list'}>
              {jobs.map((t) => (
                <li key={t.id} className={interactive ? (t.done ? 'board-job board-job-done' : 'board-job') : undefined}>
                  {interactive ? (
                    <button
                      type="button" className="board-job-tick" aria-pressed={t.done}
                      aria-label={`${t.done ? 'Untick' : 'Tick'}: ${t.title}`}
                      disabled={busyTask === t.id} onClick={() => void tickJob(t, !t.done)}
                    >
                      <span className="board-job-box" aria-hidden="true">{t.done ? '✓' : ''}</span>
                      <span className="board-task-title">{t.title}</span>
                      <span className="board-task-who">{t.person ? t.person : 'nobody yet'}</span>
                    </button>
                  ) : (
                    <>
                      <span className="board-task-title">{t.title}</span>
                      <span className="board-task-who">{t.person ? t.person : 'nobody yet'}</span>
                    </>
                  )}
                  {interactive && t.done && ticks.ids.includes(t.id) && (
                    <UndoTick label={t.title} busy={busyTask === t.id} onUndo={() => void tickJob(t, false)} />
                  )}
                </li>
              ))}
            </ol>
          )}
          {/* Three jobs is what fits across the room; the rest of them are one tap away. */}
          {interactive && <p className="board-all-tasks"><Link to="/tasks">All tasks</Link></p>}
        </section>

        <section className="board-facts" aria-label="Today">
          <p><Icon name="sun" size={22} /> <span>Sunset {sunset ? timeOfDay(sunset.getTime()) : 'not tonight'}</span></p>
          <p><Icon name="radio" size={22} /> <span>{bulletin ? `${bulletinWords(bulletin.station)} ${bulletinWords(bulletin.frequency)} at ${clockTime(bulletin.at)}` : 'No bulletin scheduled'}</span></p>
        </section>
      </div>

      <section className="board-events" aria-label="Last events">
        <ul>
          {log.length === 0 && <li className="muted">Nothing logged yet.</li>}
          {/* Through the words table, like every other event line in the box: the board was the one
              screen still printing "(kiosk)" and "(drill)" at a household. */}
          {log.map((e) => <li key={e.id}><strong>{timeOfDay(Date.parse(e.updated_at))}</strong> {eventTitle(e.title)} <span className="muted">{ago(e.updated_at, now)}</span></li>)}
        </ul>
      </section>
    </div>
  );
}
