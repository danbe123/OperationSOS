import { useState } from 'react';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Html } from '../components/Html';
import { PrintButton } from '../components/PrintButton';
import { Screen, Body } from '../shell/Screen';
import { EventLog } from './plan/EventLog';
import { Household } from './plan/Household';
import { Neighbours, StreetListLink } from './plan/Neighbours';
import { Notes } from './plan/Notes';
import { Pins } from './plan/Pins';
import { Stock } from './plan/Stock';

const JUMPS = [
  { to: '#household', title: 'Household' },
  { to: '#neighbours', title: 'Neighbours' },
  { to: '#stock', title: 'Stock' },
  { to: '#plan', title: 'The plan' },
  { to: '#notes', title: 'Notes' },
  { to: '#pins', title: 'Pins' },
  { to: '#log', title: 'Event log' },
];

export function Plan() {
  const planQ = useQuery(() => api.page('household-plan'), []);
  const [householdVersion, setHouseholdVersion] = useState(0);   // stock days-left depend on the household size
  return (
    <Screen title="Household" actions={<PrintButton />}>
      <Body>
        <nav className="chips no-print" aria-label="Plan sections">
          {JUMPS.map((j) => <a className="chip" key={j.to} href={j.to}>{j.title}</a>)}
        </nav>
        <section className="panel" id="household" aria-label="Household">
          <h2>Household</h2>
          <Household onChanged={() => setHouseholdVersion((v) => v + 1)} />
        </section>
        <section className="panel" id="neighbours" aria-label="Neighbours">
          <div className="panel-head"><h2>Neighbours</h2><StreetListLink /></div>
          <Neighbours />
        </section>
        <Stock refreshKey={householdVersion} />
        <section className="panel" id="plan" aria-label="The plan">
          <h2>The plan</h2>
          {planQ.error && <p className="warning">The plan is unavailable: {planQ.error}</p>}
          {planQ.data && <Html html={planQ.data.html} />}
        </section>
        <section className="panel" id="notes" aria-label="Shared notes">
          <h2>Shared notes</h2>
          <Notes />
        </section>
        <section className="panel" id="pins" aria-label="Pins on the map">
          <h2>Pins on the map</h2>
          <Pins />
        </section>
        <EventLog />
      </Body>
    </Screen>
  );
}
