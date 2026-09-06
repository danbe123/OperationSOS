import { test, expect } from './test';

/* A quick card is read at arm's length, in the dark, by someone kneeling over a body: the call is
 * the first thing on the screen and the first compression is the second, and the steps run at the
 * display size (40 px), not at the size of a paragraph on Guides. */

for (const viewport of [{ width: 853, height: 480 }, { width: 360, height: 640 }]) {
  test(`quick card steps are display-sized and lead with 999 at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/medical/card/cpr-adult');
    await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

    // the call is above the first step, and it is the one 999 component the whole box uses
    const call = page.locator('.emergency-999');
    await expect(call).toHaveCount(1);
    await expect(call).toContainText('call 999');
    const first = page.locator('.card-html ol li').first();
    expect((await call.boundingBox())!.y).toBeLessThan((await first.boundingBox())!.y);

    // the steps and their numbers are the display size, one step to a line
    const stepSize = await first.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(stepSize).toBeGreaterThanOrEqual(40);
    const numberSize = await first.evaluate((el) => parseFloat(getComputedStyle(el, '::before').fontSize));
    expect(numberSize).toBe(stepSize);
    const numberWeight = await first.evaluate((el) => getComputedStyle(el, '::before').fontWeight);
    const stepWeight = await first.evaluate((el) => getComputedStyle(el).fontWeight);
    expect(numberWeight).toBe(stepWeight);

    // the warning stays at the lead size, below the steps
    const warning = page.locator('.card-html .warning');
    if (await warning.count()) {
      const size = await warning.first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
      expect(size).toBeGreaterThanOrEqual(22);
      expect(size).toBeLessThan(stepSize);
    }

    // the first step is on the screen without scrolling, and nothing runs off the side
    const box = (await first.boundingBox())!;
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
