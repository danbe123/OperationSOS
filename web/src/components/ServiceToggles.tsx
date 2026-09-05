import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { ServiceId } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { Icon } from '../icons';
import { ALL_ON, offServices, SERVICE_IDS, SERVICE_INFO } from '../services';
import { notify } from './Notice';

/** The "what's working" strip: five shared toggles, green when on, red when off. */
export function ServiceToggles() {
  const { status, update } = useStatus();
  const [busy, setBusy] = useState<ServiceId | null>(null);
  const services = status?.services ?? ALL_ON;
  const toggle = async (id: ServiceId) => {
    if (!status) return;
    const next = !services[id];
    setBusy(id);
    update({ ...status, services: { ...services, [id]: next } });
    try {
      const saved = await api.setService(id, next);
      update({ ...status, services: saved });
    } catch (e) {
      update({ ...status, services });
      notify(`Could not update ${SERVICE_INFO[id].title}: ${errorMessage(e)}`);
    } finally {
      setBusy(null);
    }
  };
  return (
    <section className="services" aria-label="What is working">
      <p className="eyebrow">What is working</p>
      <div className="service-toggles" role="group" aria-label="Services">
        {SERVICE_IDS.map((id) => {
          const on = services[id];
          return (
            <button key={id} type="button" className={on ? 'service on' : 'service off'} aria-pressed={on} aria-label={`${SERVICE_INFO[id].title}: ${on ? 'on' : 'off'}`} disabled={busy === id || !status} onClick={() => void toggle(id)}>
              <Icon name={SERVICE_INFO[id].icon} size={22} />
              <span className="service-title">{SERVICE_INFO[id].title}</span>
              <span className="service-state">{on ? '✓ on' : '✕ off'}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

/** Home panel: what to read for each service that is off. */
export function OutagePanel() {
  const { status } = useStatus();
  const off = offServices(status?.services);
  if (!off.length) return null;
  return (
    <section className="outage-panel" aria-label="What is off">
      {off.map((id) => (
        <div key={id} className="outage">
          <h3><Icon name={SERVICE_INFO[id].icon} size={20} /> {SERVICE_INFO[id].offLabel}</h3>
          <ul className="row">
            {SERVICE_INFO[id].links.map((l) => <li key={l.to}><Link className="btn" to={l.to}>{l.title}</Link></li>)}
          </ul>
        </div>
      ))}
      {off.includes('phones') && <p className="muted">999, 111 and 105 will not connect while the phones are down; the numbers on every page are marked, and the page above says what to do instead.</p>}
    </section>
  );
}

/** One-line notice on content screens listing what is off. */
export function OutageNotice() {
  const { status } = useStatus();
  const off = offServices(status?.services);
  if (!off.length) return null;
  return (
    <p className="pad notice outage-notice" role="status">
      <Icon name="alert" size={18} /> Off right now: {off.map((id) => SERVICE_INFO[id].title.toLowerCase()).join(', ')}.
      {off.includes('phones') && <> Phone numbers on this page will not connect: <Link to="/p/no-phones">getting help without phones</Link>.</>}
      {' '}<Link to="/">Change on Home</Link>
    </p>
  );
}
