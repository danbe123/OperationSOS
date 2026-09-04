import type { Page } from '@playwright/test';
import { test, expect } from './test';

type MapWindow = Window & { __sosMap?: { loaded(): boolean; getLayer(id: string): unknown; getLayoutProperty(id: string, k: string): string | undefined; getCenter(): { lng: number; lat: number }; __styleVersion?: number } };

async function waitForMap(page: Page) {
  await page.waitForFunction(() => Boolean((window as MapWindow).__sosMap?.loaded()));
}
const styleVersion = (page: Page) => page.evaluate(() => (window as MapWindow).__sosMap?.__styleVersion ?? 0);
async function waitForStyleReload(page: Page, sinceVersion: number) {
  await page.waitForFunction((v) => ((window as MapWindow).__sosMap?.__styleVersion ?? 0) > v, sinceVersion);
}
const layerVisible = (page: Page, id: string) =>
  page.evaluate((layerId) => {
    const m = (window as MapWindow).__sosMap!;
    return Boolean(m.getLayer(layerId)) && (m.getLayoutProperty(layerId, 'visibility') ?? 'visible') === 'visible';
  }, id);

test('renders from PMTiles over range requests, toggles an overlay and keeps it across a base switch', async ({ page }) => {
  const tile = page.waitForResponse((r) => r.url().includes('.pmtiles') && Boolean(r.request().headers()['range']));
  await page.goto('/map?lat=50.92&lon=-1.43&z=12');
  const first = await tile;
  expect(first.status()).toBe(206);
  expect(first.headers()['content-encoding']).toBeUndefined();
  await waitForMap(page);
  await expect(page.getByTestId('map-readout')).toContainText('Centre: SU');

  await page.getByRole('button', { name: 'Layers' }).click();
  const panel = page.getByRole('dialog', { name: 'Layers' });
  await panel.getByLabel('Hospitals, pharmacies, GP surgeries').check();
  await expect(page).toHaveURL(/overlay=health/);
  await expect.poll(() => layerVisible(page, 'sos-overlay-health-point')).toBe(true);

  const versionBeforeBaseSwitch = await styleVersion(page);
  await panel.getByLabel('OS Open Zoomstack').check();
  await waitForStyleReload(page, versionBeforeBaseSwitch);
  await waitForMap(page);
  await expect.poll(() => layerVisible(page, 'sos-overlay-health-point')).toBe(true);
  await panel.getByLabel('Hospitals, pharmacies, GP surgeries').uncheck();
  await expect.poll(() => layerVisible(page, 'sos-overlay-health-point')).toBe(false);
});

test('place search, pin persistence and grid reference for a known point', async ({ page }) => {
  await page.goto('/map');
  await waitForMap(page);
  await page.getByRole('button', { name: 'Find place' }).click();
  await page.getByLabel('Place, postcode or grid reference').fill('oxf');
  await page.getByRole('button', { name: /Oxford/ }).click();
  await expect(page.getByTestId('map-readout')).toContainText('Centre: SP');

  await page.getByRole('button', { name: 'Find place' }).click();
  await page.getByLabel('Place, postcode or grid reference').fill('SU 3728 1551');
  await page.getByRole('button', { name: 'Go to grid reference SU 3728 1551' }).click();
  await expect(page.getByTestId('map-readout')).toContainText('Centre: SU 3728 1551');

  await page.getByRole('button', { name: 'Pins' }).click();
  await page.getByRole('button', { name: 'Drop a pin at the centre' }).click();
  await page.getByLabel('Pin name').fill('OS HQ');
  await page.getByRole('button', { name: 'Save pin' }).click();
  await expect(page.getByRole('dialog', { name: 'Pins' }).getByText('OS HQ')).toBeVisible();
  await page.reload();
  await waitForMap(page);
  await page.getByRole('button', { name: 'Pins' }).click();
  await expect(page.getByRole('dialog', { name: 'Pins' }).getByText('OS HQ')).toBeVisible();
});
