import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { ConnectPanel } from '../kiosk/ConnectPanel';
import { Screen, Body } from '../shell/Screen';
import { Briefing } from '../situation/Briefing';
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
      <p>
        {count === 0
          ? 'Nobody registered yet. Stock is counted for one person until you add people.'
          : `${count} ${count === 1 ? 'person' : 'people'} registered.`}
        {neighbours.data && neighbours.data.length > 0 && ` ${neighbours.data.length} ${neighbours.data.length === 1 ? 'neighbour' : 'neighbours'} on the street list.`}
      </p>
      {days.length === 0 ? (
        <p className="muted">No stock recorded. <Link to="/plan#stock">Add water, food and fuel</Link> to see how many days you have.</p>
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

/** The box itself: how a phone joins it, how hot it is, and the way into System. */
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
            <li><Icon name="wifi" size={18} /> WiFi <strong>{status.hotspot.ssid}</strong></li>
            <li>http://{status.hotspot.ip}</li>
            <li>http://sos.box</li>
            <li><Icon name="drive" size={18} /> {status.disks.extended.mounted ? `External drive: ${status.disks.extended.free_gb} GB free` : 'External drive: not connected'}</li>
            <li className={status.cpu_temp_c !== null && status.cpu_temp_c >= status.thermal_ai_off_c ? 'warning' : undefined}>
              <Icon name="thermometer" size={18} /> {status.cpu_temp_c === null ? 'CPU: not readable' : `CPU ${Math.round(status.cpu_temp_c)}°C`}
            </li>
          </ul>
          <div className="row">
            {callsHidden ? (
              <Link className="btn" to="/p/no-phones"><Icon name="alert" size={18} /><span>Phones down: what to do</span></Link>
            ) : (
              <button type="button" className="btn" onClick={() => setOpen(true)}><Icon name="phone" size={18} /><span>Connect a phone</span></button>
            )}
            <Link className="btn" to="/board"><Icon name="plan" size={18} /><span>Show the board</span></Link>
            <Link className="btn" to="/ai"><Icon name="ai" size={18} /><span>Assistant</span></Link>
          </div>
          {open && !callsHidden && <ConnectPanel ssid={status.hotspot.ssid} ip={status.hotspot.ip} onClose={() => setOpen(false)} />}
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
