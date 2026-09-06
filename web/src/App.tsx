import { useMemo } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import { routes } from './router';
import { StatusProvider, useStatus } from './api/status';
import { SituationProvider, useSituation } from './situation/SituationProvider';
import { isTheme, ThemeProvider, type Theme } from './theme/ThemeProvider';
import { KioskProvider } from './kiosk/KioskProvider';
import './styles/tokens.css';
import './styles/type.css';
import './styles/shell.css';
import './styles/components.css';

/** The theme the engine's modes are imposing, if it is one this build has a palette for.
 *
 * `Modes.theme` is typed as one of the two, but it arrives over the wire from a box that may be
 * older than this bundle and reads rules that travel on a stick: a modes rule written for the
 * three-theme world still says `theme: vault`. Stamped on `<html>`, that is a document with no
 * palette at all — so an unknown theme is no theme, and the reader keeps the one they were on. The
 * API guards the same value on the way out; this is the half that cannot be talked round. */
export function modeTheme(view: { modes: { theme: string | null } } | null): Theme | null {
  return isTheme(view?.modes.theme) ? view.modes.theme : null;
}

function Themed() {
  const { status } = useStatus();
  const { view } = useSituation();
  const router = useMemo(() => createBrowserRouter(routes), []);
  return (
    <ThemeProvider fallback={status?.default_theme} mode={modeTheme(view)} dim={view?.modes.dim ?? false}>
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
