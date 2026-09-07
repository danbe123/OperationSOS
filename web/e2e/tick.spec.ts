import type { Page } from '@playwright/test';
import { test, expect, setCondition } from './test';

/** One tick everywhere. A ticked job stays exactly where it is, struck through, with an Undo for ten
 * seconds — on Things to do, on the situation sheet and on a guide. A row that vanishes under the
 * finger is unrecoverable without finding and clearing a filter nobody knows about. */
async function powerOff(page: Page) {
  await page.goto('/situation');
  await setCondition(page, 'power', 'Off');
}

async function tickAndUndo(page: Page, title: RegExp) {
  const box = page.getByRole('checkbox', { name: title });
  const row = page.locator('li.task-row').filter({ has: box });
  await box.click();
  await expect(box).toBeChecked();
  await expect(row).toBeVisible();            // the row stays where it is
  await expect(row).toHaveClass(/task-done/); // struck through
  const undo = row.getByRole('button', { name: /^Undo/ });
  await expect(undo).toBeVisible();
  await undo.click();
  await expect(box).not.toBeChecked();
  await expect(row).toBeVisible();
}

test('a ticked job stays in place with an Undo, on Things to do, on the sheet and on a guide', async ({ page }) => {
  await powerOff(page);

  await page.goto('/tasks');
  await tickAndUndo(page, /Fill the bath/);

  await page.goto('/situation');
  await tickAndUndo(page, /Fill the bath/);

  await page.goto('/s/grid-collapse');
  await tickAndUndo(page, /Fill the bath/);
});

test('the meta line under a ticked job is not struck through: it is the answer', async ({ page }) => {
  await page.goto('/s/grid-collapse');
  const box = page.getByRole('checkbox', { name: /Fill the bath/ });
  await box.click();
  await expect(box).toBeChecked();
  const row = page.locator('li.task-row').filter({ has: box });
  const meta = row.locator('.task-time');
  await expect(meta).toContainText('ticked');
  expect(await meta.evaluate((el) => getComputedStyle(el).textDecorationLine)).toBe('none');
  expect(await row.locator('.task-title').evaluate((el) => getComputedStyle(el).textDecorationLine)).toContain('line-through');
});
