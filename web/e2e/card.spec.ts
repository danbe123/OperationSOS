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

    // The steps and their numbers are the display size, one step to a line — unless the card has
    // had to give up a size to keep its first three steps on the screen, which is what a reader
    // kneeling over a body actually needs. Never below the lead size.
    const stepSize = await first.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(stepSize).toBeGreaterThanOrEqual(22);
    const tight = await page.locator('.card-scroll').evaluate((el) => el.classList.contains('card-steps-tight') || el.classList.contains('card-steps-tighter'));
    if (!tight) expect(stepSize).toBeGreaterThanOrEqual(40);
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
      expect(size).toBeLessThanOrEqual(stepSize);
    }

    // the first step is on the screen without scrolling, and nothing runs off the side
    const box = (await first.boundingBox())!;
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test('the card says how many steps there are, and the rate is on the screen at 390', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/medical/card/cpr-adult');
  await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

  // The card's own name is the screen's title, at the title size, not below the size of its steps.
  const titleSize = await page.getByRole('heading', { level: 1 }).evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(titleSize).toBeGreaterThanOrEqual(28);

  // A card that carries on says so: the count, and a way down that is not a guess.
  await expect(page.locator('.card-count')).toContainText('4 steps');

  // The answer the card exists for is on the screen without scrolling: 100 to 120 a minute.
  const rate = page.getByText('100 to 120 a minute', { exact: false });
  const box = (await rate.boundingBox())!;
  expect(box.y + box.height).toBeLessThanOrEqual(844);
  // Steps 1 to 3 are all on the first screen with it.
  for (const i of [0, 1, 2]) {
    const step = (await page.locator('.card-html ol li').nth(i).boundingBox())!;
    expect(step.y + step.height, `step ${i + 1}`).toBeLessThanOrEqual(844);
  }
});

test('with the phones down the card does not tell you to ring, and says it once', async ({ page, state }) => {
  const hour = new Date(Date.now() - 3_600_000).toISOString();
  for (const id of ['mobile', 'landline'] as const) {
    state.conditions = { ...state.conditions, [id]: { ...state.conditions[id], state: 'off', since: hour, set_by: 'phone' } };
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/medical/card/cpr-adult');
  // One 999 panel on the screen, and no step under it telling somebody to ring anyway.
  await expect(page.locator('.emergency-999')).toHaveCount(1);
  await expect(page.locator('.emergency-999')).toContainText('999 will not connect');
  await expect(page.locator('.card-html')).not.toContainText('Call 999');
  await expect(page.locator('.card-html')).toContainText('Send someone');
  // And the rate is still on the screen.
  const rate = (await page.getByText('100 to 120 a minute', { exact: false }).boundingBox())!;
  expect(rate.y + rate.height).toBeLessThanOrEqual(844);
});
