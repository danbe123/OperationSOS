import { test, expect } from './test';

/* UX audit finding: a saved pin ("Well") is the only tappable thing on its row, and its link was
 * sized to its icon and word alone — 65x31 on the kiosk, well under a finger. Everything else with a
 * single tap target (a scenario tile, a job) is checked at 44px elsewhere; the pin link was not. */
test('a saved pin is a full 44px tap, not just its icon and word', async ({ page }) => {
  await page.goto('/notes');
  const pin = page.getByRole('link', { name: 'Well' });
  await expect(pin).toBeVisible();
  const box = (await pin.boundingBox())!;
  expect(box.height).toBeGreaterThanOrEqual(44);
});
