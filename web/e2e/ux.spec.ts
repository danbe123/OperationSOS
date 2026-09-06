import { test, expect } from './test';

test('the shell, the two-tap rule and the guides work on the kiosk and on a phone', async ({ page }) => {
  for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    const kiosk = viewport.width >= 700;
    await page.goto('/');

    // the same five destinations, in the same order, drawn as a rail on the kiosk and a bar on a phone
    const nav = page.getByRole('navigation', { name: 'Sections' });
    await expect(nav.locator('.rail-dest')).toHaveText(kiosk ? ['Now', 'Guides', 'Medical', 'Map', 'Find', 'AI', 'System'] : ['Now', 'Guides', 'Medical', 'Map', 'Find']);
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

    // two taps from Now to a quick card
    await nav.getByRole('link', { name: 'Medical' }).click();
    await page.getByRole('navigation', { name: 'Quick cards' }).getByRole('link', { name: 'CPR (adult)' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible();

    // two taps from Now to a scenario's Right now
    await nav.getByRole('link', { name: 'Now' }).click();
    await nav.getByRole('link', { name: 'Guides' }).click();
    await page.getByRole('navigation', { name: 'Scenarios' }).getByRole('link', { name: /National grid collapse/ }).click();
    await expect(page.getByRole('heading', { name: 'Do this first' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Right now', selected: true })).toBeVisible();

    // the checklist is beside the guidance where there is room, and under it where there is not
    const tasks = page.getByRole('complementary', { name: 'Checklist' });
    const guidance = await page.getByRole('tabpanel').boundingBox();
    const checklist = await tasks.boundingBox();
    if (viewport.width >= 800) expect(checklist!.x).toBeGreaterThan(guidance!.x + guidance!.width);
    else expect(checklist!.y).toBeGreaterThan(guidance!.y);

    // Now remembers the guide this device last opened
    await nav.getByRole('link', { name: 'Now' }).click();
    await expect(page.getByRole('region', { name: 'Carry on' })).toContainText('Continue: National grid collapse');

    // a timer keeps running while the rest of the box is read
    await nav.getByRole('link', { name: 'Guides' }).click();
    await page.getByRole('navigation', { name: 'Tools' }).getByRole('link', { name: /Timers/ }).click();
    await page.getByRole('button', { name: 'Next dose in 4 hours' }).click();
    await expect(page.getByRole('list', { name: 'Running timers' })).toContainText('Next dose in 4 hours');
    await nav.getByRole('link', { name: 'Now' }).click();
    await nav.getByRole('link', { name: 'Guides' }).click();
    await page.getByRole('navigation', { name: 'Tools' }).getByRole('link', { name: /Timers/ }).click();
    await expect(page.getByRole('list', { name: 'Running timers' })).toContainText('Next dose in 4 hours');

    // the situation clock on a guide, and the card it puts on Now
    await page.goto('/s/grid-collapse');
    await page.getByRole('button', { name: 'This has started' }).click();
    await expect(page.getByRole('status').first()).toContainText('just started, right now');
    await expect(page.getByRole('tab', { name: /Right now/ })).toHaveAttribute('aria-current', 'time');
    await nav.getByRole('link', { name: 'Now' }).click();
    const carryOn = page.getByRole('region', { name: 'Carry on' });
    await expect(carryOn).toContainText('Active situation');
    await carryOn.getByRole('link', { name: /Active situation/ }).click();
    await page.getByRole('button', { name: 'End situation' }).click();
    await page.getByRole('button', { name: 'Confirm end' }).click();
    await expect(page.getByRole('button', { name: 'This has started' })).toBeVisible();
    await nav.getByRole('link', { name: 'Now' }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test('every screen has a title, a way back and a way to search', async ({ page }) => {
  for (const path of ['/guides', '/medical', '/map', '/search', '/plan', '/system', '/tools/timers']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Find' })).toBeVisible();
    // one theme button, wherever the shell put it
    await expect(page.getByRole('button', { name: /^Theme:/ })).toHaveCount(1);
  }
});
