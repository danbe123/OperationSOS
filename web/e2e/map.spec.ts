import type { Page } from '@playwright/test';
import { test, expect } from './test';

type MapWindow = Window & { __sosMap?: { loaded(): boolean; getStyle(): { layers: { id: string; type: string; source?: string }[] }; getLayer(id: string): unknown; getLayoutProperty(id: string, k: string): string | undefined; getCenter(): { lng: number; lat: number }; __styleVersion?: number } };

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
    const actual = m.getLayer(layerId) ? layerId : m.getStyle().layers.find((l) => l.source === layerId.replace(/-point$/, '') && l.type === 'circle')?.id;
    return Boolean(actual) && (m.getLayoutProperty(actual!, 'visibility') ?? 'visible') === 'visible';
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
  await panel.getByLabel(/Hospitals, pharmacies.*GP surgeries/).check();
  await expect(page).toHaveURL(/overlay=health/);
  await expect.poll(() => layerVisible(page, 'sos-overlay-health-point')).toBe(true);

  const versionBeforeBaseSwitch = await styleVersion(page);
  await panel.getByRole('radio', { name: /OS Open Zoomstack|Ordnance Survey/ }).check();
  await waitForStyleReload(page, versionBeforeBaseSwitch);
  await waitForMap(page);
  await expect.poll(() => layerVisible(page, 'sos-overlay-health-point')).toBe(true);
  await panel.getByLabel(/Hospitals, pharmacies.*GP surgeries/).uncheck();
  await expect.poll(() => layerVisible(page, 'sos-overlay-health-point')).toBe(false);
});

test('place search, pin persistence and grid reference for a known point', async ({ page, request }) => {
  await page.goto('/map');
  await waitForMap(page);
  await page.getByRole('button', { name: 'Find place' }).click();
  await page.getByLabel('Place, postcode or grid reference').fill('oxf');
  await page.getByRole('button', { name: /^Oxford city,/i }).click();   // fixture says City, the live places index says city
  await expect(page.getByTestId('map-readout')).toContainText('Centre: SP');

  await page.getByRole('button', { name: 'Find place' }).click();
  await page.getByLabel('Place, postcode or grid reference').fill('SU 3728 1551');
  await page.getByRole('button', { name: 'Go to grid reference SU 3728 1551' }).click();
  await expect(page.getByTestId('map-readout')).toContainText('Centre: SU 3728 1551');

  await page.getByRole('button', { name: 'Pins' }).click();
  await page.getByRole('button', { name: 'Drop a pin at the centre' }).click();
  const pinTitle = `Browser map check ${Date.now()}`;
  await page.getByLabel('Pin name').fill(pinTitle);
  const created = page.waitForResponse((r) => r.url().endsWith('/api/notes') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Save pin' }).click();
  const note = await (await created).json();
  try {
    await expect(page.getByRole('dialog', { name: 'Pins' }).getByText(pinTitle)).toBeVisible();
    await page.reload();
    await waitForMap(page);
    await page.getByRole('button', { name: 'Pins' }).click();
    await expect(page.getByRole('dialog', { name: 'Pins' }).getByText(pinTitle)).toBeVisible();
  } finally {
    await request.delete(`/api/notes/${note.id}`);
  }
});
