import { render } from '@testing-library/react';
import { vi } from 'vitest';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router';
import { routes } from '../src/router';
import { api } from '../src/api/client';
import { StatusProvider } from '../src/api/status';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { status as statusFixture } from './fixtures/api';

/** Render the app's routes at a path with the real provider tree. `api.status` is mocked with the fixture unless a test mocked it first. */
export function renderRoute(path: string, opts: { routes?: RouteObject[] } = {}) {
  if (!vi.isMockFunction(api.status)) vi.spyOn(api, 'status').mockResolvedValue(statusFixture);
  const router = createMemoryRouter(opts.routes ?? routes, { initialEntries: [path] });
  const utils = render(
    <StatusProvider intervalMs={60_000}>
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </StatusProvider>,
  );
  return { ...utils, router };
}
