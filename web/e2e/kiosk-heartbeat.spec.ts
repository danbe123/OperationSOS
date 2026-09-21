import type { Page } from '@playwright/test';
import { test, expect, MODE } from './test';

/** The kiosk's own page tells the box it is alive every 30 s, so that sos-kiosk-app can restart a Chromium whose
 * page has hung. A phone must never send it: the box would take a phone for the kiosk. */
test.skip(MODE !== 'fixture', 'counts requests on the fixture box');

async function countBeats(page: Page) {
  const seen: string[] = [];
  page.on('request', (r) => { if (r.method() === 'POST' && new URL(r.url()).pathname === '/api/kiosk/alive') seen.push(r.postData() ?? ''); });
  return seen;
}

test('the kiosk page sends a heartbeat at once and every thirty seconds, with nothing in it', async ({ page }) => {
  await page.clock.install();
  const beats = await countBeats(page);
  await page.goto('/?kiosk=1');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await expect.poll(() => beats.length).toBe(1);
  await page.clock.runFor(31_000);
  await expect.poll(() => beats.length).toBe(2);
  await page.clock.runFor(60_000);
  await expect.poll(() => beats.length).toBe(4);
  expect(beats.every((b) => b === '')).toBe(true);
});

test('a phone page never sends one', async ({ page }) => {
  await page.clock.install();
  const beats = await countBeats(page);
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await page.clock.runFor(95_000);
  await page.waitForTimeout(300);
  expect(beats).toHaveLength(0);
});
