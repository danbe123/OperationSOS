import { useMemo } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import { routes } from './router';
import { StatusProvider, useStatus } from './api/status';
import { ThemeProvider } from './theme/ThemeProvider';
import { KioskProvider } from './kiosk/KioskProvider';
import './app.css';
import './screens/home.css';

function Themed() {
  const { status } = useStatus();
  const router = useMemo(() => createBrowserRouter(routes), []);
  return (
    <ThemeProvider fallback={status?.default_theme}>
      <KioskProvider>
        <RouterProvider router={router} />
      </KioskProvider>
    </ThemeProvider>
  );
}

export function App() {
  return (
    <StatusProvider>
      <Themed />
    </StatusProvider>
  );
}
