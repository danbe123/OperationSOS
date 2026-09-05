import { useLayoutEffect, useRef, type RefObject } from 'react';
import { Outlet, useLocation, useNavigationType, type RouteObject } from 'react-router';
import { AppBar } from './components/AppBar';
import { Notices } from './components/Notice';
import { Ai } from './screens/Ai';
import { Board } from './screens/Board';
import { Card } from './screens/Card';
import { Doc } from './screens/Doc';
import { Home } from './screens/Home';
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
import { Search } from './screens/Search';
import { Situation } from './screens/Situation';
import { Tasks } from './screens/Tasks';
import { System } from './screens/System';
import { DrillBanner } from './situation/DrillBanner';
import { Keyboard } from './kiosk/Keyboard';
import { IdleOverlay } from './kiosk/IdleOverlay';

/** Start each new screen at the top: the app scrolls inside .layout-main, so the browser never resets it for us.
 * Back and forward keep their position; a hash link scrolls to its anchor instead. */
export function useScrollToTop(main: RefObject<HTMLElement | null>) {
  const { pathname, hash } = useLocation();
  const type = useNavigationType();
  useLayoutEffect(() => {
    if (type === 'POP') return;
    if (hash) {
      const target = document.getElementById(hash.slice(1));
      if (target) { target.scrollIntoView(); return; }
    }
    if (main.current) main.current.scrollTop = 0;
    window.scrollTo(0, 0);
  }, [pathname, hash, type, main]);
}

export function Layout() {
  const main = useRef<HTMLElement>(null);
  useScrollToTop(main);
  return (
    <div className="layout">
      <DrillBanner />
      <main className="layout-main" ref={main}>
        <Outlet />
      </main>
      <Notices />
      <Keyboard />
      <IdleOverlay />
    </div>
  );
}

export function NotFound() {
  return (
    <div className="screen">
      <AppBar title="Not found" />
      <p className="pad">There is nothing at this address. Use Home or Search.</p>
    </div>
  );
}

export function RouteError() {
  return (
    <div className="screen">
      <AppBar title="Unable to open this page" back={false} search={false} />
      <section className="pad">
        <h2>Something went wrong</h2>
        <p>Try loading this page again, or return to Home to open another resource.</p>
        <button className="btn" type="button" onClick={() => window.location.reload()}>Reload page</button>
        {' '}<a className="btn" href="/">Return to Home</a>
      </section>
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <Home /> },
      { path: 'search', element: <Search /> },
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
