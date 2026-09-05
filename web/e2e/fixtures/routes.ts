import { readFileSync } from 'node:fs';
import type { BrowserContext, Route } from '@playwright/test';
import type { AiEvent, ChecklistItem, Note, Person, StockItem } from '../../src/api/types';
import { phaseFor } from '../../src/tools/situation';
import { aiEvents, cards, householdPlan, library, mapConfig, page as pmrPage, pages, places, playbook, playbooks, search, sseBody, suggestions } from '../../tests/fixtures/api';
import { KIWIX_PAGES } from './kiwix';
import { PIN, TOKEN, type FixtureState } from './state';

const here = (rel: string) => new URL(rel, import.meta.url);
const styleJson = JSON.parse(readFileSync(here('./maps/style.json'), 'utf8')) as { name: string; layers: { id: string; paint: Record<string, string> }[] };
const pmtiles = readFileSync(here('./maps/test.pmtiles'));
const healthGeojson = readFileSync(here('./maps/health.geojson'), 'utf8');

const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
const detail = (route: Route, status: number, message: string) => json(route, { detail: message }, status);

/** The map config the fixtures can actually serve: two bases on the same fixture tiles, one geojson overlay, no terrain, one unavailable overlay. */
export function fixtureMapConfig() {
  return {
    ...mapConfig,
    terrain: { contours: null, hillshade: null },
    overlays: mapConfig.overlays.map((o) => (o.id === 'health' ? o : { ...o, available: false, default_on: false })),
  };
}

function servePmtiles(route: Route) {
  const range = route.request().headers()['range'];
  if (!range) return route.fulfill({ status: 200, headers: { 'Content-Type': 'application/octet-stream', 'Accept-Ranges': 'bytes', 'Content-Length': String(pmtiles.length) }, body: pmtiles });
  const m = /bytes=(\d+)-(\d*)/.exec(range);
  const start = m ? Number(m[1]) : 0;
  const end = m && m[2] ? Math.min(Number(m[2]), pmtiles.length - 1) : pmtiles.length - 1;
  return route.fulfill({
    status: 206,
    headers: { 'Content-Type': 'application/octet-stream', 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${pmtiles.length}`, 'Content-Length': String(end - start + 1) },
    body: pmtiles.subarray(start, end + 1),
  });
}

export async function installFixtureRoutes(context: BrowserContext, state: FixtureState): Promise<void> {
  await context.route('**/maps/**', async (route) => {
    const url = new URL(route.request().url());
    const style = /^\/maps\/styles\/([\w-]+)\.json$/.exec(url.pathname);
    if (style) {
      const name = style[1];
      const dark = !name.endsWith('-field');
      // The road colour also varies by base (not just theme) so a base switch is a genuine,
      // diffable paint-property change - real base switches change far more than this, but the
      // map spec's "keeps [state] across a base switch" test needs at least one diffable
      // difference to observe a real style reload (see MapView's styleVersion / style.load).
      const roadColor = name.startsWith('os-') ? '#0057b8' : '#ffb000';
      const body = {
        ...styleJson,
        name,
        layers: styleJson.layers.map((l) => {
          if (l.id === 'background') return { ...l, paint: { 'background-color': dark ? '#0a0f0a' : '#f4efe4' } };
          if (l.id === 'road') return { ...l, paint: { ...l.paint, 'line-color': roadColor } };
          return l;
        }),
      };
      return json(route, body);
    }
    if (url.pathname.endsWith('.pmtiles')) return servePmtiles(route);
    if (url.pathname === '/maps/overlays/health.geojson') return route.fulfill({ status: 200, contentType: 'application/geo+json', body: healthGeojson });
    if (url.pathname === '/maps/packs/index.html') return route.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Phone map packs</h1>' });
    return route.fulfill({ status: 404, body: 'not found' });
  });

  await context.route('**/kiwix/**', async (route) => {
    const url = new URL(route.request().url());
    const html = KIWIX_PAGES[url.pathname];
    if (html) return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    if (url.pathname === '/kiwix/search') return route.fulfill({ status: 200, contentType: 'text/html', body: `<h1>Results for ${url.searchParams.get('pattern') ?? ''}</h1>` });
    return route.fulfill({ status: 404, contentType: 'text/html', body: '<h1>Not found</h1>' });
  });

  await context.route('**/docs/**', (route) => route.fulfill({ status: 404, body: 'no fixture document' }));

  await context.route('**/api/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const p = url.pathname.replace(/^\/api/, '');
    const method = req.method();
    const body = (): Record<string, unknown> => (req.postData() ? (JSON.parse(req.postData() as string) as Record<string, unknown>) : {});
    const gated = () => state.status.pin_required && req.headers()['authorization'] !== `Bearer ${TOKEN}`;

    if (method === 'GET' && p === '/status') return json(route, { ...state.status, eth_mode: state.ethMode });
    if (method === 'GET' && p === '/library') return json(route, library);
    if (method === 'GET' && p.startsWith('/library/')) {
      const item = library.categories.flatMap((c) => c.items).find((i) => i.id === decodeURIComponent(p.slice('/library/'.length)));
      return item ? json(route, item) : detail(route, 404, 'no such item');
    }
    if (method === 'GET' && p === '/search') return json(route, { ...search, q: url.searchParams.get('q') ?? '', query: url.searchParams.get('q') ?? '' });
    if (method === 'GET' && p === '/suggest') {
      const q = (url.searchParams.get('q') ?? '').toLowerCase();
      return json(route, suggestions.filter((s) => s.value.toLowerCase().startsWith(q)));
    }
    if (method === 'GET' && p === '/playbooks') return json(route, playbooks);
    const pb = /^\/playbooks\/([\w-]+)(?:\/checklist(?:\/([\w-]+))?)?$/.exec(p);
    if (pb) {
      const slug = pb[1];
      const summary = playbooks.find((x) => x.slug === slug);
      if (!summary) return detail(route, 404, 'no such playbook');
      if (!state.checklists.has(slug)) state.checklists.set(slug, playbook.checklist.map((i) => ({ ...i })));
      const list = state.checklists.get(slug) as ChecklistItem[];
      if (method === 'GET') return json(route, { ...playbook, ...summary, checklist: list });
      if (method === 'PUT' && pb[2]) {
        const item = list.find((i) => i.id === pb[2]);
        if (!item) return detail(route, 404, 'no such item');
        item.checked = Boolean(body().checked);
        item.updated_at = new Date().toISOString();
        return json(route, list);
      }
      if (method === 'DELETE') {
        for (const i of list) { i.checked = false; i.updated_at = null; }
        return json(route, list);
      }
    }
    if (method === 'GET' && p.startsWith('/modules/')) {
      const mod = playbook.modules.find((m) => m.slug === p.slice('/modules/'.length));
      return mod ? json(route, mod) : detail(route, 404, 'no such module');
    }
    if (method === 'GET' && p === '/cards') return json(route, cards);
    if (method === 'GET' && p.startsWith('/cards/')) {
      const card = cards.find((c) => c.slug === p.slice('/cards/'.length));
      return card ? json(route, card) : detail(route, 404, 'no such card');
    }
    if (method === 'GET' && p === '/pages') return json(route, pages);
    if (method === 'GET' && p.startsWith('/pages/')) {
      const slug = p.slice('/pages/'.length);
      if (slug === 'household-plan') return json(route, householdPlan);
      const meta = pages.find((x) => x.slug === slug);
      return meta ? json(route, { ...pmrPage, ...meta, html: pmrPage.html }) : detail(route, 404, 'no such page');
    }
    if (method === 'GET' && p === '/map/config') return json(route, fixtureMapConfig());
    if (method === 'GET' && p === '/map/overlays') return json(route, fixtureMapConfig().overlays);
    if (method === 'GET' && p === '/places') {
      const q = (url.searchParams.get('q') ?? '').toLowerCase();
      return json(route, places.filter((pl) => pl.name.toLowerCase().startsWith(q)));
    }
    if (p === '/notes' && method === 'GET') {
      const kind = url.searchParams.get('kind');
      const list = state.notes.filter((n) => !kind || n.kind === kind);
      return json(route, kind === 'event' ? [...list].reverse() : list);
    }
    if (p === '/household' && method === 'GET') return json(route, state.household);
    if (p === '/household' && method === 'POST') {
      const b = body();
      const person: Person = { id: state.nextId++, name: String(b.name ?? ''), age: (b.age as number | null) ?? null, needs: String(b.needs ?? ''), medications: String(b.medications ?? ''), contacts: String(b.contacts ?? ''), updated_at: new Date().toISOString() };
      state.household.push(person);
      return json(route, person);
    }
    const person = /^\/household\/(\d+)$/.exec(p);
    if (person) {
      const idx = state.household.findIndex((x) => x.id === Number(person[1]));
      if (idx === -1) return detail(route, 404, 'Person not found');
      if (method === 'PUT') { state.household[idx] = { ...state.household[idx], ...body() } as Person; return json(route, state.household[idx]); }
      if (method === 'DELETE') { state.household.splice(idx, 1); return json(route, { ok: true }); }
    }
    const withDays = (i: StockItem): StockItem => ({ ...i, days_left: i.per_person_day ? Math.round((i.quantity / (i.per_person_day * Math.max(1, state.household.length))) * 10) / 10 : null });
    if (p === '/stock' && method === 'GET') return json(route, { people: Math.max(1, state.household.length), items: state.stock.map(withDays) });
    if (p === '/stock' && method === 'POST') {
      const b = body();
      const item: StockItem = { id: state.nextId++, name: String(b.name ?? ''), category: (b.category as StockItem['category']) ?? 'other', quantity: Number(b.quantity ?? 0), unit: String(b.unit ?? ''), per_person_day: (b.per_person_day as number | null) ?? (b.category === 'water' ? 3 : null), expires: (b.expires as string | null) ?? null, notes: String(b.notes ?? ''), updated_at: new Date().toISOString(), days_left: null };
      state.stock.push(item);
      return json(route, withDays(item));
    }
    const stockItem = /^\/stock\/(\d+)$/.exec(p);
    if (stockItem) {
      const idx = state.stock.findIndex((x) => x.id === Number(stockItem[1]));
      if (idx === -1) return detail(route, 404, 'Stock item not found');
      if (method === 'PUT') { state.stock[idx] = { ...state.stock[idx], ...body() } as StockItem; return json(route, withDays(state.stock[idx])); }
      if (method === 'DELETE') { state.stock.splice(idx, 1); return json(route, { ok: true }); }
    }
    if (p === '/situation' && method === 'GET') return json(route, state.situation);
    if (p === '/situation' && method === 'POST') {
      const slug = String(body().slug ?? '');
      const summary = playbooks.find((x) => x.slug === slug);
      if (!summary) return detail(route, 404, 'Playbook not found');
      const started_at = new Date().toISOString();
      state.situation = { slug, title: summary.title, started_at, elapsed_s: 0, phase: phaseFor(0).id };
      state.status = { ...state.status, situation: { slug, started_at } };
      return json(route, state.situation);
    }
    if (p === '/situation' && method === 'DELETE') {
      state.situation = { slug: null };
      state.status = { ...state.status, situation: null };
      return json(route, state.situation);
    }
    if (p === '/notes' && method === 'POST') {
      const b = body();
      const note: Note = { id: state.nextNoteId++, kind: (b.kind as Note['kind']) ?? 'note', title: String(b.title ?? ''), body: String(b.body ?? ''), lat: (b.lat as number | null) ?? null, lon: (b.lon as number | null) ?? null, updated_at: new Date().toISOString() };
      state.notes.push(note);
      return json(route, note);
    }
    const note = /^\/notes\/(\d+)$/.exec(p);
    if (note) {
      const idx = state.notes.findIndex((n) => n.id === Number(note[1]));
      if (idx === -1) return detail(route, 404, 'no such note');
      if (method === 'PUT') { state.notes[idx] = { ...state.notes[idx], ...body(), updated_at: new Date().toISOString() } as Note; return json(route, state.notes[idx]); }
      if (method === 'DELETE') { state.notes.splice(idx, 1); return json(route, { ok: true }); }
    }
    if (method === 'POST' && p === '/ai/ask') return route.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(aiEvents as AiEvent[]) });
    if (method === 'GET' && p === '/ai/status') return json(route, state.status.ai);
    if (method === 'POST' && (p === '/ai/enable' || p === '/ai/disable')) {
      if (gated()) return detail(route, 401, 'PIN required');
      state.status = { ...state.status, ai: { ...state.status.ai, state: p === '/ai/enable' ? 'starting' : 'off' } };
      return json(route, { state: state.status.ai.state });
    }
    if (method === 'POST' && p === '/kiosk/backlight') return json(route, { level: body().level });
    if (method === 'POST' && p === '/kiosk/idle') return json(route, { ok: true });
    if (method === 'POST' && p === '/system/backlight') return json(route, { level: body().level });
    if (method === 'POST' && p === '/system/pin') {
      if (body().pin === PIN) return json(route, { token: TOKEN, expires_in: 600 });
      return detail(route, 401, 'wrong PIN');
    }
    if (method === 'POST' && ['/system/power-mode', '/system/eth-mode', '/system/hotspot', '/system/update', '/system/pin/change'].includes(p)) {
      if (gated()) return detail(route, 401, 'PIN required');
      if (p === '/system/eth-mode') state.ethMode = body().mode as 'client' | 'direct';
      if (p === '/system/power-mode') state.status = { ...state.status, power_mode: body().mode as 'normal' | 'low' };
      if (p === '/system/hotspot') state.status = { ...state.status, hotspot: { ...state.status.hotspot, ssid: String(body().ssid) } };
      if (p === '/system/update') return json(route, { started: true });
      if (p === '/system/pin/change') return json(route, { ok: true });
      return json(route, { ...state.status, eth_mode: state.ethMode });
    }
    if (method === 'POST' && p === '/system/settings') {
      state.status = { ...state.status, ...body() } as typeof state.status;
      return json(route, { ...state.status, eth_mode: state.ethMode });
    }
    if (method === 'GET' && p === '/system/update/progress') return json(route, { running: false, lines: ['Nothing to do'], done: true, ok: true });
    if (method === 'POST' && p === '/system/rescan') return json(route, { items: 7, available: 6 });
    return detail(route, 404, `no fixture for ${method} ${p}`);
  });
}
