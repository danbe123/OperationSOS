import { test, expect } from './test';

/* A quick card is read at arm's length, in the dark, by someone kneeling over a body: the call is
 * the first thing on the screen, one step is on the screen at a time at the display size (40 px),
 * and Next turns to the next one. The size never depends on how many steps the card has. */

for (const viewport of [{ width: 853, height: 480 }, { width: 360, height: 640 }]) {
  test(`quick card steps are display-sized, one at a time, and lead with 999 at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/medical/card/cpr-adult');
    await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

    // the call is above the first step, and it is the one 999 component the whole box uses
    const call = page.locator('.emergency-999');
    await expect(call).toHaveCount(1);
    await expect(call).toContainText('call 999');
    const first = page.locator('.card-paged li').first();
    await expect(first).toBeVisible();
    await expect(page.locator('.card-paged li')).toHaveCount(1);
    await expect(page.locator('.card-count')).toContainText('Step 1 of 8');
    expect((await call.boundingBox())!.y).toBeLessThan((await first.boundingBox())!.y);

    // The step and its number are the display size — unless this one step will not fit its frame,
    // in which case it drops to the lead size and stops there. Never the body size.
    const stepSize = await first.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(stepSize).toBeGreaterThanOrEqual(22);
    const tight = await page.locator('.card-scroll').evaluate((el) => el.classList.contains('card-steps-tight'));
    if (!tight) expect(stepSize).toBeGreaterThanOrEqual(40);
    const numberSize = await first.evaluate((el) => parseFloat(getComputedStyle(el, '::before').fontSize));
    expect(numberSize).toBe(stepSize);
    expect(await first.evaluate((el) => getComputedStyle(el, '::before').fontWeight)).toBe(await first.evaluate((el) => getComputedStyle(el).fontWeight));

    // the whole step is on the screen without scrolling, and nothing runs off the side
    const box = (await first.boundingBox())!;
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

    // "When to use" rides under step one, and the card's own list heading is not left as an orphan
    await expect(page.locator('.card-aside')).toContainText('When to use');
    await expect(page.locator('.card-aside')).not.toContainText('Steps');

    // Next turns the page; the warnings wait for the last step, where they are what happens next
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await expect(page.locator('.card-count')).toContainText('Step 2 of 8');
    await expect(first).toContainText('defibrillator');
    await expect(page.locator('.card-aside')).toHaveCount(0);

    // and every step at once, at the lead size, for the reader who wants the list
    await page.getByRole('button', { name: 'All steps' }).click();
    await expect(page.locator('.card-html ol li')).toHaveCount(8);
    const allSize = await page.locator('.card-html ol li').first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(allSize).toBeGreaterThanOrEqual(22);
    const warning = page.locator('.card-html .warning').first();
    await expect(warning).toContainText('Gasping');
    expect(await warning.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeLessThanOrEqual(allSize);
  });
}

test('the card says which step this is, and the rate is one turn away at 390', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/medical/card/cpr-adult');
  await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

  // The card's own name is the screen's title, at the title size, not below the size of its steps.
  const titleSize = await page.getByRole('heading', { level: 1 }).evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(titleSize).toBeGreaterThanOrEqual(28);

  // The count says where you are, on one line, with Previous and Next beside it.
  await expect(page.locator('.card-count')).toContainText('Step 1 of 8');
  await expect(page.getByRole('button', { name: 'Previous', exact: true })).toBeDisabled();

  // The answer the card exists for — 100 to 120 a minute — is step four, and it fits the screen.
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.locator('.card-count')).toContainText('Step 4 of 8');
  const rate = page.locator('.card-paged li').getByText('100 to 120', { exact: false });
  const box = (await rate.boundingBox())!;
  expect(box.y + box.height).toBeLessThanOrEqual(844);
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
  const step = page.locator('.card-paged li');
  await expect(step).not.toContainText('call 999.');
  await expect(step).toContainText('999 will not connect');
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(step).toContainText('Send someone');
  // And the rate is still two turns further on, on the screen.
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.locator('.card-count')).toContainText('Step 4 of 8');
  const rate = (await step.getByText('100 to 120', { exact: false }).boundingBox())!;
  expect(rate.y + rate.height).toBeLessThanOrEqual(844);
});
