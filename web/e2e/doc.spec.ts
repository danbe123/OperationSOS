import { test, expect } from './test';

/* The fixture box carries one real two-page PDF for every /docs/core/*.pdf, and answers /docs/extended/
 * with a 404: the two states the document viewer has. The live twin of the first test (live.spec.ts) opens
 * a real medicine PDF from the installed library. */

test('a document a guide points at opens in the viewer at its page, and Back returns to the guide', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/s/grid-collapse');
  await page.getByRole('tab', { name: 'Go deeper' }).click();
  await page.getByRole('link', { name: 'National Risk Register, page 12' }).click();
  await expect(page).toHaveURL(/\/doc\/nrr-2025#page=12$/);
  await expect(page.getByRole('heading', { level: 1, name: 'National Risk Register 2025' })).toBeVisible();
  // the file is drawn by the viewer, in its frame, not left behind a toolbar with nothing in it
  const viewer = page.frameLocator('iframe[title="Document"]');
  await expect(viewer.locator('.page[data-loaded="true"]').first()).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: 'Back', exact: true }).click();
  await expect(page).toHaveURL(/\/s\/grid-collapse(\?tab=go-deeper)?$/);
  await expect(page.getByRole('tab', { name: 'Go deeper', selected: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('a document the catalogue lists and the drive does not carry says so instead of showing a blank viewer', async ({ page }) => {
  await page.goto('/doc/fm-21-76-survival');
  await expect(page.getByRole('heading', { level: 1, name: /FM 21-76 Survival/ })).toBeVisible();
  const missing = page.getByRole('region', { name: 'Not on this box' });
  await expect(missing).toContainText('The box does not have this document.');
  await expect(missing.getByRole('link', { name: 'Open the library entry' })).toHaveAttribute('href', '/library/sources/practical#item-fm-21-76-survival');
  await expect(page.locator('iframe[title="Document"]')).toHaveCount(0);
});
