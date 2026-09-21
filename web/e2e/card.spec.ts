import { test, expect } from './test';

/* A quick card is read at arm's length, in the dark, by someone kneeling over a body. It is one sheet,
 * not a slideshow (web: "quick cards are one sheet"): the call to 999 is the first thing on the screen,
 * then when to use the card, then every step at once with the first three set at the step size, then the
 * warnings, one to a line, and what to do when nobody is coming. Nothing to turn: the sheet scrolls, and
 * the fade at its foot says there is more. The size never depends on how many steps the card has. */

const NEXT = (page: import('@playwright/test').Page) => page.getByRole('button', { name: /^(Next|Previous)/ });

for (const viewport of [{ width: 853, height: 480 }, { width: 360, height: 640 }]) {
  test(`the quick card is one sheet: the call first, the first three steps large, nothing to turn at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/medical/card/cpr-adult');
    await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

    // the call is above the first step, and it is the one 999 component the whole box uses
    const call = page.locator('.emergency-999');
    await expect(call).toHaveCount(1);
    await expect(call).toContainText('call 999');
    const steps = page.getByRole('list', { name: 'Steps' }).getByRole('listitem');
    await expect(steps).toHaveCount(8);
    const first = steps.first();
    await expect(first).toBeVisible();
    expect((await call.boundingBox())!.y).toBeLessThan((await first.boundingBox())!.y);

    // Nothing to turn: there is no pager and no step counter, and the steps are the card's own, in order.
    await expect(NEXT(page)).toHaveCount(0);
    await expect(page.getByText(/Step \d of \d/)).toHaveCount(0);
    await expect(first).toContainText('call 999');
    await expect(steps.nth(1)).toContainText('defibrillator');
    await expect(steps.nth(3)).toContainText('100 to 120');

    // The first three are the ones read from a standing start: bold, at the step size (never the body
    // size), with the numeral in the same face and weight beside them. The other five are the lead size.
    const size = (loc: typeof first) => loc.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    const stepSize = viewport.width >= 700 ? 28 : 25;
    for (const i of [0, 1, 2]) {
      await expect(steps.nth(i)).toHaveClass(/card-step-lead/);
      expect(await size(steps.nth(i)), `step ${i + 1}`).toBe(stepSize);
      expect(await steps.nth(i).evaluate((el) => getComputedStyle(el).fontWeight)).toBe('700');
    }
    for (const i of [3, 4, 5, 6, 7]) {
      await expect(steps.nth(i)).not.toHaveClass(/card-step-lead/);
      expect(await size(steps.nth(i)), `step ${i + 1}`).toBe(22);
    }
    // the numeral is bigger than its step and stands in the margin: it is drawn, not typed into the text
    expect(await first.evaluate((el) => parseFloat(getComputedStyle(el, '::before').fontSize))).toBeGreaterThan(stepSize);
    expect(await first.evaluate((el) => getComputedStyle(el, '::before').content)).toBe('counter(step)');

    // the first step is whole on the screen without scrolling, and nothing runs off the side
    const box = (await first.boundingBox())!;
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const frame = page.locator('.card-scroll');
    expect(await frame.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);

    // "When to use" is the line above the steps, and the card's own list heading is not left as an orphan
    const when = page.locator('.card-when');
    await expect(when).toContainText('Someone has collapsed');
    expect((await when.boundingBox())!.y).toBeLessThan(box.y);
    await expect(page.getByRole('heading', { name: 'Steps' })).toHaveCount(0);

    // The sheet is longer than its frame, says so with the fade, and scrolls to the rest: each warning is a line of its own…
    await expect(frame).toHaveClass(/card-scroll-more/);
    expect(await frame.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    const warnings = page.locator('.card-warnings .card-warning');
    await expect(warnings).toHaveCount(2);
    await expect(warnings.first()).toContainText('Gasping, snoring or occasional gulps');
    await expect(warnings.nth(1)).toContainText('Broken ribs are common');
    await warnings.nth(1).scrollIntoViewIfNeeded();
    await expect(warnings.nth(1)).toBeInViewport();
    // …and what to do when nobody is coming is the last thing on it, at the end of the scroll
    const escalate = page.getByRole('region', { name: 'Stop or escalate' });
    await escalate.scrollIntoViewIfNeeded();
    await expect(escalate).toBeInViewport();
    await expect(escalate).toContainText('a paramedic takes over');
    await expect(frame).not.toHaveClass(/card-scroll-more/);
  });
}

test('the card says what it is at the title size, and the rate is a scroll away at 390', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/medical/card/cpr-adult');
  await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

  // The card's own name is the screen's title, at the title size, not below the size of its steps.
  const titleSize = await page.getByRole('heading', { level: 1 }).evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(titleSize).toBeGreaterThanOrEqual(28);

  // The three lead steps are on the screen together.
  const steps = page.getByRole('list', { name: 'Steps' }).getByRole('listitem');
  for (const i of [0, 1, 2]) await expect(steps.nth(i)).toBeInViewport();

  // The answer the card exists for — 100 to 120 a minute — is step four, the first one at reading size,
  // and it is on the sheet in its own line: one scroll and it is on the screen.
  const rate = steps.nth(3);
  await expect(rate).toContainText('100 to 120');
  await rate.scrollIntoViewIfNeeded();
  await expect(rate).toBeInViewport({ ratio: 1 });
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
  const steps = page.getByRole('list', { name: 'Steps' }).getByRole('listitem');
  await expect(steps).toHaveCount(8);
  await expect(steps.first()).not.toContainText('call 999');
  await expect(steps.first()).toContainText('999 will not connect');
  await expect(page.getByText('call 999', { exact: false })).toHaveCount(0);
  // The second step is the same as it was with the phones up, and the rate is still step four.
  await expect(steps.nth(1)).toContainText('defibrillator');
  await expect(steps.nth(3)).toContainText('100 to 120');
});

test('a card with the phones down sends someone instead of ringing', async ({ page, state }) => {
  const hour = new Date(Date.now() - 3_600_000).toISOString();
  for (const id of ['mobile', 'landline'] as const) {
    state.conditions = { ...state.conditions, [id]: { ...state.conditions[id], state: 'off', since: hour, set_by: 'phone' } };
  }
  await page.goto('/medical/card/severe-bleeding');
  const steps = page.getByRole('list', { name: 'Steps' }).getByRole('listitem');
  await expect(steps.nth(1)).toContainText('Send someone to a landline');
  await expect(steps.nth(1)).toContainText('999 will not connect from here');
});
