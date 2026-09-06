import { test, expect } from './test';

test('set the centre as home, then walk to what is nearby', async ({ page }) => {
  await page.goto('/map?lat=50.93790&lon=-1.47080&z=14');
  await page.getByRole('button', { name: 'Home' }).click();
  const homePanel = page.getByRole('dialog', { name: 'Home' });
  await expect(homePanel).toContainText('No home set');
  await homePanel.getByLabel('Home name').fill('Our house');
  await homePanel.getByRole('button', { name: 'Set as home' }).click();
  await expect(homePanel).toContainText('Our house');
  // two grid references for two different places, each said out loud
  await expect(homePanel.locator('.map-panel-lead')).toContainText(/Your home: SU \d{4} \d{4}/);
  await expect(homePanel.locator('.map-panel-lead')).toContainText(/The map is on: SU \d{4} \d{4}/);
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

test('on a phone the nearby sheet leads with its answer and the map stays live above it', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/map?lat=50.93790&lon=-1.47080&z=14');
  await page.getByRole('button', { name: 'Nearby' }).click();

  const lead = page.locator('.map-panel-lead');
  const answer = lead.locator('.map-lead-answer');
  await expect(answer).toHaveText('Boots, High Street');
  await expect(lead).toContainText('on foot');
  // the answer is set at --t-lead, not in the small print
  expect(await answer.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(22);

  // the pinned action row no longer sits over the first result
  const leadBox = (await lead.boundingBox())!;
  const actionBox = (await page.locator('.map-panel-actions').boundingBox())!;
  expect(leadBox.y + leadBox.height).toBeLessThanOrEqual(actionBox.y + 1);

  // the sheet took 70 % because its body holds more than it can show, and the map is still live above it
  const sheetBox = (await page.locator('.map-panel').boundingBox())!;
  const hostBox = (await page.locator('.map-host').boundingBox())!;
  expect(sheetBox.height / hostBox.height).toBeGreaterThan(0.6);
  expect(sheetBox.height / hostBox.height).toBeLessThan(0.78);
  expect(sheetBox.y - hostBox.y).toBeGreaterThan(60);

  // the small print about how far "as the crow flies" is, is the last thing in the body, not the first thing in the panel
  await expect(lead).not.toContainText('crow flies');
  await expect(page.locator('.map-panel-body > *').last()).toContainText('as the crow flies');

  // choosing a kind moves that kind's nearest into the head, where it can be acted on
  await page.getByLabel('Which kind of place do you need?').selectOption({ label: 'Emergency department' });
  await expect(answer).toHaveText('Southampton General Hospital');
  await page.getByRole('button', { name: 'Show it on the map' }).click();
  await expect(page.getByTestId('map-readout')).toContainText('Centre: SU');
});

test('on a phone the home sheet labels both grid references and cuts neither', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/map?lat=54.5&lon=-3.5&z=10');
  await page.getByRole('button', { name: 'Home' }).click();
  const lead = page.locator('.map-panel-lead');
  await expect(lead).toContainText('Your home: not set yet');
  await expect(lead).toContainText(/The map is on: NY \d{4} \d{4}/);
  // the line wraps rather than being cut off after "NY"
  for (const ref of await lead.locator('.map-ref').all()) {
    expect(await ref.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  }
});
