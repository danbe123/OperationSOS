import { test, expect } from './test';

test('the power goes off: the band, the forecast, a job ticked, and everything back on', async ({ page }) => {
  await page.goto('/');
  // peacetime: Now carries the readiness, not chips, and there is no band
  const readiness = page.getByRole('region', { name: 'Situation', exact: true });
  await expect(readiness).toContainText('Everything is working');
  await expect(readiness).toContainText('62');
  await expect(page.getByRole('group', { name: 'Situation now' })).toBeHidden();

  // set the power off, an hour ago, from the sheet
  await readiness.getByRole('link', { name: 'Situation sheet' }).click();
  await page.getByLabel('Mains power: since').selectOption('hour');
  await page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Off' }).click();
  await expect(page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Off' })).toHaveAttribute('aria-pressed', 'true');

  // Now leads with what to do, and the band says what is off
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  const band = page.getByRole('group', { name: 'Situation now' });
  await expect(band.getByRole('link', { name: /Mains power: off for 1 h/ })).toBeVisible();
  const coming = page.getByRole('region', { name: 'Coming up' });
  await expect(coming).toContainText('Freezer food unsafe');
  await expect(coming).toContainText('in 23 h');
  const doing = page.getByRole('region', { name: 'Do this now' });
  await expect(doing).toContainText('Fill the bath and every container');

  // tick the bath off; the box saves it and the tick sticks
  await doing.getByRole('checkbox', { name: /Fill the bath/ }).click();
  await expect(doing.getByRole('checkbox', { name: /Fill the bath/ })).toBeChecked();
  await page.getByRole('link', { name: 'All tasks' }).click();
  await expect(page.getByRole('region', { name: 'Right now' })).toContainText('Keep the fridge and freezer doors shut');
  await expect(page.locator('.task-count')).toHaveText('3 to do');

  // the band follows onto every other screen
  await page.goto('/p/pmr446');
  await expect(band.getByRole('link', { name: /Mains power: off/ })).toBeVisible();
  await band.getByRole('link', { name: 'Situation', exact: true }).click();

  // end with everything working again
  await page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Working' }).click();
  await expect(page.getByRole('group', { name: 'Mains power' }).getByRole('button', { name: 'Working' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  await expect(page.getByRole('region', { name: 'Situation', exact: true })).toContainText('Everything is working');
  await expect(page.getByRole('group', { name: 'Situation now' })).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('a drill runs the whole thing without touching the real conditions', async ({ page }) => {
  await page.goto('/situation');
  await page.getByLabel('Drill scenario').selectOption('grid-collapse');
  await page.getByLabel('Drill started').selectOption('2');
  await page.getByRole('button', { name: 'Start drill' }).click();
  await expect(page.getByText('Drill in progress')).toBeVisible();
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  const band = page.getByRole('group', { name: 'Situation now' });
  await expect(band).toContainText('Drill');
  await expect(band).toContainText('National grid collapse');
  await band.getByRole('link', { name: 'Situation', exact: true }).click();
  await page.getByRole('button', { name: 'End drill' }).click();
  await expect(page.getByText('Drill in progress')).toBeHidden();
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  await expect(page.getByRole('region', { name: 'Situation', exact: true })).toContainText('Everything is working');
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

test('the sheet and Now fit a phone as well as the kiosk', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/situation');
  await page.getByRole('group', { name: 'Water supply' }).getByRole('button', { name: 'Off' }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  await expect(page.getByRole('group', { name: 'Situation now' })).toContainText('Water');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('the situation carries to another box as codes, and comes back in', async ({ page }) => {
  await page.goto('/situation');
  const carry = page.getByRole('region', { name: 'Carry the situation' });
  await carry.getByRole('button', { name: 'Export as codes' }).click();
  const codes = carry.getByRole('group', { name: 'Situation codes' });
  await expect(codes).toContainText('Code 1 of');
  await expect(codes.getByRole('img', { name: /Situation code 1 of/ })).toBeVisible();
  await expect(codes.getByRole('button', { name: 'Previous' })).toBeDisabled();
  await codes.getByRole('button', { name: 'Next' }).click();
  await expect(codes).toContainText('Code 2 of');
  await carry.getByRole('button', { name: 'Copy as text instead' }).click();
  await expect(carry.getByRole('textbox', { name: /Situation code 2 as text/ })).not.toBeEmpty();

  await carry.getByRole('textbox', { name: 'Situation to bring in' }).fill('{"i":0,"n":1,"d":"x"}');
  await carry.getByRole('button', { name: 'Bring it in' }).click();
  const summary = carry.getByRole('status', { name: 'What came in' });
  await expect(summary).toContainText('Brought in from the other box.');
  await expect(summary).toContainText('conditions: 2 updated, 8 kept');
});
