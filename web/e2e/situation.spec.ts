import type { Page } from '@playwright/test';
import { test, expect, openDetails, setCondition } from './test';

test('the power goes off: the band, the forecast, a job ticked, and everything back on', async ({ page }) => {
  await page.goto('/');
  // peacetime: Now asks what the situation is and puts every answer on the wall, and there is no band
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  const situations = page.getByRole('navigation', { name: 'Scenarios' });
  await expect(situations.getByRole('link', { name: /National grid collapse/ })).toBeVisible();
  // No score, no register: the front door asks nobody to describe themselves first.
  await expect(page.locator('main')).not.toContainText('out of 100');
  await expect(page.getByRole('group', { name: 'Situation now' })).toBeHidden();

  // set the power off, an hour ago, from the sheet
  await page.goto('/situation');
  await setCondition(page, 'power', 'Off', 'About an hour ago');

  // Now leads with what to do, and the band says what is off
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  const band = page.getByRole('group', { name: 'Situation now' });
  await expect(band.getByRole('link', { name: '1 off' })).toBeVisible();
  const coming = page.getByRole('region', { name: 'Coming up' });
  await expect(coming).toContainText('Freezer food unsafe');
  await expect(coming).toContainText('in 23 h');
  const doing = page.getByRole('region', { name: 'Right now' }).first();
  await expect(doing).toContainText('Fill the bath and every container');

  // tick the bath off; the box saves it and the tick sticks
  await doing.getByRole('checkbox', { name: /Fill the bath/ }).click();
  await expect(doing.getByRole('checkbox', { name: /Fill the bath/ })).toBeChecked();
  await page.getByRole('link', { name: 'All of them' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Things to do' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Right now' })).toContainText('Keep the fridge and freezer doors shut');
  // The count is said once, in a sentence, not three times.
  await expect(page.locator('.task-count')).toHaveCount(1);
  await expect(page.locator('.task-count')).toContainText('3 to do');

  // the band follows onto every other screen
  await page.goto('/p/pmr446');
  await expect(band.getByRole('link', { name: '1 off' })).toBeVisible();
  await band.getByRole('link', { name: '1 off' }).click();

  // end with everything working again
  await setCondition(page, 'power', 'Working');
  // The states stay on the row whatever it is holding: no door in front of the door.
  await expect(page.locator('#power')).toContainText('working');
  await expect(page.locator('#power').getByRole('group', { name: 'Mains power' })).toBeVisible();
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
  await expect(page.getByRole('group', { name: 'Situation now' })).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('a drill runs the whole thing without touching the real conditions', async ({ page }) => {
  await page.goto('/situation');
  await page.getByLabel('Drill scenario').selectOption('grid-collapse');
  await page.getByLabel('Drill started').selectOption('2');
  await page.getByRole('button', { name: 'Start drill' }).click();
  await expect(page.getByRole('group', { name: 'Situation now' })).toContainText('Drill');
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  const band = page.getByRole('group', { name: 'Situation now' });
  await expect(band).toContainText('Drill');
  await expect(band).toContainText('National grid collapse');
  await page.getByRole('button', { name: 'End drill' }).click();
  await expect(page.getByRole('button', { name: 'End drill' })).toBeHidden();
  // The debrief is a modal now, and a modal is answered before the box carries on.
  await page.getByRole('dialog', { name: 'How the drill went' }).getByRole('button', { name: 'Close' }).click();
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  await expect(page.getByRole('heading', { level: 1, name: "What's the situation?" })).toBeVisible();
});

test('with both phone networks down the pages say the numbers will not connect', async ({ page }) => {
  await page.goto('/situation');
  for (const id of ['mobile', 'landline'] as const) {
    await setCondition(page, id, 'Off');
  }
  await page.goto('/p/pmr446');
  const notice = page.getByRole('status').filter({ hasText: 'will not connect' });
  await expect(notice).toBeVisible();
  await notice.getByRole('link', { name: 'Getting help without phones' }).click();
  await expect(page).toHaveURL(/\/p\/no-phones$/);
});

test('the sheet and Now fit a phone as well as the kiosk', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/situation');
  await setCondition(page, 'water', 'Off');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Now' }).click();
  // A phone's band carries the count and the way to the sheet; the heading names the service.
  await expect(page.getByRole('group', { name: 'Situation now' })).toContainText('1 off');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Water off');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('the situation carries to another box as codes, and comes back in', async ({ page }) => {
  await page.goto('/situation');
  const carry = page.getByRole('region', { name: 'Carry it to another box' });
  await carry.getByRole('button', { name: 'Export as codes' }).click();
  const codes = carry.getByRole('group', { name: 'Situation codes' });
  await expect(codes).toContainText('Code 1 of');
  await expect(codes.getByRole('img', { name: /Situation code 1 of/ })).toBeVisible();
  await expect(codes.getByRole('button', { name: 'Previous' })).toBeDisabled();
  await codes.getByRole('button', { name: 'Next' }).click();
  await expect(codes).toContainText('Code 2 of');
  await carry.getByRole('button', { name: 'Copy the codes as text' }).click();
  await expect(carry.getByRole('textbox', { name: /Situation code 2 as text/ })).not.toBeEmpty();

  await carry.getByRole('textbox', { name: 'Situation to bring in' }).fill('{"i":0,"n":1,"d":"x"}');
  await carry.getByRole('button', { name: 'Bring it in' }).click();
  const summary = carry.getByRole('status', { name: 'What came in' });
  await expect(summary).toContainText('Brought in from the other box.');
  await expect(summary).toContainText('conditions: 2 updated, 8 kept');
});

/** The value a token really computes to in the palette on the screen, whatever it was written as:
 * a probe element takes `var(--x)` as its ground and the browser hands back the resolved colour. */
async function token(page: Page, name: string): Promise<string> {
  return page.evaluate((n) => {
    const probe = document.createElement('div');
    probe.style.background = `var(${n})`;
    document.body.append(probe);
    const colour = getComputedStyle(probe).backgroundColor;
    probe.remove();
    return colour;
  }, name);
}

const PALETTES = ['field', 'mono'].flatMap((theme) => [{ theme, dim: false }, { theme, dim: true }]);

test('the chosen state is filled and marked, not merely coloured, in all four palettes', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  for (const { theme, dim } of PALETTES) {
    const where = `${theme}${dim ? ' dim' : ''}`;
    await page.addInitScript((t) => localStorage.setItem('sos.theme', t as string), theme);
    await page.goto('/situation');
    if (dim) await page.evaluate(() => { document.documentElement.dataset.dim = 'on'; });
    await setCondition(page, 'power', 'Off');
    const group = page.getByRole('group', { name: 'Mains power' });
    const chosen = group.getByRole('button', { name: 'Off' });

    // The chosen button is filled with a tint of its own colour, and the other two sit on the raised
    // control tone: without that the only difference between the three was a colour.
    const [raised, panel] = [await token(page, '--raised'), await token(page, '--panel')];
    const ground = await chosen.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(ground, `${where}: the chosen state's ground`).not.toBe(raised);
    expect(ground, `${where}: the chosen state against the panel`).not.toBe(panel);
    const others = await group.getByRole('button', { name: 'Working' }).evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(others, `${where}: an unchosen state's ground`).toBe(raised);

    // and it carries a 2 px edge in the state's own colour
    const edge = await chosen.evaluate((el) => `${getComputedStyle(el).borderTopWidth} ${getComputedStyle(el).borderTopColor}`);
    expect(edge, `${where}: the edge is the danger colour`).toBe(`2px ${await token(page, '--danger')}`);

    // and exactly one of the three buttons wears a symbol: the one the box is holding
    await expect(group.locator('.state-glyph'), `${where}: symbols in the group`).toHaveCount(1);
    await expect(chosen.locator('.state-glyph')).toHaveText('✕');

    await setCondition(page, 'power', 'Working');
  }
});

test('the since answer is the one the box stores, and the row says so', async ({ page }) => {
  await page.goto('/situation');
  await setCondition(page, 'power', 'Off', 'About an hour ago');
  // Come back to the row from cold: the time must be read out of the box, not left over from a tap.
  await page.reload();
  await expect(page.locator('#power')).toContainText('for 1 h');
  // The question is asked on the row that changed and put away once it is answered.
  await expect(page.locator('#power').getByRole('group', { name: 'Mains power: since when?' })).toBeHidden();
  // A condition nobody has touched offers "Just now" for the change about to be made.
  await page.locator('#gas').getByRole('group', { name: 'Gas' }).getByRole('button', { name: 'Off', exact: true }).click();
  const when = page.locator('#gas').getByRole('group', { name: 'Gas: since when?' });
  await expect(when.getByRole('button', { name: 'Just now' })).toHaveAttribute('aria-pressed', 'true');
  await when.getByRole('button', { name: 'Cancel' }).click();
  // and what the box knows beyond the state is behind Details.
  await openDetails(page, 'gas');
  await expect(page.locator('#gas')).toContainText('Nobody has set this yet.');
});

test('carrying a situation describes the paste, and says its trouble under the button', async ({ page }) => {
  await page.setViewportSize({ width: 853, height: 480 });
  await page.goto('/situation');
  const carry = page.getByRole('region', { name: 'Carry it to another box' });
  // There is no camera in the box, so nothing on the panel may ask for a photograph or a scan.
  await expect(carry).toContainText('type or paste each code’s text in order');
  expect(await carry.textContent()).not.toMatch(/scan|photograph|JSON/i);

  const box = carry.getByRole('textbox', { name: 'Situation to bring in' });
  await box.fill('{"i":0,"n":3,"d":"one"}');
  await expect(carry).toContainText('Code 1 of 3 read.');

  await page.route('**/api/situation/import', (route) => route.fulfill({
    status: 422, contentType: 'application/json',
    body: JSON.stringify({ detail: 'a scanned chunk is not a QR chunk: expected {"i", "n", "d"}' }),
  }));
  const button = carry.getByRole('button', { name: 'Bring it in' });
  await button.click();
  const said = carry.getByRole('alert');
  await expect(said).toContainText('That is not one of this box’s codes.');
  // Under the button that caused it: the developer sentence used to be half a screen above it.
  const [pressed, trouble] = [(await button.boundingBox())!, (await said.boundingBox())!];
  expect(trouble.y).toBeGreaterThanOrEqual(pressed.y);
  expect(trouble.y - (pressed.y + pressed.height)).toBeLessThan(48);
});
