import { test as base, expect, type BrowserContext, type Page } from '@playwright/test';
import { MODE } from '../playwright.config';
import { createFixtureState, type FixtureState } from './fixtures/state';
import { installFixtureRoutes } from './fixtures/routes';

export { MODE, expect, installFixtureRoutes };

/** A service that is working is one line on the sheet until somebody asks for its form. */
export async function openCondition(page: Page, id: string) {
  const row = page.locator(`#${id}`);
  await row.waitFor();
  const change = row.getByRole('button', { name: /Change/ });
  if (await change.isVisible()) await change.click();
  await expect(row.getByRole('group')).toBeVisible();
}
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
