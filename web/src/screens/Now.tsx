import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { ConnectPanel } from '../kiosk/ConnectPanel';
import { Screen, Body } from '../shell/Screen';
import { Briefing } from '../situation/Briefing';
import { Emergency999 } from '../situation/Emergency999';
import { nowTitle } from '../situation/nowTitle';
import { Readiness } from '../situation/Readiness';
import { scenarioMapHref } from '../situation/mapLink';
import { isEventful, useCallsHidden, useSituation } from '../situation/SituationProvider';
import { stockDays } from '../situation/board';
import { situationLine } from '../components/SituationClock';
import './now.css';

const STOCK_TITLE: Record<string, string> = { water: 'Water', food: 'Food', medicine: 'Medicine', fuel: 'Fuel', other: 'Other' };

/** Who lives here and how long the stock lasts: the two facts the rest of the box counts with. */
function HouseholdSummary() {
  const people = useQuery(() => api.household(), [], { refetchOnFocus: true });
  const stock = useQuery(() => api.stock(), [], { refetchOnFocus: true });
  const neighbours = useQuery(() => api.neighbours(), [], { refetchOnFocus: true });
  const days = useMemo(() => stockDays(stock.data?.items ?? []), [stock.data]);
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
      {days.length === 0 ? (
        <>
          <p className="muted">No stock recorded yet, so the box cannot say how many days you have.</p>
          <p className="row"><Link className="btn" to="/plan#stock"><Icon name="drop" size={18} /><span>Add water, food and fuel</span></Link></p>
        </>
      ) : (
        <ul className="row now-stock" aria-label="Days of stock left">
          {days.map((d) => (
            <li key={d.category} className={d.days < 3 ? 'badge badge-danger' : d.days < 7 ? 'badge badge-warn' : 'badge badge-ok'}>
              <span aria-hidden="true">{d.days < 3 ? '⚠' : d.days < 7 ? '▲' : '✓'}</span>
              {STOCK_TITLE[d.category] ?? d.category} {d.days} {d.days === 1 ? 'day' : 'days'}
            </li>
          ))}
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
            <li><Icon name="wifi" size={18} /> Phones join it over its own WiFi, <strong>{status.hotspot.ssid}</strong>.</li>
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
  const eventful = isEventful(view);
  const mapHref = scenarioMapHref(view?.scenario?.slug);
  // The heading is the answer, not the name of the screen: the rail already says this is Now.
  return (
    <Screen title={nowTitle(view)} back={false}>
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
        {eventful ? <Briefing /> : <Readiness />}
        <HouseholdSummary />
        <BoxPanel />
      </Body>
    </Screen>
  );
}
