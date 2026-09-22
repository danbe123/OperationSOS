import { test, expect } from './test';

test('the keyboard costs the content column its height, never the rail', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  await page.goto('/search?kiosk=1');
  const nav = page.getByRole('navigation', { name: 'Sections' });
  const before = (await nav.boundingBox())!;
  await page.getByRole('combobox', { name: 'Search' }).first().click();
  const keyboard = page.getByTestId('keyboard');
  await expect(keyboard).toBeVisible();

  // The rail is the same full-height rail it was before anybody started typing…
  const after = (await nav.boundingBox())!;
  expect(Math.round(after.height)).toBe(Math.round(before.height));
  expect(Math.round(after.height)).toBeGreaterThanOrEqual(470);
  // …and every destination in it, including the footer, is still reachable.
  for (const name of ['Now', 'Library', 'Kit', 'Map', 'Find', 'AI', 'System']) {
    await expect(nav.getByRole('link', { name, exact: true })).toBeVisible();
  }
  await expect(nav.getByRole('button', { name: /^Change the theme/ })).toBeVisible();
  // Visible is not the same as readable: the rail must not be scrolling its own destinations, or a
  // word is cut in half by the footer with nothing to say it was ever there.
  const clipped = await page.locator('.mainnav-list').evaluate((el) => el.scrollHeight - el.clientHeight);
  expect(clipped).toBeLessThanOrEqual(1);

  // The keyboard starts where the rail ends, so it covers the content column and nothing else.
  const kb = (await keyboard.boundingBox())!;
  expect(Math.round(kb.x)).toBe(Math.round(before.x + before.width));

  // and every key is inside it: the panel is narrower than the screen now, so a fixed key width
  // would throw "shift" and the delete key off the ends the way the numeric layout once was.
  const keys = await keyboard.locator('.hg-button').all();
  expect(keys.length).toBeGreaterThan(20);
  for (const key of keys) {
    const label = (await key.textContent()) ?? '';
    const box = (await key.boundingBox())!;
    expect(box.x, label).toBeGreaterThanOrEqual(kb.x - 1);
    expect(box.x + box.width, label).toBeLessThanOrEqual(kb.x + kb.width + 1);
    expect(box.height, label).toBeGreaterThanOrEqual(48);
    expect(await key.evaluate((el) => el.scrollWidth <= el.clientWidth + 1), label).toBe(true);
  }
});

test('a landscape phone gets the bottom bar, so no destination is off the bottom of the screen', async ({ page }) => {
  await page.setViewportSize({ width: 844, height: 390 });
  await page.goto('/');
  const nav = page.getByRole('navigation', { name: 'Sections' });
  const box = (await nav.boundingBox())!;
  expect(box.width).toBeGreaterThan(300);                 // a bar along the bottom, not a 96 px rail
  expect(box.y + box.height).toBeLessThanOrEqual(391);
  for (const name of ['Now', 'Library', 'Kit', 'Map', 'Find']) {
    const dest = (await nav.getByRole('link', { name, exact: true }).boundingBox())!;
    expect(dest.y + dest.height, name).toBeLessThanOrEqual(391);
  }
  // the theme button moves to the screen head when there is no rail footer to hold it
  await expect(page.getByRole('button', { name: /^Change the theme/ })).toHaveCount(1);
});

test('every key on the keyboard is readable on a portrait phone, not just the kiosk', async ({ page }) => {
  // UX audit finding: {bksp}/{enter}/{shift} read "⌫ delete", "↵ enter", "⇧ shift" on the kiosk, but
  // at 390px wide the row has no room for the word and `overflow: hidden` cut it silently to "dele",
  // "ente" and "shi" with no ellipsis — even the icon glyph in front of the word was gone.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/search?kiosk=1');
  await page.getByRole('combobox', { name: 'Search' }).first().click();
  const keyboard = page.getByTestId('keyboard');
  await expect(keyboard).toBeVisible();
  const keys = await keyboard.locator('.hg-button').all();
  expect(keys.length).toBeGreaterThan(20);
  for (const key of keys) {
    const label = (await key.textContent()) ?? '';
    expect(await key.evaluate((el) => el.scrollWidth <= el.clientWidth + 1), label).toBe(true);
  }
});
