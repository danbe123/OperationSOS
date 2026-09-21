import { test, expect } from './test';

test('the shell, the way to a card, a scenario and a timer, and the clock work on the kiosk and on a phone', async ({ page }) => {
  for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    const kiosk = viewport.width >= 700;
    await page.goto('/');

    // the same five destinations, in the same order, drawn as a rail on the kiosk and a bar on a phone
    const nav = page.getByRole('navigation', { name: 'Sections' });
    await expect(nav.locator('.rail-dest')).toHaveText(kiosk ? ['Now', 'Library', 'Kit', 'Map', 'Find', 'AI', 'System'] : ['Now', 'Library', 'Kit', 'Map', 'Find']);
    await expect(nav.getByRole('link', { name: 'Now' })).toHaveAttribute('aria-current', 'page');
    const navBox = (await nav.boundingBox())!;
    const mainBox = (await page.locator('.app-main').boundingBox())!;
    if (kiosk) {
      expect(navBox.width).toBeLessThanOrEqual(100);
      expect(navBox.x + navBox.width).toBeLessThanOrEqual(mainBox.x + 1);   // a rail, to the left
    } else {
      expect(navBox.y).toBeGreaterThanOrEqual(mainBox.y + mainBox.height - 1); // a bar, along the bottom
      expect(navBox.width).toBeGreaterThan(300);
    }

    // Medical is a shelf of the Library now, not a place on the rail: Now, Library, the Medical shelf, the card
    await nav.getByRole('link', { name: 'Library' }).click();
    await page.getByRole('navigation', { name: 'Shelves' }).getByRole('link', { name: /Medical/ }).click();
    await expect(nav.getByRole('link', { name: 'Library' })).toHaveAttribute('aria-current', 'page');
    await page.getByRole('navigation', { name: 'Quick cards' }).getByRole('link', { name: 'CPR (adult)' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

    // one tap from Now to a scenario's Right now: the situations are the front door's answers
    await nav.getByRole('link', { name: 'Now' }).click();
    await page.getByRole('navigation', { name: 'Scenarios' }).getByRole('link', { name: /National grid collapse/ }).click();
    await expect(page.getByRole('heading', { name: 'Do this first' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Right now', selected: true })).toBeVisible();

    // the jobs sit beside the guidance where there is room, and above it where there is not
    const tasks = page.getByRole('complementary', { name: 'Things to do for this guide' });
    const guidance = await page.getByRole('tabpanel').boundingBox();
    const checklist = await tasks.boundingBox();
    if (viewport.width >= 800) expect(checklist!.x).toBeGreaterThan(guidance!.x + guidance!.width);
    else expect(checklist!.y).toBeLessThan(guidance!.y);

    // every phase tab is reachable: none is scrolled off the end with nothing to say it exists
    const tabs = page.getByRole('tab');
    const strip = (await page.locator('.tabs').boundingBox())!;
    for (const box of await Promise.all((await tabs.all()).map((t) => t.boundingBox()))) {
      expect(box!.x + box!.width).toBeLessThanOrEqual(strip.x + strip.width + 1);
    }

    // a timer keeps running while the rest of the box is read; the tools are on the Guides shelf
    await nav.getByRole('link', { name: 'Library' }).click();
    await page.getByRole('navigation', { name: 'Shelves' }).getByRole('link', { name: /Guides/ }).click();
    await page.getByRole('navigation', { name: 'Tools' }).getByRole('link', { name: /Timers/ }).click();
    await page.getByRole('button', { name: 'Next dose in 4 hours' }).click();
    await expect(page.getByRole('list', { name: 'Running timers' })).toContainText('Next dose in 4 hours');
    await nav.getByRole('link', { name: 'Now' }).click();
    await nav.getByRole('link', { name: 'Library' }).click();
    await page.getByRole('navigation', { name: 'Shelves' }).getByRole('link', { name: /Guides/ }).click();
    await page.getByRole('navigation', { name: 'Tools' }).getByRole('link', { name: /Timers/ }).click();
    await expect(page.getByRole('list', { name: 'Running timers' })).toContainText('Next dose in 4 hours');

    // the situation clock on a guide, and the band it puts on every screen
    await page.goto('/s/grid-collapse');
    await page.getByRole('button', { name: /Start the clock/ }).click();
    // The slot that held Start now says how long it has been running.
    await expect(page.getByRole('status').first()).toContainText('just started');
    await expect(page.getByRole('tab', { name: /Right now/ })).toHaveAttribute('aria-current', 'time');
    await expect(page.getByRole('group', { name: 'Situation now' })).toContainText('National grid collapse');
    await page.getByRole('button', { name: /just started/ }).click();
    await page.getByRole('button', { name: 'End situation' }).click();
    await expect(page.getByText('End this situation?')).toBeVisible();
    await page.getByRole('button', { name: 'Confirm', exact: true }).click();
    await expect(page.getByRole('button', { name: /Start the clock/ })).toBeVisible();
    // ended here, the band goes from every screen at once
    await expect(page.getByRole('group', { name: 'Situation now' })).toBeHidden();
    await nav.getByRole('link', { name: 'Now' }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

/* Every screen says where it is. Most do it with a heading; Find and the Kit's front are drawn without
 * one on purpose (the rail already says which they are, and the row went to the field or the tabs), so
 * for those the name is on the landmark and in the tab title instead. The old addresses for Guides and
 * Medical are redirects into the Library, and must land on their shelf. The box's own System screen is
 * not a destination: nothing on the bar is lit for it. */
const SCREENS: { path: string; lands: string; title: string; heading: boolean; back: boolean; rail: string | null }[] = [
  { path: '/guides', lands: '/library/guides', title: 'Guides', heading: true, back: true, rail: 'Library' },
  { path: '/medical', lands: '/library/medical', title: 'Medical', heading: true, back: true, rail: 'Library' },
  { path: '/map', lands: '/map', title: 'Map', heading: true, back: false, rail: 'Map' },
  { path: '/search', lands: '/search', title: 'Find', heading: false, back: false, rail: 'Find' },
  { path: '/kit', lands: '/kit', title: 'Kit', heading: false, back: false, rail: 'Kit' },
  { path: '/notes', lands: '/notes', title: 'Notes and pins', heading: true, back: true, rail: 'Now' },
  { path: '/system', lands: '/system', title: 'System', heading: true, back: true, rail: null },
  { path: '/tools/timers', lands: '/tools/timers', title: 'Timers', heading: true, back: true, rail: 'Library' },
];

for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
  test(`every screen has a title, a way back and a way to search at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const screen of SCREENS) {
      await page.goto(screen.path);
      await expect(page, screen.path).toHaveURL(new RegExp(`${screen.lands}$`));
      // the screen is named, on its landmark and in the tab, whether or not it draws a heading
      await expect(page.locator('main#main'), screen.path).toHaveAttribute('aria-label', screen.title);
      await expect(page, screen.path).toHaveTitle(`${screen.title} · SOS`);
      const headings = page.getByRole('heading', { level: 1 });
      if (screen.heading) await expect(headings.first(), screen.path).toHaveText(screen.title);
      else await expect(headings, `${screen.path} is drawn without a heading`).toHaveCount(0);
      // a way to search: Find is on the rail or the bar wherever you are
      const nav = page.getByRole('navigation', { name: 'Sections' });
      await expect(nav.getByRole('link', { name: 'Find' }), screen.path).toBeVisible();
      // the rail or bar lights the destination the screen belongs to
      const lit = nav.locator('.rail-dest[aria-current="page"]');
      if (screen.rail) await expect(lit, screen.path).toHaveText(screen.rail);
      // a way back on every screen that has one to give
      await expect(page.getByRole('button', { name: 'Back', exact: true }), screen.path).toHaveCount(screen.back ? 1 : 0);
      // one theme button, wherever the shell put it
      await expect(page.getByRole('button', { name: /^Change the theme/ }), `${screen.path}: the theme control`).toHaveCount(1);
    }
  });
}
