import { test, expect } from './test';

/* Round 3 weighed the box with a keyboard and with a phone. On the kiosk the first job's tick box
 * was the seventeenth tab stop — a decorative wordmark, eight rail links, the theme button and three
 * band links first, on every screen, every time. On a phone the bottom bar is drawn last and read
 * first, and no screen but Find carried a search field at all. */

test('the first tab stop is a way past the furniture, on every screen', async ({ page, state }) => {
  const hour = new Date(Date.now() - 3_600_000).toISOString();
  state.conditions = { ...state.conditions, power: { ...state.conditions.power, state: 'off', since: hour, set_by: 'phone' } };
  for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    await expect(page.getByRole('region', { name: 'Right now' })).toBeVisible();

    // Tab 1 is the skip link, and it is visible the moment it has focus.
    await page.keyboard.press('Tab');
    const skip = page.getByRole('link', { name: 'Skip to what to do' });
    await expect(skip).toBeFocused();
    const box = (await skip.boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.height).toBeGreaterThanOrEqual(48);

    // Following it puts focus on the screen itself, named after the screen.
    await page.keyboard.press('Enter');
    const main = page.locator('main#main');
    await expect(main).toBeFocused();
    const label = await main.getAttribute('aria-label');
    expect(label).toBe(await page.getByRole('heading', { level: 1 }).textContent());

    // And from there the first job is a handful of stops away, not seventeen.
    let stops = 0;
    for (; stops < 8; stops += 1) {
      await page.keyboard.press('Tab');
      const isCheck = await page.evaluate(() => document.activeElement?.getAttribute('type') === 'checkbox');
      if (isCheck) break;
    }
    expect(stops, `${viewport.width}: stops to the first job`).toBeLessThan(8);
  }
});

test('the wordmark is not a second Now, and the navigation is read after the content', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  await page.goto('/');
  // The wordmark is decoration over the destination below it: it stays on the screen, out of the
  // tab order.
  await expect(page.locator('.rail-brand')).toHaveAttribute('tabindex', '-1');
  // The rail is drawn on the left and comes after the content in the DOM.
  const order = await page.evaluate(() => {
    const nav = document.querySelector('nav.mainnav')!;
    const main = document.querySelector('main#main')!;
    return main.compareDocumentPosition(nav) & Node.DOCUMENT_POSITION_FOLLOWING ? 'nav after main' : 'nav before main';
  });
  expect(order).toBe('nav after main');
});

test('every phone screen carries a search, and the theme control is not a destination', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  // Every screen: the field where the screen has room for it, and the way to Find where it has not.
  // Both are in the screen head, both are 48 px, and before this round a phone had neither.
  for (const route of ['/', '/medical', '/tasks', '/library', '/tools', '/guides', '/medical/card/cpr-adult', '/situation', '/map']) {
    await page.goto(route);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const field = page.getByRole('combobox', { name: 'Search' });
    const find = page.locator('.screen-head-find');
    expect(await field.count() + await find.count(), `a way to search on ${route}`).toBeGreaterThan(0);
    await expect(await field.count() ? field : find).toBeVisible();
  }
  // The theme control says what pressing it does, and is a button, not a sixth place to go.
  await page.goto('/');
  const theme = page.getByRole('button', { name: /^Change the theme/ });
  await expect(theme).toBeVisible();
  await expect(theme).toHaveAttribute('aria-label', /Field now; next is Mono/);
});

test('a section is named by its own heading, and the map has words on its controls', async ({ page, state }) => {
  const hour = new Date(Date.now() - 3_600_000).toISOString();
  state.conditions = { ...state.conditions, power: { ...state.conditions.power, state: 'off', since: hour, set_by: 'phone' } };
  await page.setViewportSize({ width: 853, height: 480 });
  await page.goto('/');
  // "Briefing" was a region wrapping four regions, named after a word that is nowhere on the screen.
  await expect(page.getByRole('region', { name: 'Briefing' })).toHaveCount(0);
  for (const region of await page.getByRole('region').all()) {
    const name = await region.getAttribute('aria-label');
    if (!name) continue;
    const heading = region.locator('h2').first();
    if (await heading.count()) expect((await heading.textContent())?.trim()).toBe(name);
  }

  await page.goto('/map');
  const nav = page.getByRole('group', { name: 'Move the map' });
  await expect(nav.getByRole('button', { name: 'Zoom in' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'Zoom out' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'Face north' })).toBeVisible();
  // MapLibre's own wordless control set is not drawn at all.
  await expect(page.locator('.maplibregl-ctrl-group')).toHaveCount(0);
});
