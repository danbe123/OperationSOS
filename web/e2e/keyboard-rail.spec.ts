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
  for (const name of ['Now', 'Guides', 'Medical', 'Map', 'Find', 'AI', 'System']) {
    await expect(nav.getByRole('link', { name, exact: true })).toBeVisible();
  }
  await expect(nav.getByRole('button', { name: /^Theme:/ })).toBeVisible();

  // The keyboard starts where the rail ends, so it covers the content column and nothing else.
  const kb = (await keyboard.boundingBox())!;
  expect(Math.round(kb.x)).toBe(Math.round(before.x + before.width));
});

test('a landscape phone gets the bottom bar, so no destination is off the bottom of the screen', async ({ page }) => {
  await page.setViewportSize({ width: 844, height: 390 });
  await page.goto('/');
  const nav = page.getByRole('navigation', { name: 'Sections' });
  const box = (await nav.boundingBox())!;
  expect(box.width).toBeGreaterThan(300);                 // a bar along the bottom, not a 96 px rail
  expect(box.y + box.height).toBeLessThanOrEqual(391);
  for (const name of ['Now', 'Guides', 'Medical', 'Map', 'Find']) {
    const dest = (await nav.getByRole('link', { name, exact: true }).boundingBox())!;
    expect(dest.y + dest.height, name).toBeLessThanOrEqual(391);
  }
  // the theme button moves to the screen head when there is no rail footer to hold it
  await expect(page.getByRole('button', { name: /^Theme:/ })).toHaveCount(1);
});
