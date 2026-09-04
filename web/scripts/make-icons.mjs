import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const dir = new URL('../public/icons/', import.meta.url);
mkdirSync(dir, { recursive: true });
const svg = (size) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 100 100">
<rect width="100" height="100" rx="18" fill="#0a0f0a"/>
<circle cx="50" cy="50" r="36" fill="none" stroke="#39ff7a" stroke-width="6"/>
<text x="50" y="61" text-anchor="middle" font-family="monospace" font-size="30" font-weight="700" fill="#39ff7a">SOS</text>
</svg>`;
writeFileSync(new URL('icon.svg', dir), svg(512));

const browser = await chromium.launch();
for (const size of [192, 512]) {
  const page = await browser.newPage({ viewport: { width: size, height: size } });
  await page.setContent(`<html><body style="margin:0;background:#0a0f0a">${svg(size)}</body></html>`);
  await page.screenshot({ path: fileURLToPath(new URL(`icon-${size}.png`, dir)) });
  await page.close();
  console.log(`wrote public/icons/icon-${size}.png`);
}
await browser.close();
