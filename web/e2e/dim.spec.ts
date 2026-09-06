import type { Page } from '@playwright/test';
import { test, expect } from './test';

/** The engine raises dim when the power is off and it is dark — 03:00, in a blackout, on a box
 * running off a battery. It used to be `filter: brightness(0.55)` on `body`, which made `body` the
 * containing block for every fixed overlay and dropped the contrast floor through the floor. */
async function goDim(page: Page, path: string) {
  await page.goto(path);
  await page.evaluate(() => { document.documentElement.dataset.dim = 'on'; });
}

function luminance(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

test('dim keeps the 7:1 floor in every theme, and dims nothing with a filter', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  for (const theme of ['field', 'mono']) {
    await page.addInitScript((t) => localStorage.setItem('sos.theme', t as string), theme);
    await goDim(page, '/');
    // A filter on body is what broke the overlays; nothing in dim is drawn with one.
    expect(await page.evaluate(() => getComputedStyle(document.body).filter)).toBe('none');
    const tokens = await page.evaluate(() => {
      const s = getComputedStyle(document.documentElement);
      const read = (n: string) => s.getPropertyValue(n).trim();
      return { ink: read('--ink'), muted: read('--ink-muted'), ground: read('--ground'), panel: read('--panel') };
    });
    for (const on of [tokens.ground, tokens.panel]) {
      expect(contrast(tokens.ink, on), `${theme}: ink on ${on}`).toBeGreaterThanOrEqual(7);
      expect(contrast(tokens.muted, on), `${theme}: muted on ${on}`).toBeGreaterThanOrEqual(7);
    }
  }
});

test('in dim every overlay still measures from the screen, not from the shell', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  await goDim(page, '/search?kiosk=1');
  await page.getByRole('combobox', { name: 'Search' }).first().click();
  const keyboard = page.getByTestId('keyboard');
  await expect(keyboard).toBeVisible();
  const box = (await keyboard.boundingBox())!;
  // The keyboard sits on the bottom edge of the 480 px screen, not 32 px down a 256 px shell.
  expect(Math.round(box.y + box.height)).toBe(480);
  expect(box.y).toBeGreaterThan(200);
  // and the search field it was opened for is above it, not behind it
  const field = (await page.getByRole('combobox', { name: 'Search' }).first().boundingBox())!;
  expect(field.y + field.height).toBeLessThanOrEqual(box.y);
});
