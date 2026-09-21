import type { Page } from '@playwright/test';
import { test, expect, MODE } from './test';

/** The box goes away and comes back: sos-api restarts by itself (systemd, about three seconds) and Caddy in
 * front of it answers 502 meanwhile, or the connection is refused outright. The screen the household is on
 * must keep what it has, say once and calmly that it is reconnecting, lose nothing that was being written,
 * and catch up by itself. Scripted with route interception, so the fixture box only. */
test.skip(MODE !== 'fixture', 'the outage is scripted with route interception on the fixture box');

type How = 'refused' | 'bad-gateway';

async function boxThatCanGoAway(page: Page) {
  let away: How | null = null;
  const asked: string[] = [];
  await page.route('**/api/**', (route) => {
    if (away === null) return route.fallback();
    asked.push(new URL(route.request().url()).pathname);
    if (away === 'refused') return route.abort('connectionrefused');
    return route.fulfill({ status: 502, contentType: 'text/plain', body: '' });
  });
  return {
    goAway: (how: How = 'refused') => { away = how; },
    comeBack: () => { away = null; },
    /** What was asked of the box while it was away. */
    asked,
  };
}

/** Somebody comes back to the screen (or the poll comes round): the app asks the box for something. */
const nudge = (page: Page) => page.evaluate(() => window.dispatchEvent(new Event('focus')));
const reconnecting = (page: Page) => page.getByTestId('reconnecting');

for (const how of ['refused', 'bad-gateway'] as const) {
  test(`Now keeps its screen while the box is away (${how}), says Reconnecting, and catches up by itself`, async ({ page, state }) => {
    const box = await boxThatCanGoAway(page);
    await page.goto('/');
    const heading = page.getByRole('heading', { level: 1, name: "What's the situation?" });
    const scenarios = page.getByRole('navigation', { name: 'Scenarios' });
    await expect(scenarios.getByRole('link', { name: /National grid collapse/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Mains power: on/ })).toBeVisible();
    await page.evaluate(() => { (window as unknown as { pageWasNotReloaded: boolean }).pageWasNotReloaded = true; });

    box.goAway(how);
    await nudge(page);
    await expect(reconnecting(page)).toBeVisible({ timeout: 10_000 });
    await expect(reconnecting(page)).toHaveText(/Reconnecting/);
    // No white screen, nothing alarming, nothing thrown away.
    await expect(heading).toBeVisible();
    await expect(scenarios.getByRole('link', { name: /National grid collapse/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Mains power: on/ })).toBeVisible();
    await expect(page.locator('main')).not.toContainText('cannot read');
    await expect(page.getByRole('dialog')).toHaveCount(0);

    // While it is away, something changes on the box.
    state.conditions.power = { ...state.conditions.power, state: 'off', updated_at: new Date().toISOString() };
    await page.waitForTimeout(3000);
    // ...and it is not a tight loop: a few seconds of outage is a few asks, not dozens.
    expect(box.asked.length).toBeLessThanOrEqual(8);

    box.comeBack();
    await expect(page.getByRole('button', { name: /^Mains power: off/ })).toBeVisible({ timeout: 20_000 });
    await expect(reconnecting(page)).toHaveCount(0);
    expect(await page.evaluate(() => (window as unknown as { pageWasNotReloaded?: boolean }).pageWasNotReloaded)).toBe(true);
  });
}

test('a tick made while the box restarts is retried and lands, without the household doing anything twice', async ({ page, state }) => {
  const box = await boxThatCanGoAway(page);
  await page.goto('/s/grid-collapse');
  const item = page.getByRole('checkbox', { name: /Fill the bath/ });
  await expect(item).toBeVisible();
  box.goAway('bad-gateway');
  await item.click();
  await expect(item).toBeChecked();          // the tick shows at once
  await page.waitForTimeout(1500);
  box.comeBack();                            // sos-api is back before the retries run out
  await expect(item).toBeChecked();
  await expect(page.locator('.notices')).toHaveCount(0);   // nothing to apologise for
  const saved = state.checklists.get('grid-collapse')!.find((i) => /Fill the bath/.test(i.text))!;
  await expect.poll(() => saved.checked, { timeout: 15_000 }).toBe(true);   // the tick shows at once; this is the box having it
});

test('a tick that cannot be saved is reported, and the list is not thrown away', async ({ page, state }) => {
  const box = await boxThatCanGoAway(page);
  await page.goto('/s/grid-collapse');
  const item = page.getByRole('checkbox', { name: /Fill the bath/ });
  await item.click();
  await expect(item).toBeChecked();
  await expect(page.locator('li.task-row').filter({ has: item }).locator('.task-time')).toContainText('ticked');
  const other = page.getByRole('checkbox', { name: /Keep the freezer shut/ });
  box.goAway();
  await other.click();
  await expect(page.locator('.notices')).toContainText(/nothing was saved/i, { timeout: 30_000 });
  await expect(other).not.toBeChecked();     // shown as what it is: not saved
  // The guide with its ticks is still on the screen, and the earlier tick is still there.
  await expect(item).toBeChecked();
  await expect(page.getByRole('heading', { name: 'Things to do for this guide' })).toBeVisible();
  await expect(reconnecting(page)).toBeVisible();
  box.comeBack();
  await expect(reconnecting(page)).toHaveCount(0, { timeout: 20_000 });
  await expect(item).toBeChecked();
  expect(state.checklists.get('grid-collapse')!.find((i) => /freezer/.test(i.text))!.checked).toBe(false);
});

test('a guide with ticks in it stays on the screen through an outage and reads itself again after', async ({ page, state }) => {
  const box = await boxThatCanGoAway(page);
  await page.goto('/s/grid-collapse');
  const item = page.getByRole('checkbox', { name: /Fill the bath/ });
  await item.click();
  await expect(page.locator('li.task-row').filter({ has: item }).locator('.task-time')).toContainText('ticked');
  box.goAway();
  await nudge(page);
  await expect(reconnecting(page)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole('heading', { name: 'Things to do for this guide' })).toBeVisible();
  await expect(page.locator('main')).not.toContainText('Could not load this guide');
  await expect(item).toBeChecked();
  // Another phone ticks something else while this one cannot reach the box.
  state.checklists.get('grid-collapse')!.find((i) => /freezer/.test(i.text))!.checked = true;
  box.comeBack();
  await expect(page.getByRole('checkbox', { name: /Keep the freezer shut/ })).toBeChecked({ timeout: 20_000 });
  await expect(item).toBeChecked();
});

test('a note being written survives the box being away, and the browser restarting', async ({ page, state }) => {
  const box = await boxThatCanGoAway(page);
  await page.goto('/notes');
  await page.getByRole('button', { name: 'Add a note' }).click();
  const form = page.getByRole('form', { name: 'Add a note' });
  await form.getByLabel('Title').fill('Rendezvous');
  await form.getByLabel('Note').fill('Church car park at noon');

  box.goAway();
  await form.getByRole('button', { name: 'Add note' }).click();
  await expect(page.getByText(/Not saved yet/)).toBeVisible({ timeout: 30_000 });
  await expect(form.getByLabel('Title')).toHaveValue('Rendezvous');
  await expect(form.getByLabel('Note')).toHaveValue('Church car park at noon');
  expect(state.notes.some((n) => n.title === 'Rendezvous')).toBe(false);

  // The browser is restarted with the box still away: the draft is there when the page comes up again.
  await page.reload();
  const restored = page.getByRole('form', { name: 'Add a note' });
  await expect(restored.getByLabel('Title')).toHaveValue('Rendezvous');
  await expect(restored.getByLabel('Note')).toHaveValue('Church car park at noon');

  box.comeBack();
  await restored.getByRole('button', { name: 'Add note' }).click();
  await expect(page.getByRole('list', { name: 'Notes and pins' })).toContainText('Rendezvous');
  expect(state.notes.filter((n) => n.title === 'Rendezvous')).toHaveLength(1);
  await expect(page.getByRole('form', { name: 'Add a note' })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('form', { name: 'Add a note' })).toHaveCount(0);   // and the draft is gone once it is saved
});

test('a half-typed search is not lost, and its results arrive by themselves when the box is back', async ({ page }) => {
  const box = await boxThatCanGoAway(page);
  await page.goto('/search');
  const field = page.getByRole('combobox', { name: 'Search' });
  await field.fill('bleeding');
  box.goAway();
  await field.press('Enter');
  await expect(page).toHaveURL(/q=bleeding/);
  await expect(page.getByText(/Search failed/)).toBeVisible({ timeout: 10_000 });
  await expect(field).toHaveValue('bleeding');
  box.comeBack();
  await expect(page.getByText(/results?$/).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Search failed/)).toHaveCount(0);
  await expect(field).toHaveValue('bleeding');
});

test('the board keeps working through an outage and says Reconnecting', async ({ page }) => {
  const box = await boxThatCanGoAway(page);
  await page.goto('/board');
  const working = page.getByRole('region', { name: 'What is working' });
  await expect(working).toBeVisible();
  box.goAway();
  await nudge(page);
  await expect(reconnecting(page)).toBeVisible({ timeout: 10_000 });
  await expect(working).toBeVisible();
  box.comeBack();
  await expect(reconnecting(page)).toHaveCount(0, { timeout: 20_000 });
  await expect(working).toBeVisible();
});
