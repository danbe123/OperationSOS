import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { expect, type Page } from '@playwright/test';
import { test } from './test';
import type { FixtureState } from './fixtures/state';
import { WIKI } from '../tests/fixtures/api';

/* Every entry in the redesign brief's coverage inventory, captured at 853x480 (the kiosk) and 390
 * wide (a phone) in vault, field and blackout. Run it with `node scripts/screenshots.mjs <round>`;
 * it is skipped by the ordinary browser suite unless SOS_SHOTS is set. */

const OUT = process.env.SOS_SHOTS_DIR ?? resolve('..', 'docs/superpowers/critique/round-0');
const THEMES = (process.env.SOS_SHOTS_THEMES ?? 'vault,field,blackout').split(',');
/** A comma-separated list of substrings: `node scripts/screenshots.mjs round-0 map,keyboard`. */
const ONLY = (process.env.SOS_SHOTS_ONLY ?? '').split(',').map((x) => x.trim()).filter(Boolean);
const SIZES = [
  { width: 853, height: 480, kiosk: true },
  { width: 390, height: 844, kiosk: false },
];

type Shot = { name: string; go: (page: Page, state: FixtureState) => Promise<void> };

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
  { name: 'now-peacetime', go: async (p) => { await p.goto('/'); await expect(p.getByRole('region', { name: 'Situation', exact: true })).toBeVisible(); } },
  { name: 'now-power-off', go: async (p, s) => { off(s, 'power'); await p.goto('/'); await expect(p.getByRole('region', { name: 'Right now' })).toBeVisible(); } },
  { name: 'now-phones-down', go: async (p, s) => { off(s, 'mobile', 'landline'); await p.goto('/'); await expect(p.getByTestId('status-strip')).toBeVisible(); } },
  { name: 'now-drill', go: async (p, s) => { off(s, 'power'); s.drill = true; s.situation = { slug: 'grid-collapse', title: 'National grid collapse', started_at: hour(), elapsed_s: 3600, phase: 'right-now' }; await p.goto('/'); await expect(p.getByRole('group', { name: 'Situation now' })).toBeVisible(); } },
  { name: 'now-engine-down', go: async (p) => { await p.route('**/api/situation/view', (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"the engine is not answering"}' })); await p.goto('/'); await expect(p.getByText(/The box cannot read the situation/)).toBeVisible(); } },
  { name: 'now-empty-household', go: async (p) => { await p.goto('/'); await expect(p.getByRole('region', { name: 'Household and stock' })).toBeVisible(); } },
  { name: 'situation-sheet', go: async (p, s) => { off(s, 'power', 'water'); await p.goto('/situation'); await expect(p.getByRole('heading', { level: 1, name: 'Situation' })).toBeVisible(); } },
  { name: 'situation-carry', go: async (p) => { await p.goto('/situation'); await p.getByRole('button', { name: 'Export as codes' }).click(); await expect(p.getByRole('group', { name: 'Situation codes' })).toBeVisible(); await p.getByRole('group', { name: 'Situation codes' }).scrollIntoViewIfNeeded(); } },
  { name: 'situation-drill', go: async (p) => { await p.goto('/situation#drill'); await p.getByLabel('Drill scenario').selectOption('grid-collapse'); await p.getByRole('region', { name: 'Drill' }).scrollIntoViewIfNeeded(); } },
  { name: 'tasks', go: async (p, s) => { off(s, 'power'); await p.goto('/tasks'); await expect(p.getByRole('heading', { level: 1, name: 'Things to do' })).toBeVisible(); } },
  { name: 'tasks-empty', go: async (p) => { await p.goto('/tasks'); await expect(p.getByText('Nothing to do.')).toBeVisible(); } },
  { name: 'board', go: async (p, s) => { off(s, 'power', 'water'); s.situation = { slug: 'grid-collapse', title: 'National grid collapse', started_at: hour(), elapsed_s: 3600, phase: 'right-now' }; await p.goto('/board'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
  { name: 'board-peacetime', go: async (p) => { await p.goto('/board'); await expect(p.getByRole('region', { name: 'What is working' })).toBeVisible(); } },
  { name: 'guides', go: async (p) => { await p.goto('/guides'); await expect(p.getByRole('navigation', { name: 'Scenarios' })).toBeVisible(); } },
  { name: 'guides-filtered', go: async (p) => { await p.goto('/guides'); await p.getByRole('searchbox', { name: 'Filter these guides' }).fill('water'); await expect(p.getByRole('status')).toBeVisible(); } },
  { name: 'scenario-right-now', go: async (p) => { await p.goto('/s/grid-collapse'); await expect(p.getByRole('heading', { name: 'Do this first' })).toBeVisible(); } },
  { name: 'scenario-later', go: async (p) => { await p.goto('/s/grid-collapse?tab=first-72-hours'); await expect(p.getByRole('heading', { name: 'First 72 hours' })).toBeVisible(); } },
  { name: 'module', go: async (p) => { await p.goto('/m/water'); await expect(p.getByRole('heading', { level: 1, name: 'Water' })).toBeVisible(); } },
  { name: 'page', go: async (p) => { await p.goto('/p/pmr446'); await expect(p.getByRole('heading', { level: 1, name: 'PMR446 radio' })).toBeVisible(); } },
  { name: 'medical', go: async (p) => { await p.goto('/medical'); await expect(p.getByRole('navigation', { name: 'Quick cards' })).toBeVisible(); } },
  { name: 'medical-phones-down', go: async (p, s) => { off(s, 'mobile', 'landline'); await p.goto('/medical'); await expect(p.getByText('999 will not connect')).toBeVisible(); } },
  { name: 'quick-card', go: async (p) => { await p.goto('/medical/card/cpr-adult'); await expect(p.getByRole('heading', { level: 1, name: 'CPR (adult)' })).toBeVisible(); } },
  { name: 'childrens-doses', go: async (p) => { await p.goto('/medical/dose'); await p.getByLabel('Years').fill('4'); await expect(p.getByRole('region', { name: 'Dose' })).toBeVisible(); } },
  { name: 'map', go: async (p) => { await p.goto('/map'); await expect(p.getByRole('toolbar', { name: 'Map tools' })).toBeVisible(); await p.waitForTimeout(1200); } },
  { name: 'map-layers', go: async (p) => { await p.goto('/map'); await p.getByRole('button', { name: 'Layers' }).click(); await expect(p.getByRole('dialog', { name: 'Layers' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'map-nearby', go: async (p, s) => { s.home = { lat: 50.9379, lon: -1.4708, label: 'Home', flood_zone: '3' }; await p.goto('/map?lat=50.9379&lon=-1.4708&z=14'); await p.getByRole('button', { name: 'Nearby' }).click(); await expect(p.getByRole('list', { name: 'Nearby facilities' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'map-home', go: async (p) => { await p.goto('/map'); await p.getByRole('button', { name: 'Home' }).click(); await expect(p.getByRole('dialog', { name: 'Home' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'map-share', go: async (p) => { await p.goto('/map'); await p.getByRole('button', { name: 'Share' }).click(); await expect(p.getByRole('dialog', { name: 'Share' })).toBeVisible(); await p.waitForTimeout(800); } },
  { name: 'find-empty', go: async (p) => { await p.goto('/search'); await expect(p.getByRole('heading', { level: 1, name: 'Find' })).toBeVisible(); } },
  { name: 'find-results', go: async (p) => { await p.goto('/search?q=water'); await expect(p.getByRole('list', { name: 'Results' })).toBeVisible(); } },
  { name: 'library', go: async (p) => { await p.goto('/library'); await expect(p.getByRole('heading', { level: 1, name: 'Library' })).toBeVisible(); } },
  { name: 'reader', go: async (p) => { await p.goto(`/read/${WIKI}/A/Water`); await expect(p.getByTitle('Article')).toBeVisible(); await p.waitForTimeout(600); } },
  { name: 'document-missing', go: async (p) => { await p.goto('/doc/nrr-2025'); await expect(p.getByRole('heading', { level: 1 })).toBeVisible(); } },
  { name: 'assistant-off', go: async (p) => { await p.goto('/ai'); await expect(p.getByText('The assistant is off')).toBeVisible(); } },
  { name: 'household', go: async (p, s) => { s.household = [{ id: 1, name: 'Sam', age: 41, needs: 'asthma', medications: 'salbutamol inhaler', contacts: 'GP 023 8000 0000', updated_at: hour() }]; await p.goto('/plan'); await expect(p.getByRole('region', { name: 'Household', exact: true })).toBeVisible(); } },
  { name: 'neighbours', go: async (p, s) => { s.neighbours = [{ id: 5, name: 'Joan Reeve', address: '14 Mill Lane', needs: 'oxygen concentrator, cannot manage stairs', skills: '', contacts: '07700 900123', notes: 'key is with number 12', updated_at: hour() }, { id: 6, name: 'Ade Okafor', address: '18 Mill Lane', needs: '', skills: 'nurse, has a petrol generator', contacts: '07700 900456', notes: '', updated_at: hour() }]; await p.goto('/plan'); await p.getByRole('region', { name: 'Neighbours' }).scrollIntoViewIfNeeded(); await expect(p.getByRole('list', { name: 'Neighbours' })).toBeVisible(); } },
  { name: 'stock', go: async (p, s) => { s.stock = [{ id: 1, name: 'Bottled water', category: 'water', quantity: 13.5, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: hour(), days_left: 1.5 }]; await p.goto('/plan#stock'); await p.getByRole('region', { name: 'Stock' }).scrollIntoViewIfNeeded(); } },
  { name: 'field-craft', go: async (p) => { await p.goto('/fieldcraft'); await expect(p.getByRole('heading', { level: 1, name: 'Field craft' })).toBeVisible(); } },
  { name: 'phone-and-radio', go: async (p) => { await p.goto('/radio'); await expect(p.getByRole('navigation', { name: 'Comms pages' })).toBeVisible(); } },
  { name: 'tools', go: async (p) => { await p.goto('/tools'); await expect(p.getByRole('navigation', { name: 'Tools' })).toBeVisible(); } },
  { name: 'timers', go: async (p) => { await p.goto('/tools/timers'); await p.getByRole('button', { name: 'Next dose in 4 hours' }).click(); await expect(p.getByRole('list', { name: 'Running timers' })).toContainText('Next dose'); } },
  { name: 'sun-and-moon', go: async (p) => { await p.goto('/tools/sun'); await expect(p.getByRole('region', { name: 'Sun' })).toBeVisible(); } },
  { name: 'calculators', go: async (p) => { await p.goto('/tools/calc'); await expect(p.getByRole('region', { name: 'Generator runtime' })).toBeVisible(); } },
  { name: 'event-log', go: async (p) => { await p.goto('/tools/log'); await expect(p.getByRole('list', { name: 'Event log' })).toBeVisible(); } },
  { name: 'system', go: async (p) => { await p.goto('/system'); await expect(p.getByRole('heading', { level: 1, name: 'System' })).toBeVisible(); } },
  { name: 'not-found', go: async (p) => { await p.goto('/nowhere'); await expect(p.getByRole('heading', { level: 1, name: 'Not found' })).toBeVisible(); } },
  { name: 'connect-a-phone', go: async (p) => { await p.goto('/'); await p.getByRole('button', { name: 'Connect a phone' }).click(); await expect(p.getByRole('dialog', { name: 'Connect a phone' })).toBeVisible(); await p.waitForTimeout(400); } },
  { name: 'keyboard', go: async (p) => { await p.goto('/search?kiosk=1'); await expect(p.getByTestId('keyboard')).toBeVisible(); await p.getByRole('combobox', { name: 'Search' }).first().fill('wat'); } },
  { name: 'notice', go: async (p) => { await p.goto(`/read/${WIKI}/A/Water`); await p.waitForTimeout(500); await p.getByTitle('Article').contentFrame().getByRole('link').filter({ hasText: /http/ }).first().click({ timeout: 3000 }).catch(() => undefined); await p.waitForTimeout(400); } },
];

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
          await settle(page);
          const path = `${OUT}/${shot.name}-${size.width}-${theme}.png`;
          mkdirSync(dirname(path), { recursive: true });
          await page.screenshot({ path });
        });
      }
    });
  }
}
