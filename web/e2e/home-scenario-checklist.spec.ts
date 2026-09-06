import { test, expect } from './test';

test('Guides -> scenario -> tick a job; a second phone sees the tick', async ({ page, browser, withFixtures }) => {
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Guides' }).click();
  await expect(page.getByRole('heading', { name: 'Situations' })).toBeVisible();
  await page.getByRole('navigation', { name: 'Scenarios' }).getByRole('link', { name: /National grid collapse/ }).click();
  await expect(page).toHaveURL(/\/s\/grid-collapse$/);
  await expect(page.getByRole('tab', { name: 'Right now', selected: true })).toBeVisible();
  const box = page.getByLabel(/Fill the bath/);
  await expect(box).not.toBeChecked();
  await box.check();
  await expect(box).toBeChecked();
  await expect(page.getByTestId('checklist-summary')).toContainText('2 of 3 done');

  const other = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await withFixtures(other);
  const phone = await other.newPage();
  await phone.goto('/s/grid-collapse');
  await expect(phone.getByLabel(/Fill the bath/)).toBeChecked();
  await other.close();
});
