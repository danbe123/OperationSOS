import { test, expect } from './test';

/* The kiosk's number pad. simple-keyboard's own stylesheet gives every key in the numeric layout
 * `width: 33.3%`, and that layout has four keys a row, so the rows came out a third too wide and
 * the left column — 1, 4 and 7 — was thrown off the screen along with "done". */

test('the number pad shows every digit and its done key, and keeps the answer in view', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  await page.goto('/medical/dose?kiosk=1');
  await page.getByLabel('Years').click();
  const pad = page.getByTestId('keyboard');
  await expect(pad).toBeVisible();

  const panel = (await page.locator('.kb-panel').boundingBox())!;
  for (const key of ['1', '4', '7', '0', 'done ▾']) {
    const button = pad.locator(`.hg-button[data-skbtn="${key === 'done ▾' ? '{done}' : key}"]`);
    await expect(button).toBeVisible();
    const box = (await button.boundingBox())!;
    expect(box.x, key).toBeGreaterThanOrEqual(panel.x - 1);
    expect(box.x + box.width, key).toBeLessThanOrEqual(panel.x + panel.width + 1);
    expect(box.width, key).toBeGreaterThanOrEqual(48);
  }

  // typing an age gives the dose, and the dose is above the pad rather than under it
  await pad.locator('.hg-button[data-skbtn="4"]').click();
  const dose = page.locator('.dose-result');
  await expect(dose).toContainText('mg');
  const answer = (await dose.boundingBox())!;
  expect(answer.y).toBeLessThan(panel.y);

  // "done ▾" reads in full and closes the pad
  await expect(pad.locator('.hg-button[data-skbtn="{done}"]')).toHaveText('done ▾');
  await pad.locator('.hg-button[data-skbtn="{done}"]').click();
  await expect(page.getByTestId('keyboard')).toBeHidden();
});
