import { existsSync, readFileSync } from 'node:fs';

const required = [
  'public/pdfjs/web/viewer.html',
  'public/pdfjs/build/pdf.mjs',
  'public/pdfjs/build/pdf.worker.mjs',
  'public/fonts/vt323-v18-latin-regular.woff2',
  'public/fonts/inter-v20-latin-regular.woff2',
  'public/fonts/source-serif-4-v14-latin-600.woff2',
  'public/welcome.html',
  'public/starting.html',
  'public/icons/icon-192.png',
  'public/icons/icon-512.png',
];
const missing = required.filter((p) => !existsSync(new URL(`../${p}`, import.meta.url)));
if (missing.length > 0) {
  console.error(`Missing bundled assets:\n  ${missing.join('\n  ')}\nRun "pnpm vendor" for PDF.js, "pnpm welcome" and "pnpm icons" for generated pages; fonts are committed.`);
  process.exit(1);
}
// The viewer must carry the box's policy patch (see vendor-pdfjs.sh): the theme stylesheet is inline,
// and nothing on the box may call out.
const viewer = readFileSync(new URL('../public/pdfjs/web/viewer.html', import.meta.url), 'utf8');
if (!viewer.includes("style-src 'self' 'unsafe-inline'") || /connect-src \*/.test(viewer)) {
  console.error('public/pdfjs/web/viewer.html is the stock viewer without the policy patch: run "pnpm vendor".');
  process.exit(1);
}
console.log('bundled assets present');
