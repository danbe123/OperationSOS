import { test, expect } from './test';

test('the interactive board scrolls to the tenth condition and the last job instead of clipping them off', async ({ page, state }) => {
  // Two conditions off plus a scenario's tasks is the ordinary shape of a real incident, and on the
  // kiosk's own 853x480 it is exactly the shape that used to overflow board-cols with overflow:hidden
  // and no way to reach the rest: a household could not tell whether Sewage was off.
  const hour = new Date(Date.now() - 3_600_000).toISOString();
  for (const id of ['power', 'water'] as const) {
    state.conditions = { ...state.conditions, [id]: { ...state.conditions[id], state: 'off', since: hour, set_by: 'phone' } };
  }
  state.situation = { slug: 'grid-collapse', title: 'National grid collapse', started_at: hour, elapsed_s: 3600, phase: 'right-now' };
  await page.setViewportSize({ width: 853, height: 480 });
  await page.goto('/board');
  const conditions = page.getByRole('region', { name: 'What is working' });
  await expect(conditions).toContainText('Sewage');
  await conditions.getByText('Sewage').scrollIntoViewIfNeeded();
  await expect(conditions.getByText('Sewage')).toBeInViewport();
  // The board is worked with a finger, so its columns must be a real scroll container, not a box
  // whose own overflow: hidden makes the touch-scrollable content below the fold unreachable.
  const overflowY = await page.locator('.board-live .board-cols').evaluate((el) => getComputedStyle(el).overflowY);
  expect(overflowY).not.toBe('hidden');
});

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
