import { Outlet, type RouteObject } from 'react-router';
import { AppBar } from './components/AppBar';
import { Notices } from './components/Notice';
import { Card } from './screens/Card';
import { Doc } from './screens/Doc';
import { Home } from './screens/Home';
import { Library } from './screens/Library';
import { MapScreen } from './screens/Map';
import { Medical } from './screens/Medical';
import { Module } from './screens/Module';
import { Reader } from './screens/Reader';
import { Scenario } from './screens/Scenario';
import { Search } from './screens/Search';
import { Keyboard } from './kiosk/Keyboard';
import { IdleOverlay } from './kiosk/IdleOverlay';

export function Layout() {
  return (
    <div className="layout">
      <main className="layout-main">
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

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'search', element: <Search /> },
      { path: 'library', element: <Library /> },
      { path: 'map', element: <MapScreen /> },
      { path: 'medical', element: <Medical /> },
      { path: 'medical/card/:slug', element: <Card /> },
      { path: 'doc/:id', element: <Doc /> },
      { path: 'read/:id/*', element: <Reader /> },
      { path: 's/:slug', element: <Scenario /> },
      { path: 'm/:slug', element: <Module /> },
      { path: '*', element: <NotFound /> },
    ],
  },
];
