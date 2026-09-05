import { useMemo } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import { routes } from './router';
import { StatusProvider, useStatus } from './api/status';
import { SituationProvider, useSituation } from './situation/SituationProvider';
import { ThemeProvider } from './theme/ThemeProvider';
import { KioskProvider } from './kiosk/KioskProvider';
import './styles/tokens.css';
import './styles/type.css';
import './styles/shell.css';
import './styles/components.css';

function Themed() {
  const { status } = useStatus();
  const { view } = useSituation();
  const router = useMemo(() => createBrowserRouter(routes), []);
  return (
    <ThemeProvider fallback={status?.default_theme} mode={view?.modes.theme ?? null} dim={view?.modes.dim ?? false}>
      <KioskProvider>
        <RouterProvider router={router} />
      </KioskProvider>
    </ThemeProvider>
  );
}

export function App() {
  return (
    <StatusProvider>
      <SituationProvider>
        <Themed />
      </SituationProvider>
    </StatusProvider>
  );
}
