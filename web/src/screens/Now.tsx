import { useRef, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { StockResponse } from '../api/types';
import { useQuery, type QueryState } from '../api/useQuery';
import { Icon } from '../icons';
import { ConnectPanel } from '../kiosk/ConnectPanel';
import { Screen, Body } from '../shell/Screen';
import { Briefing } from '../situation/Briefing';
import { Emergency999 } from '../situation/Emergency999';
import { nowTitle } from '../situation/nowTitle';
import { Readiness } from '../situation/Readiness';
import { scenarioMapHref } from '../situation/mapLink';
import { isEventful, useCallsHidden, useSituation } from '../situation/SituationProvider';
import { situationLine } from '../components/SituationClock';
import { ReadAloud } from '../situation/ReadAloud';
import './now.css';

/** The three the box counts in days, in the order it counts them. */
const STOCK_DAYS = [['water', 'Water'], ['food', 'Food'], ['medicine', 'Medicine']] as const;

/** Who lives here and how long the stock lasts: the two facts the rest of the box counts with. The
 * cupboard is read one level up, in Now, because the heading needs the same answer this panel does. */
function HouseholdSummary({ stock }: { stock: QueryState<StockResponse> }) {
  const people = useQuery(() => api.household(), [], { refetchOnFocus: true });
  const neighbours = useQuery(() => api.neighbours(), [], { refetchOnFocus: true });
  const days = stock.data?.days ?? null;
  const count = people.data?.length ?? 0;
  return (
    <section className="panel" aria-label="Household and stock">
      <div className="panel-head">
        <h2>Household and stock</h2>
        <Link className="btn btn-small" to="/plan">Open the plan</Link>
      </div>
      {/* The one place the box says who it is counting for. The peacetime panel above says how many
          things would help most and nothing else about people or water, so the screen no longer makes
          four statements about the same stock. */}
      <p>
        {count === 0
          ? 'Nobody is registered yet, so the box counts stock for one person.'
          : `${count} ${count === 1 ? 'person is' : 'people are'} registered.`}
        {neighbours.data && neighbours.data.length > 0 && ` ${neighbours.data.length} ${neighbours.data.length === 1 ? 'neighbour' : 'neighbours'} on the street list.`}
      </p>
      {!days || (stock.data?.items.length ?? 0) === 0 ? (
        <>
          <p className="muted">No stock recorded yet, so the box cannot say how many days you have.</p>
          <p className="row"><Link className="btn" to="/plan/stock"><Icon name="drop" size={18} /><span>Add water, food and fuel</span></Link></p>
        </>
      ) : (
        /* The API's own three figures, not a fourth count of the same cupboard: whatever Stock,
           the hub and the board say, this panel says too. */
        <ul className="row now-stock" aria-label="Days of stock left">
          {STOCK_DAYS.map(([id, title]) => {
            const d = days[id];
            return (
              <li key={id}>
                {/* The badge is the link, not a link inside a badge: a chip that keeps its tone and
                    opens the cupboard it is talking about. */}
                <Link className={d < 3 ? 'badge badge-danger' : d < 7 ? 'badge badge-warn' : 'badge badge-ok'} to="/plan/stock">
                  <span aria-hidden="true">{d < 3 ? '⚠' : d < 7 ? '▲' : '✓'}</span>
                  {title} {d} {d === 1 ? 'day' : 'days'}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/** The box itself: how a phone joins it, and the way into System. The front door used to carry the
 * hotspot's IP, a second bare URL, the free space on the drive and "CPU 45°C" — the box talking
 * about itself, in its own words, above the household's own jobs. What is left is the two things a
 * household does here (join a phone, put the board up) and anything that is actually wrong; the
 * numbers live one tap away on System, where they belong. */
function BoxPanel() {
  const { status, error } = useStatus();
  const callsHidden = useCallsHidden();
  const [open, setOpen] = useState(false);
  return (
    <section className="panel" aria-label="The box" data-testid="status-strip">
      <div className="panel-head"><h2>The box</h2><Link className="btn btn-small" to="/system"><Icon name="settings" size={18} /><span>System</span></Link></div>
      {!status ? (
        <p className="muted">{error ? `Box status unavailable: ${error}` : 'Checking the box…'}</p>
      ) : (
        <>
          <ul className="row now-box" aria-label="Box status">
            {/* One sentence, in one flex item: as three children of an inline-flex row the network's
                name went to a line of its own and the full stop after it to a third. */}
            <li><Icon name="wifi" size={18} /> <span>Phones join it over its own Wi-Fi, <strong>{status.hotspot.ssid}</strong>.</span></li>
            {/* Only what is wrong. A drive that is there and a chip that is cool are not news. */}
            {!status.disks.extended.mounted && <li className="warning"><Icon name="drive" size={18} /> The extra library drive is not connected.</li>}
            {status.cpu_temp_c !== null && status.cpu_temp_c >= status.thermal_ai_off_c && (
              <li className="warning"><Icon name="thermometer" size={18} /> The box is hot ({Math.round(status.cpu_temp_c)}°C), so the assistant is off until it cools.</li>
            )}
          </ul>
          <div className="row">
            {/* A phone joins the box over the box's own WiFi, which has nothing to do with whether
                the mobile network is up: with the networks down this was the one button that
                disappeared, and the address a second phone needs went with it. */}
            {callsHidden && <Link className="btn" to="/p/no-phones"><Icon name="alert" size={18} /><span>Phones down: what to do</span></Link>}
            <button type="button" className="btn" onClick={() => setOpen(true)}><Icon name="phone" size={18} /><span>Connect a phone</span></button>
            <Link className="btn" to="/board"><Icon name="plan" size={18} /><span>Show the board</span></Link>
            <Link className="btn" to="/ai"><Icon name="ai" size={18} /><span>Assistant</span></Link>
          </div>
          {open && <ConnectPanel ssid={status.hotspot.ssid} ip={status.hotspot.ip} onClose={() => setOpen(false)} />}
        </>
      )}
    </section>
  );
}

/** A situation that is running, or the guide last opened on this device: the way straight back in.
 * The band already names a scenario the engine knows about, so this only fills the gaps it leaves. */
function CarryOn() {
  const { status } = useStatus();
  const { view } = useSituation();
  const playbooks = useQuery(() => api.playbooks(), []);
  const [lastSlug] = useState(() => {
    try { return localStorage.getItem('sos.lastPlaybook'); } catch { return null; }
  });
  const titleOf = (slug: string) => (playbooks.data ?? []).find((p) => p.slug === slug)?.title ?? slug;
  const running = !view?.scenario && status?.situation ? status.situation : null;
  const last = lastSlug && lastSlug !== running?.slug && lastSlug !== view?.scenario?.slug ? lastSlug : null;
  if (!running && !last) return null;
  return (
    <section className="panel panel-warn now-carry" aria-label="Carry on">
      {running && (
        <Link className="now-resume" to={`/s/${running.slug}`}>
          <Icon name="alert" size={20} />
          <span>
            <small>Active situation, {situationLine({ ...running, title: null, elapsed_s: 0, phase: 'right-now' })}</small>
            <strong>{titleOf(running.slug)}</strong>
          </span>
          <Icon name="forward" size={20} />
        </Link>
      )}
      {last && (
        <Link className="now-resume" to={`/s/${last}`}>
          <Icon name="book" size={20} />
          <span><small>Recently opened on this device</small><strong>Continue: {titleOf(last)}</strong></span>
          <Icon name="forward" size={20} />
        </Link>
      )}
    </section>
  );
}

/** Now is the front door. It answers "what do I do" from the engine, or says nothing is wrong and
 * shows how ready the household is. */
export function Now() {
  const { view, error, loading, refresh } = useSituation();
  // The cupboard, read once for the two things that ask about it: the heading and the panel below.
  const stock = useQuery(() => api.stock(), [], { refetchOnFocus: true });
  const stockEmpty = stock.data ? stock.data.items.length === 0 : null;
  const eventful = isEventful(view);
  const mapHref = scenarioMapHref(view?.scenario?.slug);
  // What is read aloud is the briefing itself; the button that reads it belongs in the screen's own
  // actions, beside Search, not on a row of its own above the first job.
  const briefing = useRef<HTMLDivElement>(null);
  // The heading is the answer, not the name of the screen: the rail already says this is Now.
  return (
    <Screen
      title={nowTitle(view, stockEmpty)}
      back={false}
      actions={eventful ? <ReadAloud id="briefing" target={briefing} label="Read aloud" /> : undefined}
    >
      <Body>
        {/* With both networks down this is the most important new fact on the front door, and the
            box used to say nothing about it here at all. One component, one sentence. */}
        <Emergency999 onlyWhenHidden />
        {error && (
          <p className="panel panel-warn row" role="status">
            <span className="warning">The box cannot read the situation.</span>
            <span className="muted">The guides and the map still work.</span>
            <button type="button" className="btn btn-small" onClick={() => void refresh()}><Icon name="refresh" size={18} /><span>Try again</span></button>
          </p>
        )}
        {loading && !view && <p className="muted">Reading the situation…</p>}
        {view?.modes.map_first && (
          <p><Link className="btn btn-primary btn-big" to={mapHref}><Icon name="map" /><span>Open the map</span></Link></p>
        )}
        <CarryOn />
        {eventful ? <Briefing blockRef={briefing} /> : <Readiness />}
        <HouseholdSummary stock={stock} />
        <BoxPanel />
      </Body>
    </Screen>
  );
}
