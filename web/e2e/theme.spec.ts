import { test, expect } from './test';

test('theme choice persists across reloads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'field');
  await page.getByRole('button', { name: /Change the theme. Field now/ }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'mono');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'mono');
  await expect(page.getByRole('button', { name: /Change the theme. Mono now/ })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('sos.theme'))).toBe('mono');
  // Two themes and no more: the next tap comes back to the light one.
  await page.getByRole('button', { name: /Change the theme. Mono now/ }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'field');
});
