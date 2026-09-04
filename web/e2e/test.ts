import { test as base, expect, type BrowserContext } from '@playwright/test';
import { MODE } from '../playwright.config';
import { createFixtureState, type FixtureState } from './fixtures/state';
import { installFixtureRoutes } from './fixtures/routes';

export { MODE, expect, installFixtureRoutes };
export type { FixtureState };

/** Every spec gets a fresh fixture state; in fixture mode the context's requests are answered from it. */
export const test = base.extend<{ state: FixtureState; withFixtures: (context: BrowserContext) => Promise<void> }>({
  // eslint-disable-next-line no-empty-pattern
  state: async ({}, use) => { await use(createFixtureState()); },
  withFixtures: async ({ state }, use) => {
    await use(async (context: BrowserContext) => { if (MODE === 'fixture') await installFixtureRoutes(context, state); });
  },
  context: async ({ context, withFixtures }, use) => {
    await withFixtures(context);
    await use(context);
  },
});
