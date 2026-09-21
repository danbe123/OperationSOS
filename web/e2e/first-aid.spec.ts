import { test, expect } from './test';

/** The design rule: every quick card is at most two taps from Home. Medical lives in the Library now, so Now,
 * Library, Medical, card was three; the First aid tile on Now is the second tap's shortcut. */
for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
  test(`a quick card is two taps from Now: First aid, then the card, at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');
    const grid = page.getByRole('navigation', { name: 'Scenarios' });
    const aid = grid.getByRole('link', { name: /First aid/ });
    await aid.scrollIntoViewIfNeeded();
    await expect(aid).toBeVisible();
    await expect(aid).toContainText('Quick cards');
    // the same tile as its neighbours: same size, same touch target, first in the grid: a quick card must not sit below twenty scenarios
    const first = grid.getByRole('link').first();
    await expect(first).toContainText('First aid');
    const neighbour = grid.getByRole('link', { name: /National grid collapse/ });
    const [a, n] = [(await aid.boundingBox())!, (await neighbour.boundingBox())!];
    expect(a.height).toBeGreaterThanOrEqual(44);   // a touch target
    expect(Math.abs(a.width - n.width)).toBeLessThanOrEqual(1);
    expect(await aid.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe(await neighbour.evaluate((el) => getComputedStyle(el).backgroundColor));
    await page.screenshot({ path: `/tmp/recovery-shot-firstaid-${viewport.width}.png` });

    await aid.click();                                                  // tap 1
    await expect(page).toHaveURL(/\/library\/medical$/);
    await page.getByRole('navigation', { name: 'Quick cards' }).getByRole('link', { name: /CPR/ }).first().click();   // tap 2
    await expect(page).toHaveURL(/\/medical\/card\/cpr-adult$/);
    await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();
  });
}

test('the situation tiles and the services row behave as before with First aid beside them', async ({ page }) => {
  await page.goto('/');
  const grid = page.getByRole('navigation', { name: 'Scenarios' });
  await grid.getByRole('link', { name: /National grid collapse/ }).click();
  await expect(page).toHaveURL(/\/s\/grid-collapse$/);
  await page.goBack();
  await page.getByRole('button', { name: /^Mains power: on/ }).click();
  await expect(page.getByRole('button', { name: /^Mains power: off/ })).toBeVisible();
  await expect(grid.getByRole('link', { name: /First aid/ })).toBeVisible();
});
