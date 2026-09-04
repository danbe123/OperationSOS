import { test, expect } from './test';

const WIKI = 'wikipedia_en_100_mini_2026-01';

test('three article links, then Back three times; app URL matches the frame each time', async ({ page }) => {
  await page.goto(`/read/${WIKI}/A/Main_Page`);
  const frame = page.frameLocator('iframe[title="Article"]');
  await expect(frame.getByRole('heading', { name: 'Main Page' })).toBeVisible();

  await frame.getByRole('link', { name: 'Water' }).click();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Water$`));
  await expect(frame.getByRole('heading', { name: 'Water' })).toBeVisible();

  await frame.getByRole('link', { name: 'Ice' }).click();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Ice$`));
  await expect(frame.getByRole('heading', { name: 'Ice' })).toBeVisible();

  await frame.getByRole('link', { name: 'Electrical grid' }).click();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Electrical_grid$`));
  await expect(frame.getByRole('heading', { name: 'Electrical grid' })).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Ice$`));
  await expect(frame.getByRole('heading', { name: 'Ice' })).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Water$`));
  await expect(frame.getByRole('heading', { name: 'Water' })).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Main_Page$`));
  await expect(frame.getByRole('heading', { name: 'Main Page' })).toBeVisible();
  expect(await page.locator('iframe[title="Article"]').getAttribute('src')).toBe(`/kiwix/content/${WIKI}/A/Main_Page`);
});

test('an external link shows the in-app notice and stays put', async ({ page }) => {
  await page.goto(`/read/${WIKI}/A/Water`);
  const frame = page.frameLocator('iframe[title="Article"]');
  await frame.getByRole('link', { name: 'the live article' }).click();
  await expect(page.getByText('Not in the library (needs the internet)')).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Water$`));
});
