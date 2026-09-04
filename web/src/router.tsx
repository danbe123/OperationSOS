import { Outlet, type RouteObject } from 'react-router';
import { AppBar } from './components/AppBar';
import { Notices } from './components/Notice';
import { Home } from './screens/Home';

export function Layout() {
  return (
    <div className="layout">
      <main className="layout-main">
        <Outlet />
      </main>
      <Notices />
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
      { path: '*', element: <NotFound /> },
    ],
  },
];
