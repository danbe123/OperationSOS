import { test, expect } from './test';

test('a box with a voice reads a page aloud, and stops when told', async ({ page }) => {
  await page.goto('/p/pmr446');
  const read = page.getByRole('button', { name: 'Read aloud' });
  await expect(read).toBeVisible();
  await read.click();
  await expect(page.getByRole('button', { name: 'Stop reading' })).toBeVisible();
  await page.getByRole('button', { name: 'Stop reading' }).click();
  await expect(page.getByRole('button', { name: 'Read aloud' })).toBeVisible();
});

test('a box with no voice takes the read-aloud buttons away', async ({ page, state }) => {
  state.speaks = false;
  await page.goto('/p/pmr446');
  await page.getByRole('button', { name: 'Read aloud' }).click();
  await expect(page.getByText(/no voice installed/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Read aloud' })).toBeHidden();
  // and it stays away on the next screen in this session
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Read aloud' })).toBeHidden();
});
