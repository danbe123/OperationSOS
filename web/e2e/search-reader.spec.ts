import { test, expect } from './test';

test('Home -> search -> open an article in the reader', async ({ page }) => {
  await page.goto('/');
  const search = page.getByRole('combobox', { name: 'Search' }).first();
  await search.fill('water');
  await search.press('Enter');
  await expect(page).toHaveURL(/\/search\?q=water$/);
  // Results are grouped by where they came from, the box's own guidance first.
  await expect(page.getByRole('region', { name: 'From this box' })).toBeVisible();
  const results = page.getByRole('region', { name: /^Wikipedia/ });
  await expect(results.getByRole('listitem')).not.toHaveCount(0);
  await results.getByRole('link', { name: /\bWater\b/ }).first().click();
  await expect(page).toHaveURL(/\/read\/wikipedia_en_100_mini_2026-01\/A\/Water$/);
  const frame = page.frameLocator('iframe[title="Article"]');
  await expect(frame.getByRole('heading', { name: 'Water' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Water' })).toBeVisible();
});
