import { test, expect } from './test';

/** The app logs an uncaught error and an unhandled rejection with context, but it must not hide them: the
 * browser tests that assert "no page errors" (live.spec.ts, doc.spec.ts) rely on Playwright hearing them. */
test('an uncaught error still reaches Playwright as a pageerror, and the screen stays', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const logged: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') logged.push(m.text()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await page.evaluate(() => { setTimeout(() => { throw new Error('uncaught on purpose'); }, 0); });
  await expect.poll(() => errors.some((m) => m.includes('uncaught on purpose'))).toBe(true);
  await expect.poll(() => logged.some((m) => m.includes('[sos] uncaught error'))).toBe(true);
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
});

test('an unhandled rejection is visible to Playwright too', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await page.evaluate(() => { void Promise.reject(new Error('rejected on purpose')); });
  await expect.poll(() => errors.some((m) => m.includes('rejected on purpose'))).toBe(true);
});
