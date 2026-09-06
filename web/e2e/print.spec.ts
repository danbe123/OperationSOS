import { test, expect } from './test';

/* Print is a state, not a stylesheet: it is what the box looks like when a household takes a CPR
 * card, a scenario or the situation report to a printer — which is most likely at 03:00, in a power
 * cut, with the box in mono and dim on. That was exactly the case that printed three solid black
 * A4 pages, because the dim palette (0,3,0) outranked the print palette (0,2,0). */

const PAPER = 'rgb(243, 239, 228)';
const INK = 'rgb(27, 27, 27)';
const THEMES = ['field', 'mono'];
const PRINTABLE = ['/medical/card/cpr-adult', '/s/grid-collapse', '/p/pmr446', '/m/water', '/situation'];

async function palette(page: import('@playwright/test').Page) {
  return page.evaluate(() => {
    const s = getComputedStyle(document.documentElement);
    return {
      body: getComputedStyle(document.body).backgroundColor,
      ink: getComputedStyle(document.body).color,
      ground: s.getPropertyValue('--ground').trim(),
      panel: s.getPropertyValue('--panel').trim(),
      size: parseFloat(getComputedStyle(document.body).fontSize),
    };
  });
}

for (const theme of THEMES) {
  for (const dim of [false, true]) {
    test(`print is paper and ink in ${theme}${dim ? ' with dim on' : ''}`, async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem('sos.theme', t as string), theme);
      for (const route of PRINTABLE) {
        await page.goto(route);
        if (dim) await page.evaluate(() => { document.documentElement.dataset.dim = 'on'; });
        await page.emulateMedia({ media: 'print' });
        const shown = await palette(page);
        expect(shown.body, `${route} in ${theme}`).toBe(PAPER);
        expect(shown.ink, `${route} in ${theme}`).toBe(INK);
        expect(shown.ground).toBe('#f3efe4');
        expect(shown.panel).toBe('#ffffff');
        // 11 pt measured 14.67 px: under the floor the box holds itself to on a screen.
        expect(shown.size, `${route} body size`).toBeGreaterThanOrEqual(16);
        await page.emulateMedia({ media: 'screen' });
      }
    });
  }
}

test('a printed scenario is the whole guide, with no tab strip and every module open', async ({ page }) => {
  await page.goto('/s/grid-collapse');
  await expect(page.getByRole('tab', { name: 'Right now' })).toBeVisible();
  await page.emulateMedia({ media: 'print' });
  // The tabs are controls for a screen; on paper they are a row of dead buttons above one phase.
  await expect(page.locator('.tabs')).toBeHidden();
  for (const phase of ['Do this first', 'First 72 hours', 'Long term']) {
    await expect(page.getByRole('heading', { name: phase })).toBeVisible();
  }
  // Modules print open: an accordion on paper is a title with its content hidden underneath it.
  const closed = await page.locator('details.section:not([open])').count();
  expect(closed).toBe(0);
  await page.emulateMedia({ media: 'screen' });
});
