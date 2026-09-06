import { test, expect } from './test';

for (const viewport of [{ width: 853, height: 480 }, { width: 360, height: 640 }]) {
  test(`quick card title and first three steps fit at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/medical/card/cpr-adult');
    const title = page.getByRole('heading', { level: 1, name: 'CPR (adult)' });
    await expect(title).toBeVisible();
    const third = page.locator('.card-html ol li').nth(2);
    await expect(third).toBeVisible();
    const box = await third.boundingBox();
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
    // a quick card is read at arm's length: the one place prose runs at the lead size or bigger
    const fontSize = await third.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(fontSize).toBeGreaterThanOrEqual(22);
  });
}
