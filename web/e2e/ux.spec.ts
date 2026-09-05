import { test, expect } from './test';

test('field manual shortcuts, checklist jump and resume work on kiosk and phone', async ({ page }) => {
  for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    const scenarios = page.getByRole('navigation', { name: 'Scenarios' });
    await expect(scenarios.getByRole('link', { name: /National grid collapse/ })).toBeVisible();
    await page.screenshot({ path: `/tmp/sos-home-${viewport.width}.png` });
    await scenarios.getByRole('link', { name: /National grid collapse/ }).click();
    await expect(page.getByRole('heading', { name: 'Do this first' })).toBeVisible();
    await page.screenshot({ path: `/tmp/sos-scenario-${viewport.width}.png` });
    if (viewport.width < 780) {
      await page.getByRole('link', { name: 'Household checklist' }).click();
    } else {
      const sidebar = page.getByRole('complementary', { name: 'Checklist' });
      const guidance = await page.getByRole('tabpanel').boundingBox();
      const checklist = await sidebar.boundingBox();
      expect(checklist!.x).toBeGreaterThan(guidance!.x + guidance!.width);
      await page.locator('.layout-main').evaluate((el) => { el.scrollTop = 250; });
    }
    await expect(page.getByRole('heading', { name: 'Checklist', exact: true })).toBeInViewport();
    await page.getByRole('link', { name: 'Home', exact: true }).click();
    await expect(page.getByRole('link', { name: /Continue: National grid collapse/ })).toBeVisible();
    // tools: the sixth tile, the tool list and a timer that keeps running while reading a playbook
    await page.getByRole('navigation', { name: 'Main sections' }).getByRole('link', { name: /Tools/ }).click();
    const tools = page.getByRole('navigation', { name: 'Tools' });
    await expect(tools.getByRole('link')).toHaveCount(7);
    await tools.getByRole('link', { name: /Timers/ }).click();
    await page.getByRole('button', { name: 'Next dose in 4 hours' }).click();
    await expect(page.getByRole('list', { name: 'Running timers' })).toContainText('Next dose in 4 hours');
    // situation clock: start it on the playbook, see the phase badge, and the card on Home
    await page.goto('/s/grid-collapse');
    await page.getByRole('button', { name: 'This has started' }).click();
    await expect(page.getByRole('status')).toContainText('just started, right now');
    await expect(page.getByRole('tab', { name: /Right now/ })).toHaveAttribute('aria-current', 'time');
    await page.getByRole('link', { name: 'Home', exact: true }).click();
    await expect(page.getByRole('link', { name: /Active situation/ })).toContainText('National grid collapse');
    await page.getByRole('link', { name: /Active situation/ }).click();
    await page.getByRole('button', { name: 'End situation' }).click();
    await page.getByRole('button', { name: 'Confirm end' }).click();
    await expect(page.getByRole('button', { name: 'This has started' })).toBeVisible();
    await page.getByRole('link', { name: 'Home', exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});
