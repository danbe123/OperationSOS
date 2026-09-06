import { test, expect } from './test';

test('set the centre as home, then walk to what is nearby', async ({ page }) => {
  await page.goto('/map?lat=50.93790&lon=-1.47080&z=14');
  await page.getByRole('button', { name: 'Home' }).click();
  const homePanel = page.getByRole('dialog', { name: 'Home' });
  await expect(homePanel).toContainText('No home set');
  await homePanel.getByLabel('Home name').fill('Our house');
  await homePanel.getByRole('button', { name: 'Set as home' }).click();
  await expect(homePanel).toContainText('Our house');
  // the flood overlay is not installed on this box, so no zone is recorded rather than a guess
  await expect(homePanel).toContainText('No flood zone recorded');
  await homePanel.getByRole('button', { name: 'Close' }).click();

  await page.getByRole('button', { name: 'Nearby' }).click();
  const panel = page.getByRole('dialog', { name: 'Nearby' });
  const pharmacy = page.locator('.nearby-facility').filter({ hasText: 'Pharmacy' });
  await expect(pharmacy).toContainText('Boots, High Street');
  await expect(pharmacy).toContainText('on foot');
  // the runners-up ride under the nearest rather than as blocks of their own
  await expect(pharmacy).toContainText('Shirley Pharmacy');
  // a facility with no data on the box says why, rather than staying silent
  await expect(panel).toContainText('No searchable copy of the rest-centre data on this box.');

  await page.locator('.nearby-facility').filter({ hasText: 'Emergency department' })
    .getByRole('button', { name: /Line to Southampton General Hospital/ }).click();
  const readout = page.getByTestId('map-readout');
  await expect(readout).toContainText('Southampton General Hospital');
  await expect(readout).toContainText('from home');
  await expect(readout).toContainText('on foot');

  // the home keeps its own marker on the map
  expect(await page.evaluate(() => Boolean((window as unknown as { __sosMap?: { getLayer: (id: string) => unknown } }).__sosMap?.getLayer('sos-home-point')))).toBe(true);
});

test('the map fits a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/map?lat=50.93790&lon=-1.47080&z=14');
  await page.getByRole('button', { name: 'Nearby' }).click();
  await expect(page.getByRole('list', { name: 'Nearby facilities' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
