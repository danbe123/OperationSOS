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

  // The board is worked with a finger now, so the way back is a button and not the whole screen.
  await page.getByRole('button', { name: 'Back to Now' }).click();
  await expect(page).toHaveURL(/\/$/);

  // and the drill ends with what happened in it
  await page.getByRole('button', { name: 'End drill' }).click();
  // The debrief is a dialog: as a panel in the flow it took 326 px of a 480 px kiosk and pushed the
  // five destinations off the rail.
  const debrief = page.getByRole('dialog', { name: 'How the drill went' });
  await expect(debrief).toContainText('National grid collapse, ');
  await expect(debrief.getByRole('list', { name: 'What happened in the drill' })).toContainText('Drill started');
  await debrief.getByRole('button', { name: 'Close' }).click();
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
});

test('Home in peacetime asks what the situation is, and asks for nothing else first', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  const situations = page.getByRole('navigation', { name: 'Scenarios' });
  // No score, no points, no register: the front door is the question and its answers.
  await expect(page.locator('main')).not.toContainText('out of 100');
  await expect(page.locator('main')).not.toContainText('points');
  await expect(page.locator('main')).not.toContainText('register');
  // A tile is a touch target, and it opens that situation's guide.
  const tile = situations.getByRole('link', { name: /National grid collapse/ });
  expect((await tile.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await tile.click();
  await expect(page).toHaveURL(/\/s\/grid-collapse$/);
});
