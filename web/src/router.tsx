import type { RouteObject } from 'react-router';
import { Ai } from './screens/Ai';
import { Board } from './screens/Board';
import { Card } from './screens/Card';
import { Doc } from './screens/Doc';
import { Now } from './screens/Now';
import { Guides } from './screens/Guides';
import { Library } from './screens/Library';
import { MapScreen } from './screens/Map';
import { Medical } from './screens/Medical';
import { Module } from './screens/Module';
import { Page } from './screens/Page';
import { Plan } from './screens/Plan';
import { Tools } from './screens/Tools';
import { Fieldcraft } from './screens/Fieldcraft';
import { Timers } from './screens/tools/Timers';
import { SunMoon } from './screens/tools/SunMoon';
import { Calculators } from './screens/tools/Calculators';
import { Log } from './screens/tools/Log';
import { Dose } from './screens/tools/Dose';
import { Radio } from './screens/Radio';
import { Reader } from './screens/Reader';
import { Scenario } from './screens/Scenario';
import { Find } from './screens/Find';
import { Situation } from './screens/Situation';
import { Tasks } from './screens/Tasks';
import { System } from './screens/System';
import { Screen, Body } from './shell/Screen';
import { Shell } from './shell/Shell';

export { useScrollToTop } from './shell/Shell';

export function NotFound() {
  return (
    <Screen title="Not found">
      <Body>
        <p>There is nothing at this address.</p>
        <div className="row"><a className="btn btn-primary" href="/">Go to Now</a><a className="btn" href="/search">Search the box</a></div>
      </Body>
    </Screen>
  );
}

export function RouteError() {
  return (
    <Screen title="Unable to open this page" back={false} search={false}>
      <Body>
        <p>Try loading this page again, or go back to Now and open something else.</p>
        <div className="row">
          <button className="btn btn-primary" type="button" onClick={() => window.location.reload()}>Reload the page</button>
          <a className="btn" href="/">Go to Now</a>
        </div>
      </Body>
    </Screen>
  );
}

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Shell />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <Now /> },
      { path: 'now', element: <Now /> },
      { path: 'guides', element: <Guides /> },
      { path: 'search', element: <Find /> },
      { path: 'find', element: <Find /> },
      { path: 'library', element: <Library /> },
      { path: 'map', element: <MapScreen /> },
      { path: 'medical', element: <Medical /> },
      { path: 'medical/card/:slug', element: <Card /> },
      { path: 'radio', element: <Radio /> },
      { path: 'p/:slug', element: <Page /> },
      { path: 'plan', element: <Plan /> },
      { path: 'tools', element: <Tools /> },
      { path: 'fieldcraft', element: <Fieldcraft /> },
      { path: 'tools/timers', element: <Timers /> },
      { path: 'tools/sun', element: <SunMoon /> },
      { path: 'tools/calc', element: <Calculators /> },
      { path: 'tools/log', element: <Log /> },
      { path: 'medical/dose', element: <Dose /> },
      { path: 'doc/:id', element: <Doc /> },
      { path: 'read/:id/*', element: <Reader /> },
      { path: 's/:slug', element: <Scenario /> },
      { path: 'm/:slug', element: <Module /> },
      { path: 'situation', element: <Situation /> },
      { path: 'tasks', element: <Tasks /> },
      { path: 'board', element: <Board /> },
      { path: 'system', element: <System /> },
      { path: 'ai', element: <Ai /> },
      { path: '*', element: <NotFound /> },
    ],
  },
];
