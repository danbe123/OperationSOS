import { readFileSync } from 'node:fs';
import type { BrowserContext, Route } from '@playwright/test';
import type { AiEvent, ChecklistItem, ConditionId, ConditionState, NearbyFacility, Neighbour, Note, Person, StockItem } from '../../src/api/types';
import { CONDITION_IDS } from '../../src/api/types';
import { phaseFor } from '../../src/tools/situation';
import { aiEvents, cards, cardsNoPhones, fieldcraftPage, householdPlan, library, mapConfig, page as pmrPage, pages, places, playbook, playbooks, search, sseBody, suggestions } from '../../tests/fixtures/api';
import { bearingDeg, distanceKm, naismithMinutes } from '../../src/map/measure';
import { computeView, freshConditions, report } from './engine';
import { KIWIX_PAGES } from './kiwix';
import { PIN, TOKEN, type FixturePlace, type FixtureState } from './state';

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

/** A quarter-second of silence: enough for the player to load, play and fire `ended`. */
function silentWav(): Buffer {
  const rate = 8000;
  const samples = rate / 4;
  const buf = Buffer.alloc(44 + samples * 2);
  buf.write('RIFF', 0);
  buf.writeUInt32LE(36 + samples * 2, 4);
  buf.write('WAVEfmt ', 8);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24);
  buf.writeUInt32LE(rate * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write('data', 36);
  buf.writeUInt32LE(samples * 2, 40);
  return buf;
}

const FACILITY_TITLES: Record<string, string> = {
  'emergency-department': 'Emergency department', pharmacy: 'Pharmacy', gp: 'GP surgery', fuel: 'Fuel station',
  'water-works': 'Water treatment works', 'fire-station': 'Fire station', 'rest-centre': 'Rest centre',
};
const COMPASS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];

/** What `GET /nearby?lat&lon` answers: one block per facility, nearest first, with the ones the box
 * has no searchable data for saying plainly why. Matches sos.nearby.nearest(). */
export function nearbyFrom(places: FixturePlace[], missing: string[], lat: number, lon: number): NearbyFacility[] {
  const ids = [...new Set([...places.map((p) => p.facility), ...missing])];
  return ids.map((id) => {
    const found = places
      .filter((pl) => pl.facility === id)
      .map((pl) => {
        const km = distanceKm({ lat, lon }, { lat: pl.lat, lon: pl.lon });
        const bearing = bearingDeg({ lat, lon }, { lat: pl.lat, lon: pl.lon });
        return {
          name: pl.name, lat: pl.lat, lon: pl.lon,
          distance_m: Math.round(km * 1000),
          bearing_deg: Math.round(bearing),
          compass: COMPASS[Math.round((bearing % 360) / 22.5) % 16],
          walk_minutes: naismithMinutes(km),
          source: 'overlay:health',
          properties: {},
        };
      })
      .sort((a, b) => a.distance_m - b.distance_m);
    const facility: NearbyFacility = {
      id, title: FACILITY_TITLES[id] ?? id, found: found.length > 0,
      nearest: found[0] ?? null, also: found.slice(1, 3), searched: found.length ? ['health'] : [], note: null,
    };
    if (!found.length) facility.why = `No searchable copy of the ${id} data on this box.`;
    return facility;
  });
}

/** What `GET /api/situation/export` answers: one document, checksummed, that another box can take in. */
function exportDocument(state: FixtureState) {
  const view = computeView(state);
  return {
    kind: 'sos-situation-export', version: 1, exported_at: new Date().toISOString(), checksum: 'fixture',
    data: { conditions: view.conditions, household: state.household, neighbours: state.neighbours, stock: state.stock, notes: state.notes },
  };
}

/** The box writes an event for every change worth remembering; the board and the drill debrief read them. */
function logEvent(state: FixtureState, title: string): void {
  state.notes.push({ id: state.nextNoteId++, kind: 'event', title, body: '', lat: null, lon: null, updated_at: new Date().toISOString() });
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

    if (method === 'GET' && p === '/status') {
      const v = computeView(state);
      return json(route, {
        ...state.status, eth_mode: state.ethMode,
        conditions: Object.fromEntries(CONDITION_IDS.map((id) => [id, v.conditions[id].state])),
        modes: v.modes, drill: v.meta.drill, readiness_score: v.readiness.score,
        situation: state.situation.slug ? { slug: state.situation.slug, started_at: state.situation.started_at } : null,
      });
    }
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
      // The engine resolves the card's own call directives against the situation, so a card asked
      // for while both networks are down is not the same card.
      const set = computeView(state).modes.calls === 'hidden' ? cardsNoPhones : cards;
      const card = set.find((c) => c.slug === p.slice('/cards/'.length));
      return card ? json(route, card) : detail(route, 404, 'no such card');
    }
    if (method === 'GET' && p === '/pages') return json(route, pages);
    if (method === 'GET' && p.startsWith('/pages/')) {
      const slug = p.slice('/pages/'.length);
      if (slug === 'household-plan') return json(route, householdPlan);
      if (slug === fieldcraftPage.slug) return json(route, fieldcraftPage);
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
    if (p === '/neighbours' && method === 'GET') return json(route, state.neighbours);
    if (p === '/neighbours' && method === 'POST') {
      const b = body();
      const n: Neighbour = { id: state.nextId++, name: String(b.name ?? ''), address: String(b.address ?? ''), needs: String(b.needs ?? ''), skills: String(b.skills ?? ''), contacts: String(b.contacts ?? ''), notes: String(b.notes ?? ''), updated_at: new Date().toISOString() };
      state.neighbours.push(n);
      return json(route, n);
    }
    const neighbour = /^\/neighbours\/(\d+)$/.exec(p);
    if (neighbour) {
      const idx = state.neighbours.findIndex((x) => x.id === Number(neighbour[1]));
      if (idx === -1) return detail(route, 404, 'Neighbour not found');
      if (method === 'PUT') { state.neighbours[idx] = { ...state.neighbours[idx], ...body(), updated_at: new Date().toISOString() } as Neighbour; return json(route, state.neighbours[idx]); }
      if (method === 'DELETE') { state.neighbours.splice(idx, 1); return json(route, { ok: true }); }
    }
    if (p === '/street-list' && method === 'GET') {
      const rows = state.neighbours.map((n) => `| ${n.name} | ${n.address} | ${n.needs} | ${n.skills} | ${n.contacts} |`).join('\n');
      return route.fulfill({ status: 200, contentType: 'text/markdown; charset=utf-8', body: `# Street list\n\n| Name | Address | Needs | Can do | Reach on |\n|---|---|---|---|---|\n${rows}\n` });
    }
    if (p === '/situation/export' && method === 'GET') {
      return json(route, exportDocument(state));
    }
    if (p === '/situation/export/qr' && method === 'GET') {
      const payload = JSON.stringify(exportDocument(state));
      const size = 700;
      const parts: string[] = [];
      for (let i = 0; i < payload.length; i += size) parts.push(payload.slice(i, i + size));
      return json(route, { chunks: parts.map((d, i) => JSON.stringify({ i, n: parts.length, d })) });
    }
    if (p === '/situation/import' && method === 'POST') {
      const raw = req.postData();
      if (!raw) return detail(route, 422, 'Nothing to bring in');
      return json(route, {
        ok: true, version: 1, exported_at: new Date().toISOString(),
        counts: {
          conditions: { updated: 2, kept: 8 },
          household: { added: 1, updated: 0, kept: state.household.length },
          neighbours: { added: state.neighbours.length, updated: 0, kept: 0 },
          events: { added: 3, skipped: 0 },
        },
        home: state.home ? 'kept' : 'set',
        scenario: state.situation.slug ? 'kept' : 'started: grid-collapse',
        changes: ['Mains power set to off', 'One person added to the household'],
      });
    }
    if (p === '/stock' && method === 'GET') return json(route, { people: Math.max(1, state.household.length), items: state.stock.map(withDays) });
    if (p === '/stock' && method === 'POST') {
      const b = body();
      const item: StockItem = { id: state.nextId++, name: String(b.name ?? ''), category: (b.category as StockItem['category']) ?? 'other', quantity: Number(b.quantity ?? 0), unit: String(b.unit ?? ''), per_person_day: (b.per_person_day as number | null) ?? (b.category === 'water' ? 3 : null), expires: (b.expires as string | null) ?? null, notes: String(b.notes ?? ''), updated_at: new Date().toISOString(), days_left: null, kit_item: null };
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
    // The situation engine (spec 2026-09-06): an in-memory View over the fixture state.
    if (method === 'GET' && p === '/situation/view') return json(route, computeView(state));
    if (method === 'GET' && p === '/situation/report') return route.fulfill({ status: 200, contentType: 'text/markdown; charset=utf-8', body: report(state) });
    if (method === 'GET' && p === '/conditions') return json(route, computeView(state).conditions);
    const cond = /^\/conditions\/([\w-]+)(?:\/(confirm|accept))?$/.exec(p);
    if (cond) {
      const id = cond[1] as ConditionId;
      const current = state.conditions[id];
      if (!current) return detail(route, 404, 'no such condition');
      const now = new Date().toISOString();
      if (method === 'PUT') {
        const b = body();
        const next = String(b.state ?? '');
        if (!['working', 'degraded', 'off'].includes(next)) return detail(route, 422, 'bad state');
        if (b.expected_updated_at && b.expected_updated_at !== current.updated_at) return json(route, current, 409);
        state.conditions = { ...state.conditions, [id]: {
          ...current, state: next as ConditionState, since: String(b.since ?? now), note: String(b.note ?? ''),
          source: 'manual', confidence: 1, set_by: 'phone', updated_at: now, confirmed_at: now,
        } };
        logEvent(state, `${current.title} ${next}${state.drill ? ' (drill)' : ' (phone)'}`);
        return json(route, computeView(state).conditions[id]);
      }
      if (method === 'POST' && cond[2] === 'confirm') {
        state.conditions = { ...state.conditions, [id]: { ...current, confirmed_at: now, updated_at: now } };
        return json(route, computeView(state).conditions[id]);
      }
      if (method === 'POST' && cond[2] === 'accept') {
        const rule = String(body().rule ?? '');
        const proposal = computeView(state).inferred.find((i) => i.rule === rule && i.condition === id);
        if (!proposal) return detail(route, 404, 'no such proposal');
        state.conditions = { ...state.conditions, [id]: { ...current, state: proposal.state, since: now, source: 'inferred', confidence: proposal.confidence, set_by: 'box', updated_at: now, confirmed_at: now } };
        return json(route, computeView(state).conditions[id]);
      }
    }
    if (method === 'GET' && p === '/tasks') return json(route, computeView(state).tasks);
    if (method === 'PUT' && p.startsWith('/tasks/')) {
      const id = decodeURIComponent(p.slice('/tasks/'.length));
      const b = body();
      const existing = computeView(state).tasks.find((t) => t.id === id);
      if (!existing) return detail(route, 404, 'no such task');
      const done = b.done === undefined ? existing.done : Boolean(b.done);
      const person = b.person === undefined ? existing.person : (String(b.person) || null);
      state.taskState.set(id, { done, person, done_at: done ? new Date().toISOString() : null });
      if (done !== existing.done) logEvent(state, `${existing.title} ${done ? 'ticked' : 'unticked'}${person ? ` by ${person}` : ''}`);
      const checklist = /^checklist:([\w-]+)\/(.+)$/.exec(id);
      if (checklist) {
        const list = state.checklists.get(checklist[1]) ?? [];
        const item = list.find((i) => i.id === checklist[2]);
        if (item) { item.checked = done; item.updated_at = new Date().toISOString(); }
      }
      return json(route, computeView(state).tasks.find((t) => t.id === id));
    }
    if (method === 'GET' && p === '/nearby') {
      const lat = Number(url.searchParams.get('lat') ?? state.home?.lat ?? 0);
      const lon = Number(url.searchParams.get('lon') ?? state.home?.lon ?? 0);
      return json(route, {
        lat, lon,
        method: "Straight-line distance and bearing; walking time by Naismith's rule (5 km/h). Roads and paths will be longer.",
        facilities: nearbyFrom(state.places, state.missingNearby, lat, lon),
      });
    }
    if (method === 'GET' && p === '/sensors') return json(route, state.sensors);
    if (method === 'GET' && p === '/recordings') return json(route, state.recordings);
    if (method === 'POST' && p === '/speak') {
      if (!state.speaks) return detail(route, 503, 'Reading aloud is not installed on this box');
      return route.fulfill({ status: 200, contentType: 'audio/wav', body: silentWav() });
    }
    if (p === '/home' && method === 'GET') return json(route, state.home);
    if (p === '/home' && method === 'PUT') {
      const b = body();
      state.home = { lat: Number(b.lat ?? 0), lon: Number(b.lon ?? 0), label: String(b.label ?? 'Home'), flood_zone: (b.flood_zone as string | null) ?? null };
      return json(route, state.home);
    }
    if (p === '/drill' && method === 'POST') {
      const b = body();
      const slug = String(b.scenario ?? '');
      const summary = playbooks.find((x) => x.slug === slug);
      if (!summary) return detail(route, 404, 'Playbook not found');
      const at = new Date(Date.now() - Number(b.hours_ago ?? 0) * 3_600_000).toISOString();
      state.savedConditions = state.conditions;
      const conditions = freshConditions(at);
      for (const [id, value] of Object.entries((b.conditions ?? {}) as Record<string, ConditionState>)) {
        if (conditions[id as ConditionId]) conditions[id as ConditionId] = { ...conditions[id as ConditionId], state: value, set_by: 'drill' };
      }
      state.conditions = conditions;
      state.situation = { slug, title: summary.title, started_at: at, elapsed_s: 0, phase: phaseFor(0).id };
      state.drill = true;
      // The engine tags everything that happens inside a drill; the debrief filters on the tag.
      logEvent(state, `Drill started: ${summary.title} (drill)`);
      return json(route, computeView(state));
    }
    if (p === '/drill' && method === 'DELETE') {
      if (state.savedConditions) state.conditions = state.savedConditions;
      state.savedConditions = null;
      state.drill = false;
      state.situation = { slug: null };
      logEvent(state, 'Drill ended');
      return json(route, computeView(state));
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
