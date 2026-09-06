import { test as base, expect, type BrowserContext, type Page } from '@playwright/test';
import { MODE } from '../playwright.config';
import { createFixtureState, type FixtureState } from './fixtures/state';
import { installFixtureRoutes } from './fixtures/routes';

export { MODE, expect, installFixtureRoutes };

/** Say a service has changed, the way a household does: the state on the row, when it started, Save.
 * There is no "Change" button in front of the states any more. */
export async function setCondition(page: Page, id: string, state: string, since = 'Just now') {
  const row = page.locator(`#${id}`);
  await row.waitFor();
  await row.getByRole('group').first().getByRole('button', { name: state, exact: true }).click();
  const when = row.getByRole('group', { name: /since when\?$/ });
  await when.getByRole('button', { name: since, exact: true }).click();
  await when.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(row.getByRole('group').first().getByRole('button', { name: state, exact: true })).toHaveAttribute('aria-pressed', 'true');
}

/** What the box knows beyond the state — who set it, the note, the day-old prompt — is behind Details. */
export async function openDetails(page: Page, id: string) {
  const row = page.locator(`#${id}`);
  await row.waitFor();
  const details = row.getByRole('button', { name: /^Details/ });
  if ((await details.getAttribute('aria-expanded')) !== 'true') await details.click();
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
