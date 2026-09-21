import { test, expect, MODE } from './test';

const probes = ['/generate_204', '/gen_204', '/hotspot-detect.html', '/library/test/success.html', '/connecttest.txt', '/ncsi.txt', '/canonical.html', '/success.txt'];

test('captive-portal probe paths redirect to the welcome page (dev stack)', async ({ request }) => {
  test.skip(MODE !== 'dev', 'the probe redirects are Caddy\'s, and fixture mode is `vite preview`, which has no Caddy');
  for (const p of probes) {
    const res = await request.get(p, { maxRedirects: 0 });
    expect(res.status(), p).toBe(302);
    expect(res.headers()['location'], p).toBe('http://10.42.0.1/welcome');
  }
});

test('/welcome and /starting load with no app JavaScript', async ({ page, request }) => {
  const suffix = MODE === 'dev' ? '' : '.html';
  // Read the served bodies over HTTP rather than by navigating: /starting redirects itself the
  // moment the box answers, and a pending redirect interrupts the next navigation in the loop.
  for (const path of ['/welcome', '/starting']) {
    const html = await (await request.get(path + suffix)).text();
    expect(html, path).not.toMatch(/<script[^>]+src=/);
  }
  const scripts: string[] = [];
  page.on('request', (r) => { if (r.resourceType() === 'script') scripts.push(r.url()); });
  await page.goto('/welcome' + suffix);
  await expect(page.getByText('Open http://10.42.0.1 in your browser (or http://sos.box)')).toBeVisible();
  await expect(page.locator('svg')).toBeVisible();
  expect(scripts.filter((s) => s.includes('/assets/') || s.includes('/src/'))).toEqual([]);
  await page.goto('/starting' + suffix);
  // /starting polls /api/status every two seconds until the box answers; under a full parallel run
  // the first poll can lose the race with everything else starting up, so allow a few rounds.
  await expect(page).toHaveURL(/\/\?kiosk=1$/, { timeout: 30_000 });
});
