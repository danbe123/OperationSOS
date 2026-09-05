import { useState } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Html } from '../components/Html';
import { Icon } from '../icons';
import { useKiosk } from '../kiosk/KioskProvider';
import { EventLog } from './plan/EventLog';
import { Household } from './plan/Household';
import { Notes } from './plan/Notes';
import { Pins } from './plan/Pins';
import { Stock } from './plan/Stock';

export function Plan() {
  const kiosk = useKiosk();
  const planQ = useQuery(() => api.page('household-plan'), []);
  const [householdVersion, setHouseholdVersion] = useState(0);   // stock days-left depend on the household size
  return (
    <div className="screen">
      <AppBar title="Plan" actions={!kiosk ? <button type="button" className="btn btn-chrome" onClick={() => window.print()}><Icon name="print" /><span>Print</span></button> : undefined} />
      <nav className="row pad plan-jump no-print" aria-label="Plan sections">
        <a className="btn" href="#household">Household</a><a className="btn" href="#stock">Stock</a><a className="btn" href="#plan">Household plan</a><a className="btn" href="#notes">Notes</a><a className="btn" href="#log">Event log</a>
      </nav>
      <Household onChanged={() => setHouseholdVersion((v) => v + 1)} />
      <Stock refreshKey={householdVersion} />
      <section id="plan">
        <h2 className="pad">Household plan</h2>
        {planQ.error && <p className="pad warning">Plan unavailable: {planQ.error}</p>}
        {planQ.data && <Html html={planQ.data.html} />}
      </section>
      <Notes />
      <Pins />
      <EventLog />
    </div>
  );
}
