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

test('a link to the internet is plain text, and a link into the library is still a link', async ({ page }) => {
  await page.goto(`/read/${WIKI}/A/Water`);
  const frame = page.frameLocator('iframe[title="Article"]');
  await expect(frame.getByRole('heading', { name: 'Water' })).toBeVisible();
  // Nothing on this box can follow it, so it is not offered as something to tap: the words stay, the link goes.
  const live = frame.locator('span.sos-unlinked', { hasText: 'the live article' });
  await expect(live).toBeVisible();
  await expect(frame.getByRole('link', { name: 'the live article' })).toHaveCount(0);
  await expect(frame.locator('a[href^="http"]')).toHaveCount(0);
  await expect(frame.getByRole('link', { name: 'Ice' })).toBeVisible();
  // Tapping the words does nothing: no notice, and the address stays put.
  await live.click();
  await expect(page.getByText('Not in the library (needs the internet)')).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Water$`));
});

test('a link a page adds to the internet after it loads still says it needs the internet, and stays put', async ({ page }) => {
  await page.goto(`/read/${WIKI}/A/Late_link`);
  const frame = page.frameLocator('iframe[title="Article"]');
  await expect(frame.getByRole('heading', { name: 'Late link' })).toBeVisible();
  // The reader styles the frame first thing when it loads, and unlinks the internet's links and starts
  // listening to clicks in the same breath: once the style is there, the page has been gone over once.
  await expect(frame.locator('style#sos-reader-theme')).toBeAttached();
  await frame.getByRole('button', { name: 'Add a link' }).click();
  // So this one is a real anchor, and the click handler is what catches it.
  await frame.getByRole('link', { name: 'a late link' }).click();
  await expect(page.getByText('Not in the library (needs the internet)')).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/read/${WIKI}/A/Late_link$`));
  await expect(frame.getByRole('heading', { name: 'Late link' })).toBeVisible();
});
