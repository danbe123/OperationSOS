import { test, expect } from './test';

test('a drill puts the board on the kiosk screen, and a tap brings Home back', async ({ page }) => {
  await page.goto('/situation');
  await page.getByLabel('Drill scenario').selectOption('grid-collapse');
  await page.getByLabel('Drill started').selectOption('2');
  await page.getByRole('button', { name: 'Start drill' }).click();
  await expect(page.getByRole('group', { name: 'Situation now' })).toContainText('Drill');

  await page.getByRole('link', { name: 'Board' }).click();
  await expect(page).toHaveURL(/\/board$/);
  await expect(page.getByRole('heading', { name: 'National grid collapse' })).toBeVisible();
  const conditions = page.getByRole('region', { name: 'What is working' });
  await expect(conditions).toContainText('Power');
  await expect(conditions).toContainText('✕ off');
  await expect(conditions).toContainText('for 2 h');
  const jobs = page.getByRole('region', { name: 'Next jobs' });
  await expect(jobs).toContainText('Fill the bath and every container');
  const today = page.getByRole('region', { name: 'Today' });
  await expect(today).toContainText('Sunset');
  await expect(today).toContainText('BBC Radio 4');
  await expect(page.getByRole('region', { name: 'Last events' })).toContainText('Drill started: National grid collapse');
  await page.screenshot({ path: '/tmp/sos-board-853.png' });

  await page.getByRole('region', { name: 'Next jobs' }).click();
  await expect(page).toHaveURL(/\/$/);

  // and the drill ends with what happened in it
  await page.getByRole('button', { name: 'End drill' }).click();
  // The debrief is a dialog: as a panel in the flow it took 326 px of a 480 px kiosk and pushed the
  // five destinations off the rail.
  const debrief = page.getByRole('dialog', { name: 'How the drill went' });
  await expect(debrief).toContainText('National grid collapse, ');
  await expect(debrief.getByRole('list', { name: 'What happened in the drill' })).toContainText('Drill started');
  await debrief.getByRole('button', { name: 'Close' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Everything is working' })).toBeVisible();
});

test('Home in peacetime says where to start, and asks for nothing first', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'Everything is working' })).toBeVisible();
  const strip = page.getByRole('region', { name: 'Start here' });
  // No score, no points: a number out of a hundred whose meaning is never given is not an answer.
  await expect(strip).not.toContainText('out of 100');
  await expect(strip).not.toContainText('points');
  await expect(strip).not.toContainText('register');
  // The one measure left is the ticks the household has already made, and it opens the kits.
  const row = strip.getByRole('link', { name: /basic items ticked/ });
  expect((await row.boundingBox())!.height).toBeGreaterThanOrEqual(20);
  await row.click();
  await expect(page).toHaveURL(/\/kit$/);
  await expect(page.getByRole('group', { name: 'How many people' })).toContainText('For 2 people');
});
