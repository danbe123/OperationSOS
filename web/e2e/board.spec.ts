import { test, expect } from './test';

test('a drill puts the board on the kiosk screen, and a tap brings Home back', async ({ page }) => {
  await page.goto('/situation');
  await page.getByLabel('Drill scenario').selectOption('grid-collapse');
  await page.getByLabel('Drill started').selectOption('2');
  await page.getByRole('button', { name: 'Start drill' }).click();
  await expect(page.getByText('DRILL in progress')).toBeVisible();

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
  await expect(page.getByText(/jobs ticked/)).toContainText('Drill ended: National grid collapse.');
  await expect(page.getByRole('list', { name: 'What happened in the drill' })).toContainText('Drill started');
  await expect(page.getByRole('region', { name: 'Situation' })).toContainText('Everything is working');
});

test('Home in peacetime says how long the household would last, in plain words', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'Everything is working' })).toBeVisible();
  const strip = page.getByRole('region', { name: 'Situation' });
  // No score, no points: a number out of a hundred whose meaning is never given is not an answer.
  await expect(strip).not.toContainText('out of 100');
  await expect(strip).not.toContainText('points');
  await expect(strip).toContainText('would help most');
  const gaps = strip.getByLabel('Gaps to close');
  await expect(gaps).toContainText('Water: 1.5 days for 3 people');
  // A gap is a thing to do, so it is a row you can hit, not an underlined link.
  const row = gaps.getByRole('link', { name: 'Water: 1.5 days for 3 people' });
  expect((await row.boundingBox())!.height).toBeGreaterThanOrEqual(48);
  await row.click();
  await expect(page).toHaveURL(/\/plan#stock$/);
});
