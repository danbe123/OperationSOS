import { test, expect, MODE } from './test';

// Cannot run in fixture mode: these open the real installed library (real map overlays, a real medicine PDF, the live API), which `vite preview` and the mocks do not have.
// Their fixture-mode counterparts are map.spec.ts (overlays), doc.spec.ts (a PDF and Back) and home-scenario-checklist.spec.ts (a tick seen by a second phone).
test.skip(MODE !== 'dev', 'needs the installed library and the dev stack (real overlays, real PDF, live API)');

test('flood, access land, footpaths and hospitals draw real features', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const ids = ['flood-zones', 'access-land', 'footpaths', 'health'];
  const failures: string[] = [];
  page.on('response', (r) => { if (r.url().includes('/maps/') && r.status() >= 400) failures.push(r.url()); });
  await page.goto(`/map?lat=50.91&lon=-1.50&z=11&${ids.map((id) => `overlay=${id}`).join('&')}`);
  for (const id of ids) {
    await expect.poll(() => page.evaluate((overlay) => {
      const map = (window as unknown as { __sosMap?: { queryRenderedFeatures(): { source: string }[] } }).__sosMap;
      return map?.queryRenderedFeatures().filter((f) => f.source === `sos-overlay-${overlay}`).length ?? 0;
    }, id), { timeout: 30_000 }).toBeGreaterThan(0);
  }
  expect(failures).toEqual([]);
});

test('the bookmarked medicine PDF opens and Back returns to the scenario', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/s/nuclear-war');
  await expect(page.getByRole('tab', { name: 'Right now' })).toBeVisible();
  await page.goto('/read/zimgit-medicine_en_2024-08/files/First%20Aid%20and%20Medicine%20(1).pdf');
  await expect(page).toHaveURL(/\/read\/zimgit-medicine_en\/files\//);
  const viewer = page.frameLocator('iframe[title="Document"]');
  await expect(viewer.locator('.page[data-loaded="true"]').first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: 'Back', exact: true }).click();
  await expect(page).toHaveURL(/\/s\/nuclear-war$/);
  await expect(page.getByRole('tab', { name: 'Right now' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('the live checklist uses the sidebar and synchronises across phones', async ({ page, browser }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/s/nuclear-war');
  const sidebar = page.locator('.scenario-checklist');
  const guidance = page.locator('.scenario-guidance');
  await expect(sidebar).toBeVisible();
  const a = (await sidebar.boundingBox())!;
  const b = (await guidance.boundingBox())!;
  expect(a.x).toBeGreaterThan(b.x + b.width);
  const box = sidebar.getByRole('checkbox').first();
  const original = await box.isChecked();
  const phoneContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    await box.setChecked(!original);
    const phone = await phoneContext.newPage();
    await phone.goto('/s/nuclear-war');
    await expect(phone.locator('.scenario-checklist').getByRole('checkbox').first()).toBeChecked({ checked: !original });
    expect(await phone.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  } finally {
    await box.setChecked(original);
    await phoneContext.close();
  }
});
