import { test, expect } from './test';

test('theme choice persists across reloads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'vault');
  await page.getByRole('button', { name: 'Theme: Vault' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'field');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'field');
  await expect(page.getByRole('button', { name: 'Theme: Field' })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('sos.theme'))).toBe('field');
});
