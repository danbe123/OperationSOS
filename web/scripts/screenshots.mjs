#!/usr/bin/env node
// Capture every entry in the redesign brief's coverage inventory at 853x480 and 390 wide, in all
// three themes, from the Playwright fixture server. The critique rounds reuse this:
//
//   node scripts/screenshots.mjs            # into docs/superpowers/critique/round-0
//   node scripts/screenshots.mjs round-3    # into that round's folder
//   node scripts/screenshots.mjs round-3 map   # only the shots whose name contains "map"
//
// The work itself lives in e2e/screenshots.spec.ts so it can use the same fixture state and routes
// as the browser suite; this wrapper only points it at a folder and reports what it wrote.
import { spawnSync } from 'node:child_process';
import { readdirSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const round = process.argv[2] ?? 'round-0';
const only = process.argv[3] ?? '';
const out = resolve(web, '..', 'docs/superpowers/critique', round);
mkdirSync(out, { recursive: true });

// `vite preview` serves dist from disk and Playwright reuses a server that is already up, so the
// build has to be refreshed here or a later round quietly photographs an older interface.
const built = spawnSync('pnpm', ['exec', 'vite', 'build'], { cwd: web, stdio: 'inherit' });
if (built.status !== 0) process.exit(built.status ?? 1);

const result = spawnSync(
  'pnpm',
  ['exec', 'playwright', 'test', 'e2e/screenshots.spec.ts', '--workers=2', '--reporter=line'],
  {
    cwd: web,
    stdio: 'inherit',
    env: { ...process.env, SOS_SHOTS: '1', SOS_SHOTS_DIR: out, SOS_SHOTS_ONLY: only },
  },
);

const written = readdirSync(out).filter((f) => f.endsWith('.png'));
console.log(`\n${written.length} screenshots in ${out}`);
process.exit(result.status ?? 1);
