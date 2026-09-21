import { test, expect } from './test';

test('Now -> scenario -> tick a job; a second phone sees the tick', async ({ page, browser, withFixtures }) => {
  // The situations are the front door's answers now, one tap from Now; the Library's Guides shelf no
  // longer carries them.
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await page.getByRole('navigation', { name: 'Scenarios' }).getByRole('link', { name: /National grid collapse/ }).click();
  await expect(page).toHaveURL(/\/s\/grid-collapse$/);
  await expect(page.getByRole('tab', { name: 'Right now', selected: true })).toBeVisible();
  const box = page.getByRole('checkbox', { name: /Fill the bath/ });
  await expect(box).not.toBeChecked();
  await box.check();
  await expect(box).toBeChecked();
  await expect(page.getByTestId('checklist-summary')).toContainText('2 of 3 done');

  const other = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await withFixtures(other);
  const phone = await other.newPage();
  await phone.goto('/s/grid-collapse');
  await expect(phone.getByRole('checkbox', { name: /Fill the bath/ })).toBeChecked();
  await other.close();
});
