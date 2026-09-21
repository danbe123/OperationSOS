import { test, expect } from './test';

/** After the kiosk browser (or the box) restarts, Now offers one calm way back to the screen somebody was
 * on. A full page load is what a restarted browser does: it comes up on the front door with no history. */
const chip = (page: import('@playwright/test').Page) => page.getByRole('link', { name: /Continue where you were/ });

test('a restarted browser offers to go back to the guide, and goes only when asked', async ({ page }) => {
  await page.goto('/s/grid-collapse?tab=first-72-hours');
  await expect(page.getByRole('heading', { level: 1, name: 'National grid collapse' })).toBeVisible();
  await page.goto('/');   // the browser came back up on the front door
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await expect(chip(page)).toBeVisible();
  await expect(chip(page)).toContainText('National grid collapse');
  await expect(page).toHaveURL(/\/$/);   // it did not take them anywhere by itself
  await page.waitForTimeout(500);
  await expect(page).toHaveURL(/\/$/);
  await chip(page).click();
  await expect(page).toHaveURL(/\/s\/grid-collapse\?tab=first-72-hours$/);
  await expect(page.getByRole('heading', { level: 1, name: 'National grid collapse' })).toBeVisible();
});

test('it is not there after an ordinary trip round the app, and can be dismissed for good', async ({ page }) => {
  await page.goto('/s/grid-collapse');
  await expect(page.getByRole('heading', { level: 1, name: 'National grid collapse' })).toBeVisible();
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await expect(chip(page)).toHaveCount(0);

  await page.goto('/');
  await expect(chip(page)).toBeVisible();
  await page.getByRole('button', { name: /Dismiss: continue where you were/ }).click();
  await expect(chip(page)).toHaveCount(0);
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await expect(chip(page)).toHaveCount(0);
});

test('it is not offered for a place left more than twelve hours ago, or when the browser will not store', async ({ page }) => {
  await page.goto('/s/grid-collapse');
  await expect(page.getByRole('heading', { level: 1, name: 'National grid collapse' })).toBeVisible();
  await page.evaluate(() => {
    const p = JSON.parse(localStorage.getItem('sos.lastPlace') ?? '{}');
    localStorage.setItem('sos.lastPlace', JSON.stringify({ ...p, at: Date.now() - 13 * 3600 * 1000 }));
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await expect(chip(page)).toHaveCount(0);

  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('denied'); };
    Storage.prototype.setItem = () => { throw new Error('denied'); };
  });
  await page.goto('/s/grid-collapse');
  await expect(page.getByRole('heading', { level: 1, name: 'National grid collapse' })).toBeVisible();
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();   // no white screen without storage
  await expect(chip(page)).toHaveCount(0);
});
