import { useEffect, useReducer } from 'react';
import { api } from '../api/client';
import type { ConditionId } from '../api/types';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { describeElapsed, phaseFor } from '../tools/situation';
import '../screens/board.css';
import { boardSunset, nextTasks, stockDays } from './board';
import { ago, chipDuration, clockTime, CONDITION_INFO, HOME_CONDITION_IDS, STATE_LABEL, STATE_SYMBOL, STATE_TONE } from './conditions';
import { useSituation } from './SituationProvider';

export const BOARD_REFRESH_MS = 30_000;
const STOCK_TITLE: Record<string, string> = { water: 'Water', food: 'Food', medicine: 'Medicine', fuel: 'Fuel', other: 'Other' };

function timeOfDay(at: number): string {
  return new Date(at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

/** The kiosk's standing screen: what is off, what is next, and when the light goes.
 * Big type for a 7-inch screen across the room; everything on it refreshes itself. */
export function BoardView() {
  const { view } = useSituation();
  const stock = useQuery(() => api.stock(), [], { intervalMs: BOARD_REFRESH_MS });
  const events = useQuery(() => api.notes('event'), [], { intervalMs: BOARD_REFRESH_MS });
  const [, tick] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    const id = window.setInterval(tick, BOARD_REFRESH_MS);
    return () => window.clearInterval(id);
  }, []);

  const now = Date.now();
  if (!view) return <div className="board board-waiting"><p>Reading the situation…</p></div>;
  const scenario = view.scenario;
  const others = (Object.keys(view.conditions) as ConditionId[])
    .filter((id) => !HOME_CONDITION_IDS.includes(id) && view.conditions[id]?.state !== 'working');
  const shown = [...HOME_CONDITION_IDS, ...others];
  const jobs = nextTasks(view.tasks);
  const sunset = boardSunset(view, now);
  const bulletin = view.bulletins.next;
  const days = stockDays(stock.data?.items ?? []);
  const log = (events.data ?? []).slice(0, 5);

  return (
    <div className="board">
      <header className="board-head">
        {view.meta.drill && <span className="badge badge-warn board-drill"><span aria-hidden="true">⚑</span> Drill</span>}
        <h1 className="board-title">
          {scenario ? scenario.title : shown.some((id) => view.conditions[id]?.state !== 'working') ? 'Something is off' : 'Everything is working'}
        </h1>
        {scenario && <p className="board-elapsed">{describeElapsed(scenario.elapsed_s)}, {phaseFor(scenario.elapsed_s).title.toLowerCase()}</p>}
        <p className="board-now">{timeOfDay(now)}</p>
      </header>

      <div className="board-cols">
        <section className="board-conditions" aria-label="What is working">
          {shown.map((id) => {
            const c = view.conditions[id];
            if (!c) return null;
            const tone = STATE_TONE[c.state];
            return (
              <div key={id} className={`board-cond cond-${tone}`}>
                <span className="board-cond-name"><Icon name={CONDITION_INFO[id].icon} size={26} /> {CONDITION_INFO[id].short}</span>
                <span className="cond-state"><span aria-hidden="true">{STATE_SYMBOL[c.state]}</span> {STATE_LABEL[c.state]}</span>
                <span className="cond-for">{chipDuration(c.state, c.for_s)}</span>
              </div>
            );
          })}
        </section>

        <section className="board-tasks" aria-label="Next jobs">
          <h2>Next</h2>
          {jobs.length === 0 ? (
            <p className="muted">Nothing outstanding.</p>
          ) : (
            <ol className="board-task-list">
              {jobs.map((t) => (
                <li key={t.id}>
                  <span className="board-task-title">{t.title}</span>
                  <span className="board-task-who">{t.person ? t.person : 'nobody yet'}</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="board-facts" aria-label="Today">
          <p><Icon name="sun" size={22} /> Sunset {sunset ? timeOfDay(sunset.getTime()) : 'not tonight'}</p>
          <p><Icon name="radio" size={22} /> {bulletin ? `${bulletin.station} ${bulletin.frequency} at ${clockTime(bulletin.at)}` : 'No bulletin scheduled'}</p>
          <ul className="board-stock" aria-label="Stock left">
            {days.length === 0 && <li className="muted">No stock recorded</li>}
            {days.map((d) => (
              <li key={d.category} className={d.days < 3 ? 'warning' : undefined}>
                {STOCK_TITLE[d.category] ?? d.category} {d.days} {d.days === 1 ? 'day' : 'days'}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="board-events" aria-label="Last events">
        <ul>
          {log.length === 0 && <li className="muted">Nothing logged yet.</li>}
          {log.map((e) => <li key={e.id}><strong>{timeOfDay(Date.parse(e.updated_at))}</strong> {e.title} <span className="muted">{ago(e.updated_at, now)}</span></li>)}
        </ul>
      </section>
    </div>
  );
}
