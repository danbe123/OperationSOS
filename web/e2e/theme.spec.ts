import { test, expect } from './test';

test('theme choice persists across reloads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'vault');
  await page.getByRole('button', { name: /Change the theme. Vault now/ }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'field');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'field');
  await expect(page.getByRole('button', { name: /Change the theme. Field now/ })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('sos.theme'))).toBe('field');
});
