import { test, expect } from './test';

test('field manual shortcuts, checklist jump and resume work on kiosk and phone', async ({ page }) => {
  for (const viewport of [{ width: 853, height: 480 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    const help = page.getByRole('navigation', { name: 'Quick help' });
    await expect(help.getByRole('link', { name: /Someone is hurt/ })).toBeVisible();
    await page.screenshot({ path: `/tmp/sos-home-${viewport.width}.png` });
    await help.getByRole('link', { name: /Power is out/ }).click();
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
    await page.getByRole('link', { name: /All situations.*Browse/ }).click();
    await expect(page.getByRole('heading', { name: 'All situations', exact: true })).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});
