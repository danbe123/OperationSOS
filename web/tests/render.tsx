import { render } from '@testing-library/react';
import { vi } from 'vitest';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router';
import { routes } from '../src/router';
import { api, ApiError } from '../src/api/client';
import { StatusProvider } from '../src/api/status';
import { SituationProvider } from '../src/situation/SituationProvider';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { KioskProvider } from '../src/kiosk/KioskProvider';
import { status as statusFixture } from './fixtures/api';

/** Render the app's routes at a path with the real provider tree. `api.status` and `api.situationView`
 * are mocked with the fixtures unless a test mocked them first (a 404 View means "no engine here"). */
export function renderRoute(path: string, opts: { routes?: RouteObject[]; kiosk?: boolean } = {}) {
  if (!vi.isMockFunction(api.status)) vi.spyOn(api, 'status').mockResolvedValue(statusFixture);
  if (!vi.isMockFunction(api.situationView)) vi.spyOn(api, 'situationView').mockRejectedValue(new ApiError(404, 'Not Found'));
  const router = createMemoryRouter(opts.routes ?? routes, { initialEntries: [path] });
  const utils = render(
    <StatusProvider intervalMs={60_000}>
      <SituationProvider intervalMs={60_000}>
        <ThemeProvider>
          <KioskProvider force={opts.kiosk ?? false}>
            <RouterProvider router={router} />
          </KioskProvider>
        </ThemeProvider>
      </SituationProvider>
    </StatusProvider>,
  );
  return { ...utils, router };
}
