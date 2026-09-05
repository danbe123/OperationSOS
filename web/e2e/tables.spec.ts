import { test, expect } from './test';

test('tables use the desktop width and scroll independently on phones', async ({ page }) => {
  await page.route('**/api/pages/table-layout', (route) => route.fulfill({ json: {
    slug: 'table-layout', title: 'Table layout',
    html: '<h2>Comparison</h2><table><thead><tr><th>Method</th><th>Amount</th><th>Wait</th><th>Use</th><th>Limitations</th></tr></thead><tbody><tr><td>Example method</td><td>See instructions</td><td>See instructions</td><td>A detailed description of the intended use.</td><td><a href="/p/water-disinfection">Read the full guidance</a></td></tr></tbody></table><p>Supporting guidance below the table.</p>',
  } }));
  await page.setViewportSize({ width: 1678, height: 1000 });
  await page.goto('/p/table-layout');
  const table = page.getByRole('table');
  await expect(table).toBeVisible();
  expect((await table.boundingBox())!.width).toBeGreaterThan(1500);
  await page.setViewportSize({ width: 390, height: 844 });
  const region = page.getByRole('region', { name: /Comparison table/ });
  expect(await region.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await region.focus();
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => region.evaluate((el) => el.scrollLeft)).toBeGreaterThan(0);
  await table.getByRole('link').click();
  await expect(page).toHaveURL(/\/p\/water-disinfection$/);
});
