import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { expect, type Page } from '@playwright/test';
import { test } from './test';
import type { FixtureState } from './fixtures/state';
import { WIKI } from '../tests/fixtures/api';

/* Every entry in the redesign brief's coverage inventory, captured at 853x480 (the kiosk) and 390
 * wide (a phone) in field and mono. Run it with `node scripts/screenshots.mjs <round>`;
 * it is skipped by the ordinary browser suite unless SOS_SHOTS is set. */

const OUT = process.env.SOS_SHOTS_DIR ?? resolve('..', 'docs/superpowers/critique/round-0');
const THEMES = (process.env.SOS_SHOTS_THEMES ?? 'field,mono').split(',');
/** A comma-separated list of substrings: `node scripts/screenshots.mjs round-0 map,keyboard`. */
const ONLY = (process.env.SOS_SHOTS_ONLY ?? '').split(',').map((x) => x.trim()).filter(Boolean);
const SIZES = [
  { width: 853, height: 480, kiosk: true },
  { width: 390, height: 844, kiosk: false },
];

/** `dim` photographs a shot in the engine's dim mode — the state it raises when the power is off and
 * it is dark. It is set after the screen is up so the theme under test stays the theme under test. */
type Shot = { name: string; go: (page: Page, state: FixtureState) => Promise<void>; dim?: boolean; print?: boolean };

const hour = () => new Date(Date.now() - 3_600_000).toISOString();
function off(state: FixtureState, ...ids: ('power' | 'water' | 'mobile' | 'landline' | 'internet')[]) {
  for (const id of ids) state.conditions = { ...state.conditions, [id]: { ...state.conditions[id], state: 'off', since: hour(), set_by: 'phone' } };
}

async function settle(page: Page) {
  // The map keeps a tile request in flight for as long as it is on screen, so networkidle is a
  // best-effort settle with a short leash rather than something to wait 30 seconds for.
  await page.waitForLoadState('networkidle', { timeout: 2500 }).catch(() => undefined);
  await page.waitForTimeout(250);
}

const SHOTS: Shot[] = [
  { name: 'now-peacetime', go: async (p) => { await p.goto('/'); await expect(p.getByRole('navigation', { name: 'Scenarios' })).toBeVisible(); } },
  // The front door with something off: the same question, tiles and services, with the row's own
  // "off" and one line to the sheet. The briefing it used to turn into is `situation-power-off`.
  { name: 'now-power-off', go: async (p, s) => { off(s, 'power'); await p.goto('/'); await expect(p.getByRole('link', { name: 'What to do now' })).toBeVisible(); } },
  { name: 'now-phones-down', go: async (p, s) => { off(s, 'mobile', 'landline'); await p.goto('/'); await expect(p.getByText('999 will not connect')).toBeVisible(); } },
  { name: 'now-drill', go: async (p, s) => { off(s, 'power'); s.drill = true; s.situation = { slug: 'grid-collapse', title: 'National grid collapse', started_at: hour(), elapsed_s: 3600, phase: 'right-now' }; await p.goto('/'); await expect(p.getByRole('group', { name: 'Situation now' })).toBeVisible(); } },
  { name: 'now-engine-down', go: async (p) => { await p.route('**/api/situation/view', (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"the engine is not answering"}' })); await p.goto('/'); await expect(p.getByText(/The box cannot read the situation/)).toBeVisible(); } },
  // Nothing typed in at all: the state a box is in on the day it is hung on the wall, and the state
  // it is useful in — the front door asks what the situation is and every answer is a tile, with no
  // form to fill in first.
  { name: 'now-nothing-typed-in', go: async (p) => { await p.goto('/'); await expect(p.getByRole('link', { name: /National grid collapse/ })).toBeVisible(); } },
  { name: 'situation-power-off', go: async (p, s) => { off(s, 'power'); await p.goto('/situation'); await expect(p.getByRole('region', { name: 'Right now' })).toBeVisible(); } },
  { name: 'situation-sheet', go: async (p, s) => { off(s, 'power', 'water'); await p.goto('/situation'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
  { name: 'situation-carry', go: async (p) => { await p.goto('/situation'); await p.getByRole('button', { name: 'Export as codes' }).click(); await expect(p.getByRole('group', { name: 'Situation codes' })).toBeVisible(); await p.getByRole('group', { name: 'Situation codes' }).scrollIntoViewIfNeeded(); } },
  { name: 'situation-drill', go: async (p) => { await p.goto('/situation#drill'); await p.getByLabel('Drill scenario').selectOption('grid-collapse'); await p.getByRole('region', { name: 'Practise a drill' }).scrollIntoViewIfNeeded(); } },
  { name: 'tasks', go: async (p, s) => { off(s, 'power'); await p.goto('/tasks'); await expect(p.getByRole('heading', { level: 1, name: 'Things to do' })).toBeVisible(); } },
  { name: 'tasks-empty', go: async (p) => { await p.goto('/tasks'); await expect(p.getByText('Nothing to do.')).toBeVisible(); } },
  { name: 'board', go: async (p, s) => { off(s, 'power', 'water'); s.situation = { slug: 'grid-collapse', title: 'National grid collapse', started_at: hour(), elapsed_s: 3600, phase: 'right-now' }; await p.goto('/board'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
  { name: 'board-peacetime', go: async (p) => { await p.goto('/board'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
  { name: 'guides', go: async (p) => { await p.goto('/guides'); await expect(p.getByRole('navigation', { name: 'Phone and radio' })).toBeVisible(); } },
  { name: 'guides-filtered', go: async (p) => { await p.goto('/guides'); await p.getByRole('searchbox', { name: 'Filter these guides' }).fill('water'); await expect(p.getByRole('status')).toBeVisible(); } },
  { name: 'scenario-right-now', go: async (p) => { await p.goto('/s/grid-collapse'); await expect(p.getByRole('heading', { name: 'Do this first' })).toBeVisible(); } },
  { name: 'scenario-later', go: async (p) => { await p.goto('/s/grid-collapse?tab=first-72-hours'); await expect(p.getByRole('heading', { name: 'First 72 hours' })).toBeVisible(); } },
  { name: 'module', go: async (p) => { await p.goto('/m/water'); await expect(p.getByRole('heading', { level: 1, name: 'Water' })).toBeVisible(); } },
  { name: 'page', go: async (p) => { await p.goto('/p/pmr446'); await expect(p.getByRole('heading', { level: 1, name: 'PMR446 radio' })).toBeVisible(); } },
  { name: 'medical', go: async (p) => { await p.goto('/medical'); await expect(p.getByRole('navigation', { name: 'Quick cards' })).toBeVisible(); } },
  { name: 'medical-phones-down', go: async (p, s) => { off(s, 'mobile', 'landline'); await p.goto('/medical'); await expect(p.getByText('999 will not connect')).toBeVisible(); } },
  { name: 'quick-card', go: async (p) => { await p.goto('/medical/card/cpr-adult'); await expect(p.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible(); } },
  // The card's own step 1 says "call 999", so the card with the phones down is a state of its own.
  { name: 'quick-card-phones-off', go: async (p, s) => { off(s, 'mobile', 'landline'); await p.goto('/medical/card/cpr-adult'); await expect(p.locator('.emergency-999')).toContainText('999 will not connect'); } },
  { name: 'childrens-doses', go: async (p) => { await p.goto('/medical/dose'); await p.getByLabel('Years').fill('4'); await expect(p.getByRole('region', { name: 'Dose' })).toBeVisible(); } },
  { name: 'map', go: async (p) => { await p.goto('/map'); await expect(p.getByRole('toolbar', { name: 'Map tools' })).toBeVisible(); await p.waitForTimeout(1200); } },
  { name: 'map-layers', go: async (p) => { await p.goto('/map'); await expect(p.getByRole('group', { name: 'Map layers' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'map-nearby', go: async (p, s) => { s.home = { lat: 50.9379, lon: -1.4708, label: 'Home', flood_zone: '3' }; await p.goto('/map?lat=50.9379&lon=-1.4708&z=14'); await p.getByRole('button', { name: 'Nearby' }).click(); await expect(p.getByRole('list', { name: 'Nearby facilities' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'map-home', go: async (p) => { await p.goto('/map'); await p.getByRole('button', { name: 'Home' }).click(); await expect(p.getByRole('dialog', { name: 'Home' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'map-share', go: async (p) => { await p.goto('/map'); await p.getByRole('button', { name: 'Share' }).click(); await expect(p.getByRole('dialog', { name: 'Share' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'find-empty', go: async (p) => { await p.goto('/search'); await expect(p.getByRole('heading', { level: 1, name: 'Find' })).toBeVisible(); } },
  { name: 'find-results', go: async (p) => { await p.goto('/search?q=water'); await expect(p.getByRole('region', { name: 'Results' })).toBeVisible(); } },
  { name: 'library', go: async (p) => { await p.goto('/library'); await expect(p.getByRole('heading', { level: 1, name: 'Library' })).toBeVisible(); } },
  { name: 'reader', go: async (p) => { await p.goto(`/read/${WIKI}/A/Water`); await expect(p.getByTitle('Article')).toBeVisible(); await p.waitForTimeout(600); } },
  { name: 'document-missing', go: async (p) => { await p.goto('/doc/nrr-2025'); await expect(p.getByRole('heading', { level: 1 })).toBeVisible(); } },
  { name: 'assistant-off', go: async (p) => { await p.goto('/ai'); await expect(p.getByText('The assistant is off')).toBeVisible(); } },
  { name: 'notes', go: async (p) => { await p.goto('/notes'); await expect(p.getByRole('list', { name: 'Notes and pins' })).toBeVisible(); } },
  { name: 'kit', go: async (p) => { await p.goto('/kit'); await expect(p.getByRole('group', { name: 'How many people' })).toBeVisible(); } },
  { name: 'field-craft', go: async (p) => { await p.goto('/fieldcraft'); await expect(p.getByRole('navigation', { name: 'Field craft pages' }).getByRole('link')).toHaveCount(10); } },
  { name: 'field-craft-page', go: async (p) => { await p.goto('/p/shelter-and-warmth'); await expect(p.getByRole('heading', { level: 1, name: 'Shelter and warmth' })).toBeVisible(); } },
  { name: 'phone-and-radio', go: async (p) => { await p.goto('/radio'); await expect(p.getByRole('navigation', { name: 'Comms pages' })).toBeVisible(); } },
  { name: 'tools', go: async (p) => { await p.goto('/tools'); await expect(p.getByRole('navigation', { name: 'Tools' })).toBeVisible(); } },
  { name: 'timers', go: async (p) => { await p.goto('/tools/timers'); await p.getByRole('button', { name: 'Next dose in 4 hours' }).click(); await expect(p.getByRole('list', { name: 'Running timers' })).toContainText('Next dose'); } },
  { name: 'sun-and-moon', go: async (p) => { await p.goto('/tools/sun'); await expect(p.getByRole('region', { name: 'Sun' })).toBeVisible(); } },
  { name: 'calculators', go: async (p) => { await p.goto('/tools/calc'); await expect(p.getByRole('region', { name: 'Generator runtime' })).toBeVisible(); } },
  { name: 'event-log', go: async (p) => { await p.goto('/tools/log'); await expect(p.getByRole('list', { name: 'Event log' })).toBeVisible(); } },
  { name: 'system', go: async (p) => { await p.goto('/system'); await expect(p.getByRole('heading', { level: 1, name: 'System' })).toBeVisible(); } },
  { name: 'not-found', go: async (p) => { await p.goto('/nowhere'); await expect(p.getByRole('heading', { level: 1, name: 'Not found' })).toBeVisible(); } },
  // How a phone joins the box is on System now: the front door is the question and its tiles, and
  // the box no longer talks about itself there. The QR panel's own shot went with the panel.
  { name: 'keyboard', go: async (p) => { await p.goto('/search?kiosk=1'); await expect(p.getByTestId('keyboard')).toBeVisible(); await p.getByRole('combobox', { name: 'Search' }).first().fill('wat'); } },
  // The toast. It used to be photographed by clicking a link that did not exist, so every `notice`
  // shot was pixel-identical to `reader` and the toast had never been reviewed.
  { name: 'notice', go: async (p) => { await p.goto(`/read/${WIKI}/A/Water`); await p.getByTitle('Article').contentFrame().getByRole('link', { name: 'the live article' }).click(); await expect(p.getByText('Not in the library (needs the internet)')).toBeVisible(); } },
];

/* The dim mode, which nothing in round 1 photographed at all: the engine raises it when the power is
   off and it is dark, and it is the state the box was built for. */
const DIM: Shot[] = [
  { name: 'now-power-off-dim', dim: true, go: async (p, s) => { off(s, 'power'); await p.goto('/'); await expect(p.getByRole('link', { name: 'What to do now' })).toBeVisible(); } },
  { name: 'board-dim', dim: true, go: async (p, s) => { off(s, 'power', 'water'); s.situation = { slug: 'grid-collapse', title: 'National grid collapse', started_at: hour(), elapsed_s: 3600, phase: 'right-now' }; await p.goto('/board'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
  { name: 'quick-card-dim', dim: true, go: async (p) => { await p.goto('/medical/card/cpr-adult'); await expect(p.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible(); } },
  { name: 'keyboard-dim', dim: true, go: async (p) => { await p.goto('/search?kiosk=1'); await expect(p.getByTestId('keyboard')).toBeVisible(); await p.getByRole('combobox', { name: 'Search' }).first().fill('wat'); } },
  { name: 'notice-dim', dim: true, go: async (p) => { await p.goto(`/read/${WIKI}/A/Water`); await p.getByTitle('Article').contentFrame().getByRole('link', { name: 'the live article' }).click(); await expect(p.getByText('Not in the library (needs the internet)')).toBeVisible(); } },
];
SHOTS.push(...DIM);

/* Print is a state in the brief's own inventory and was in none of the 336 shots of round 2 — which
 * is how four palettes came to print black paper. These are the three things a household actually
 * prints, photographed in the print medium with dim on, the state it prints from in a power cut. */
const PRINT: Shot[] = [
  { name: 'print-quick-card', print: true, dim: true, go: async (p) => { await p.goto('/medical/card/cpr-adult'); await expect(p.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible(); } },
  { name: 'print-scenario', print: true, dim: true, go: async (p) => { await p.goto('/s/grid-collapse'); await expect(p.getByRole('heading', { name: 'Do this first' })).toBeVisible(); } },
  { name: 'print-situation-sheet', print: true, dim: true, go: async (p) => { await p.goto('/situation'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
];
SHOTS.push(...PRINT);

for (const size of SIZES) {
  for (const theme of THEMES) {
    test.describe(`${size.width} ${theme}`, () => {
      test.use({ viewport: { width: size.width, height: size.height } });
      for (const shot of SHOTS) {
        if (ONLY.length > 0 && !ONLY.some((only) => shot.name.includes(only))) continue;
        test(`${shot.name} ${size.width} ${theme}`, async ({ page, state }) => {
          await page.addInitScript(([t, k]) => {
            localStorage.setItem('sos.theme', t as string);
            if (k) sessionStorage.setItem('sos.kiosk', '1');
          }, [theme, size.kiosk] as const);
          await shot.go(page, state);
          if (shot.dim) await page.evaluate(() => { document.documentElement.dataset.dim = 'on'; });
          if (shot.print) await page.emulateMedia({ media: 'print' });
          await settle(page);
          const path = `${OUT}/${shot.name}-${size.width}-${theme}.png`;
          mkdirSync(dirname(path), { recursive: true });
          // A printed page is as long as it is: the whole sheet is photographed, not the window.
          await page.screenshot({ path, fullPage: shot.print === true });
        });
      }
    });
  }
}
