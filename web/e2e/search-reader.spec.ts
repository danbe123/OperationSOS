import { test, expect } from './test';

test('Home -> search -> open an article in the reader', async ({ page }) => {
  await page.goto('/');
  const search = page.getByRole('combobox', { name: 'Search' }).first();
  await search.fill('water');
  await search.press('Enter');
  await expect(page).toHaveURL(/\/search\?q=water$/);
  const results = page.getByRole('list', { name: 'Results' });
  await expect(results.getByRole('listitem')).not.toHaveCount(0);
  await results.getByRole('link', { name: /Wikipedia\s*Water/ }).click();
  await expect(page).toHaveURL(/\/read\/wikipedia_en_100_mini_2026-01\/A\/Water$/);
  const frame = page.frameLocator('iframe[title="Article"]');
  await expect(frame.getByRole('heading', { name: 'Water' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Water' })).toBeVisible();
});
