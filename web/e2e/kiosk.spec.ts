import { test, expect } from './test';
import { PIN } from './fixtures/state';

test('kiosk keyboard appears on focus, types, and picks a suggestion', async ({ page }) => {
  // Now has no search field of its own any more; the Library carries the one in the screen head.
  await page.goto('/library?kiosk=1');
  await page.getByRole('combobox', { name: 'Search' }).click();
  const keyboard = page.getByTestId('keyboard');
  await expect(keyboard).toBeVisible();
  const box = await keyboard.boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(200);
  const q = await keyboard.locator('[data-skbtn="q"]').boundingBox();
  // 48 px is the floor the brief sets; the keys share the width of the content column, which the
  // keyboard now covers on its own so the rail stays whole.
  expect(q!.width).toBeGreaterThanOrEqual(48);
  for (const k of ['w', 'a', 't']) await keyboard.locator(`[data-skbtn="${k}"]`).click();
  await expect(page.getByRole('combobox', { name: 'Search' })).toHaveValue('wat');
  await page.getByRole('option', { name: /Water disinfection/ }).click();
  await expect(page).toHaveURL(/\/p\/water-disinfection$/);
});

test('kiosk PIN pad unlocks a gated action', async ({ page, state }) => {
  state.status.pin_required = true;
  await page.goto('/system?kiosk=1');
  await page.getByRole('button', { name: 'Direct laptop link' }).click();
  const dialog = page.getByRole('dialog', { name: 'Admin PIN' });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('PIN').click();
  const keyboard = page.getByTestId('keyboard');
  await expect(keyboard.locator('[data-skbtn="7"]')).toBeVisible();
  await expect(keyboard.locator('[data-skbtn="q"]')).toHaveCount(0);
  for (const d of PIN) await keyboard.locator(`[data-skbtn="${d}"]`).click();
  await keyboard.locator('[data-skbtn="{enter}"]').click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: 'Direct laptop link' })).toHaveAttribute('aria-pressed', 'true');
});
