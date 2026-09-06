import { lazy, Suspense, type ReactNode } from 'react';
import type { RouteObject } from 'react-router';
import { Board } from './screens/Board';
import { Card } from './screens/Card';
import { Now } from './screens/Now';
import { Guides } from './screens/Guides';
import { Kit } from './screens/Kit';
import { Kits } from './screens/Kits';
import { Library } from './screens/Library';
import { Medical } from './screens/Medical';
import { Module } from './screens/Module';
import { Page } from './screens/Page';
import { Tools } from './screens/Tools';
import { Fieldcraft } from './screens/Fieldcraft';
import { Timers } from './screens/tools/Timers';
import { Calculators } from './screens/tools/Calculators';
import { Log } from './screens/tools/Log';
import { Dose } from './screens/tools/Dose';
import { Radio } from './screens/Radio';
import { Scenario } from './screens/Scenario';
import { Find } from './screens/Find';
import { Situation } from './screens/Situation';
import { Tasks } from './screens/Tasks';
import { System } from './screens/System';
import { Screen, Body } from './shell/Screen';
import { Shell } from './shell/Shell';

/* Four things in this box are large and rarely opened: the map (MapLibre and the tile reader), the
 * document viewer (the PDF frame and the EPUB reader), and the assistant. A kiosk booting to Now
 * used to parse all of them before it painted a single job. They are fetched when somebody asks for
 * them instead, behind one plain line of text — on a box with no network the chunk is on the same
 * disk as the page, so the wait is a blink. */
const MapScreen = lazy(() => import('./screens/Map').then((m) => ({ default: m.MapScreen })));
const Doc = lazy(() => import('./screens/Doc').then((m) => ({ default: m.Doc })));
const Reader = lazy(() => import('./screens/Reader').then((m) => ({ default: m.Reader })));
const Ai = lazy(() => import('./screens/Ai').then((m) => ({ default: m.Ai })));
/* The other two that carry weight: the plan's pins and the sun times both read grid references, and
 * `proj4` is 108 kB of the front door for two screens nobody opens in the first minute. */
const Plan = lazy(() => import('./screens/Plan').then((m) => ({ default: m.Plan })));
const People = lazy(() => import('./screens/plan/People').then((m) => ({ default: m.People })));
const NeighboursScreen = lazy(() => import('./screens/plan/NeighboursScreen').then((m) => ({ default: m.NeighboursScreen })));
const NotesScreen = lazy(() => import('./screens/plan/NotesScreen').then((m) => ({ default: m.NotesScreen })));
const PlanPage = lazy(() => import('./screens/plan/PlanPage').then((m) => ({ default: m.PlanPage })));
const SunMoon = lazy(() => import('./screens/tools/SunMoon').then((m) => ({ default: m.SunMoon })));

/** What a screen looks like while its own code is being read off the disk. It is a screen, not a
 * spinner: the title is already the answer to "where am I", and the rail never went anywhere. */
function Loading({ title, children }: { title: string; children?: ReactNode }) {
  return <Screen title={title} search={false}><Body><p className="muted">{children ?? 'Opening…'}</p></Body></Screen>;
}

function Later({ title, children }: { title: string; children: ReactNode }) {
  return <Suspense fallback={<Loading title={title} />}>{children}</Suspense>;
}

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
      { path: 'kit', element: <Kits /> },
      { path: 'kit/:slug', element: <Kit /> },
      { path: 'search', element: <Find /> },
      { path: 'find', element: <Find /> },
      { path: 'library', element: <Library /> },
      { path: 'map', element: <Later title="Map"><MapScreen /></Later> },
      { path: 'medical', element: <Medical /> },
      { path: 'medical/card/:slug', element: <Card /> },
      { path: 'radio', element: <Radio /> },
      { path: 'p/:slug', element: <Page /> },
      { path: 'plan', element: <Later title="Household"><Plan /></Later> },
      { path: 'plan/people', element: <Later title="People"><People /></Later> },
      { path: 'plan/neighbours', element: <Later title="Neighbours"><NeighboursScreen /></Later> },
      { path: 'plan/notes', element: <Later title="Notes and pins"><NotesScreen /></Later> },
      { path: 'plan/plan', element: <Later title="The plan"><PlanPage /></Later> },
      { path: 'tools', element: <Tools /> },
      { path: 'fieldcraft', element: <Fieldcraft /> },
      { path: 'tools/timers', element: <Timers /> },
      { path: 'tools/sun', element: <Later title="Sun and moon"><SunMoon /></Later> },
      { path: 'tools/calc', element: <Calculators /> },
      { path: 'tools/log', element: <Log /> },
      { path: 'medical/dose', element: <Dose /> },
      { path: 'doc/:id', element: <Later title="Document"><Doc /></Later> },
      { path: 'read/:id/*', element: <Later title="Reading"><Reader /></Later> },
      { path: 's/:slug', element: <Scenario /> },
      { path: 'm/:slug', element: <Module /> },
      { path: 'situation', element: <Situation /> },
      { path: 'tasks', element: <Tasks /> },
      { path: 'board', element: <Board /> },
      { path: 'system', element: <System /> },
      { path: 'ai', element: <Later title="Assistant"><Ai /></Later> },
      { path: '*', element: <NotFound /> },
    ],
  },
];
