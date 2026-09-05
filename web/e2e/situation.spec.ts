import { test, expect } from './test';

test('the power goes off: the strip, the forecast, a task ticked, and everything back on', async ({ page }) => {
  await page.goto('/');
  // peacetime: the strip carries the readiness score, not chips
  const strip = page.getByRole('region', { name: 'Situation' });
  await expect(strip).toContainText('Everything is working');
  await expect(strip).toContainText('62');

  // set the power off, an hour ago, from the sheet the chip opens
  await strip.getByRole('link', { name: 'Situation sheet' }).click();
  await page.getByLabel('Mains power: since').selectOption('hour');
  await page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Off' }).click();
  await expect(page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Off' })).toHaveAttribute('aria-pressed', 'true');
  await page.screenshot({ path: '/tmp/sos-situation-sheet-853.png' });

  // Home now leads with what is wrong, what is coming and what to do
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('group', { name: 'What is working' }).getByRole('link', { name: /Mains power: off for 1 h/ })).toBeVisible();
  const coming = page.getByRole('region', { name: 'Coming up' });
  await expect(coming).toContainText('Freezer food unsafe');
  await expect(coming).toContainText('in 23 h');
  const doing = page.getByRole('region', { name: 'Do this now' });
  await expect(doing).toContainText('Fill the bath and every container');
  await page.screenshot({ path: '/tmp/sos-home-power-off-853.png' });

  // tick the bath off; the box saves it and the tick sticks (a controlled box only settles once saved)
  await doing.getByRole('checkbox', { name: /Fill the bath/ }).click();
  await expect(doing.getByRole('checkbox', { name: /Fill the bath/ })).toBeChecked();
  await page.getByRole('link', { name: 'All tasks' }).click();
  await expect(page.getByRole('region', { name: 'Now' })).toContainText('Keep the fridge and freezer doors shut');
  await expect(page.locator('.task-count')).toHaveText('3 to do');

  // the chrome chip strip follows onto every other screen
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await page.getByRole('navigation', { name: 'Main sections' }).getByRole('link', { name: /Phone and radio/ }).click();
  const chips = page.getByRole('group', { name: 'Situation now' });
  await expect(chips.getByRole('link', { name: /Mains power: off/ })).toBeVisible();
  await chips.getByRole('link', { name: 'Situation', exact: true }).click();

  // end with everything working again
  await page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Working' }).click();
  await expect(page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Working' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Situation' })).toContainText('Everything is working');
  await expect(page.getByRole('region', { name: 'Coming up' })).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('a drill runs the whole thing without touching the real conditions', async ({ page }) => {
  await page.goto('/situation');
  await page.getByLabel('Drill scenario').selectOption('grid-collapse');
  await page.getByLabel('Drill started').selectOption('2');
  await page.getByRole('button', { name: 'Start drill' }).click();
  await expect(page.getByText('DRILL in progress')).toBeVisible();
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Situation' })).toContainText('DRILL');
  await expect(page.getByRole('region', { name: 'Situation' })).toContainText('National grid collapse');
  await page.getByRole('link', { name: 'Situation sheet' }).click();
  await page.getByRole('button', { name: 'End drill' }).click();
  await expect(page.getByText('DRILL in progress')).toBeHidden();
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Situation' })).toContainText('Everything is working');
});

test('with both phone networks down the pages say the numbers will not connect', async ({ page }) => {
  await page.goto('/situation');
  for (const name of ['Mobile network', 'Landline and 999']) {
    await page.getByRole('group', { name }).getByRole('button', { name: 'Off' }).click();
    await expect(page.getByRole('group', { name }).getByRole('button', { name: 'Off' })).toHaveAttribute('aria-pressed', 'true');
  }
  await page.goto('/p/pmr446');
  const notice = page.getByRole('status').filter({ hasText: 'will not connect' });
  await expect(notice).toBeVisible();
  await notice.getByRole('link', { name: 'Getting help without phones' }).click();
  await expect(page).toHaveURL(/\/p\/no-phones$/);
});

test('the sheet and Home fit a phone as well as the kiosk', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/situation');
  await page.getByRole('group', { name: 'Water supply' }).getByRole('button', { name: 'Off' }).click();
  await page.screenshot({ path: '/tmp/sos-situation-sheet-390.png' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('group', { name: 'What is working' })).toBeVisible();
  await page.screenshot({ path: '/tmp/sos-home-power-off-390.png' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
