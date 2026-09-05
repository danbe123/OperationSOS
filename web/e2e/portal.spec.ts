import { test, expect, MODE } from './test';

const probes = ['/generate_204', '/gen_204', '/hotspot-detect.html', '/library/test/success.html', '/connecttest.txt', '/ncsi.txt', '/canonical.html', '/success.txt'];

test('captive-portal probe paths redirect to the welcome page (dev stack)', async ({ request }) => {
  test.skip(MODE !== 'dev', 'needs Caddy');
  for (const p of probes) {
    const res = await request.get(p, { maxRedirects: 0 });
    expect(res.status(), p).toBe(302);
    expect(res.headers()['location'], p).toBe('http://10.42.0.1/welcome');
  }
});

test('/welcome and /starting load with no app JavaScript', async ({ page }) => {
  const suffix = MODE === 'dev' ? '' : '.html';
  for (const path of ['/welcome', '/starting']) {
    const scripts: string[] = [];
    page.on('request', (r) => { if (r.resourceType() === 'script') scripts.push(r.url()); });
    // Read the served body straight off the navigation response, not the live DOM: /starting redirects itself
    // (via a fetch that a fixture route answers almost immediately), and by the time a follow-up page.content()
    // would run the page can already be mid-navigation.
    const response = await page.goto(path + suffix, { waitUntil: 'domcontentloaded' });
    expect(scripts.filter((s) => s.includes('/assets/') || s.includes('/src/'))).toEqual([]);
    const html = await response!.text();
    expect(html).not.toMatch(/<script[^>]+src=/);
  }
  await page.goto('/welcome' + suffix);
  await expect(page.getByText('Open http://10.42.0.1 in your browser (or http://sos.box)')).toBeVisible();
  await expect(page.locator('svg')).toBeVisible();
  await page.goto('/starting' + suffix);
  // /starting polls /api/status every two seconds until the box answers; under a full parallel run
  // the first poll can lose the race with everything else starting up, so allow a few rounds.
  await expect(page).toHaveURL(/\/\?kiosk=1$/, { timeout: 30_000 });
});
