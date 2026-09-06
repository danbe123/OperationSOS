import type {
  AiEvent, Card, Condition, ConditionId, ConditionState, Conditions, LibraryItem, LibraryResponse, MapConfig, NearbyResponse, Note,
  ExportChunks, ImportSummary, Neighbour, Page, Place, Playbook, PlaybookSummary, SearchResponse, Sensors, SituationView, Status, StockResponse, Suggestion, UpdateProgress,
} from '../../src/api/types';
import { CONDITION_IDS } from '../../src/api/types';

export const status: Status = {
  version: '0.1.0', uptime_s: 3600, cpu_temp_c: 51.2, load: [0.3, 0.2, 0.1],
  mem: { total_mb: 8000, used_mb: 2100 },
  disks: {
    core: { mounted: true, path: '/srv/sos/core', total_gb: 465, free_gb: 260 },
    extended: { mounted: false, path: '/srv/sos/extended', total_gb: 0, free_gb: 0 },
  },
  hotspot: { ssid: 'SOS', ip: '10.42.0.1', clients: 1, enabled: true },
  eth_mode: 'client', power_mode: 'normal',
  ai: { state: 'off', model: null, message: null },
  thermal_ai_off_c: 80, idle_minutes: 5, home_minutes: 30,
  pin_required: false, dev: true, default_theme: 'vault',
  conditions: Object.fromEntries(CONDITION_IDS.map((id) => [id, 'working' as ConditionState])) as Record<ConditionId, ConditionState>,
  modes: { theme: null, dim: false, calls: 'shown', map_first: false, board: false },
  drill: false, readiness_score: 62,
};

export const WIKI = 'wikipedia_en_100_mini_2026-01';

export const wikiItem: LibraryItem = {
  id: WIKI, title: 'Wikipedia (100 articles, test)', kind: 'zim', tier: 'core', category: 'reference', scenarios: [],
  size_bytes: 4_700_000, as_at: '2026-01', licence: 'CC BY-SA 4.0', available: true,
  url: `/read/${WIKI}/A/Main_Page`, description: 'A tiny Wikipedia sample', drive_label: 'Core',
};
export const nhsItem: LibraryItem = {
  id: 'nhs_uk', title: 'NHS (as at 2026-08)', kind: 'zim', tier: 'core', category: 'medical', scenarios: ['pandemic'],
  size_bytes: 1_900_000_000, as_at: '2026-08', licence: 'OGL v3', available: true,
  url: '/read/nhs_uk/www.nhs.uk/index.html', description: 'Conditions, medicines, symptoms', drive_label: 'Core',
};
export const nhsMedicinesItem: LibraryItem = {
  id: 'nhs_medicines', title: 'NHS medicines (Kiwix)', kind: 'zim', tier: 'core', category: 'medical', scenarios: [],
  size_bytes: 120_000_000, as_at: '2025-12', licence: 'OGL v3', available: true,
  url: '/read/nhs_medicines/A/index', description: 'NHS medicines A to Z', drive_label: 'Core',
};
export const pdfItem: LibraryItem = {
  id: 'nrr-2025', title: 'National Risk Register 2025', kind: 'pdf', tier: 'core', category: 'uk-official', scenarios: [],
  size_bytes: 9_400_000, as_at: '2025-01-16', licence: 'OGL v3', available: true,
  url: '/docs/core/docs/nrr-2025.pdf', description: 'The government risk register', drive_label: 'Core',
};
export const epubItem: LibraryItem = {
  id: 'where-there-is-no-doctor', title: 'Where There Is No Doctor', kind: 'epub', tier: 'core', category: 'medical', scenarios: [],
  size_bytes: 22_000_000, as_at: '2023', licence: 'CC BY-NC-SA', available: true,
  url: '/docs/core/docs/where-there-is-no-doctor.epub', description: 'Village health care handbook', drive_label: 'Core',
};
export const extItem: LibraryItem = {
  id: 'gutenberg_en_all', title: 'Project Gutenberg', kind: 'zim', tier: 'extended', category: 'books', scenarios: [],
  size_bytes: 206_000_000_000, as_at: '2025-11', licence: 'Public domain', available: false,
  url: null, description: '70,000 books', drive_label: 'On external drive (not connected)',
};
export const mapsItem: LibraryItem = {
  id: 'uk-ie-base', title: 'Base map (UK and Ireland)', kind: 'pmtiles', tier: 'core', category: 'maps', scenarios: [],
  size_bytes: 3_400_000_000, as_at: '2026-09-02', licence: 'ODbL', available: true,
  url: '/maps/uk-ie.pmtiles', description: 'Protomaps extract', drive_label: 'Core',
};

export const library: LibraryResponse = {
  categories: [
    { id: 'medical', title: 'Medical', items: [nhsItem, nhsMedicinesItem, epubItem] },
    { id: 'uk-official', title: 'UK official', items: [pdfItem] },
    { id: 'reference', title: 'Reference', items: [wikiItem] },
    { id: 'maps', title: 'Maps', items: [mapsItem] },
    { id: 'books', title: 'Books', items: [extItem] },
  ],
};

/* The twenty situations, with the first line of each guide's own summary: a tile's line is the
   guide's own words, never its title said twice. Each is written to fit two lines at 390 px — about
   60 characters — so nothing has to be clamped and cut mid-word. */
const scenarioRows: [string, string, string, string][] = [
  ['nuclear-war', 'Nuclear war', 'radiation', 'A nuclear strike on the UK.'],
  ['nuclear-accident', 'Nuclear accident', 'plume', 'A radiation release from a UK or nearby site.'],
  ['pandemic', 'Pandemic', 'virus', 'A respiratory pandemic that overwhelms the NHS.'],
  ['grid-collapse', 'National grid collapse', 'power', 'A nationwide blackout lasting days to weeks.'],
  ['solar-storm', 'Solar superstorm', 'sun', 'A Carrington-class geomagnetic storm.'],
  ['emp', 'EMP attack', 'bolt', 'A nuclear burst kills electronics nationwide.'],
  ['cyber-attack', 'Cyber attack', 'lock', 'Sabotage takes out the NHS, banks or the grid.'],
  ['invasion', 'Invasion or occupation', 'shield', 'War on UK soil: strikes, fighting, occupation.'],
  ['civil-unrest', 'Civil unrest', 'fire', 'Rioting and arson, and police that cannot come.'],
  ['economic-collapse', 'Economic collapse', 'coins', 'Banks closed, cards dead, prices doubling.'],
  ['supply-chain', 'Supply chain collapse', 'truck', 'Fuel, food and medicine stop arriving.'],
  ['storms-flooding', 'Storms and flooding', 'wave', 'Storm winds, river floods and a North Sea surge.'],
  ['severe-winter', 'Severe winter', 'snowflake', 'Deep snow and hard frost, with heating fuel short.'],
  ['heat-drought', 'Heat and drought', 'thermometer', 'Days over 35 degrees, hosepipe bans, standpipes.'],
  ['volcanic', 'Volcanic ash', 'volcano', 'Icelandic ash and sulphur over Britain for weeks.'],
  ['chemical', 'Chemical disaster', 'flask', 'A toxic plume from a works, a tanker or an attack.'],
  ['famine', 'Famine', 'wheat', 'Blight, livestock disease, no fertiliser, no imports.'],
  ['impact-winter', 'Impact winter', 'moon', 'Years of cold, dark summers after a nuclear war.'],
  ['terrorism', 'Terrorism', 'alert', 'A bombing, a vehicle attack, or a poisoning.'],
  ['long-rebuild', 'The long rebuild', 'hammer', 'No state, no grid, no supply chain, for years.'],
];
export const playbooks: PlaybookSummary[] = scenarioRows.map(([slug, title, icon, summary], i) => ({
  slug, title, icon, order: i + 1, summary,
}));

export const playbook: Playbook = {
  slug: 'grid-collapse', title: 'National grid collapse', icon: 'power', order: 4,
  summary: 'Weeks-long blackout, water pumps and comms down.',
  sections: [
    { id: 'right-now', title: 'Right now', html: '<p>Switch off the cooker and the iron. Fill the bath. See <a href="/medical/card/cpr-adult">CPR</a> if someone collapses.</p><p>{{module:water}}</p>' },
    { id: 'first-72-hours', title: 'First 72 hours', html: '<p>Keep the freezer shut: 48 hours if full.</p><div data-module="power"></div>' },
    { id: 'first-month', title: 'First month', html: '<p>Organise the street.</p>' },
    { id: 'long-term', title: 'Long term', html: '<p>Local generation.</p>' },
    { id: 'uk-specifics', title: 'UK specifics', html: '<p>Call <strong>105</strong> for your electricity network operator. Register for the Priority Services Register.</p>' },
    { id: 'go-deeper', title: 'Go deeper', html: `<ul><li><a href="/read/${WIKI}/A/Electrical_grid">Electrical grid</a></li><li><a href="/doc/nrr-2025#page=12">National Risk Register, page 12</a></li></ul>` },
  ],
  checklist: [
    { id: 'fill-bath', text: 'Fill the bath and every container with water', checked: false, updated_at: null },
    { id: 'torch', text: 'Find torches and spare batteries', checked: true, updated_at: '2026-09-03T10:00:00Z' },
    { id: 'freezer', text: 'Keep the freezer shut', checked: false, updated_at: null },
  ],
  modules: [
    { slug: 'water', title: 'Water', html: '<p>Store 3 litres per person per day.</p>' },
    { slug: 'power', title: 'Power', html: '<p>Run generators outdoors only: carbon monoxide kills.</p>' },
  ],
  overlays: ['health', 'water'],
  sources: [{ title: 'National Risk Register 2025', doc: 'nrr-2025', as_at: '2025-01-16' }],
  reviewed: '2026-09-10',
};

export const search: SearchResponse = {
  q: 'water', query: 'water',
  results: [
    { source: 'playbooks', badge: 'Playbook', title: 'Water', snippet: 'Store 3 litres per person per day.', url: '/m/water', score: 0.32, kind: 'module' },
    { source: 'wikipedia', badge: 'Wikipedia', title: 'Water', snippet: 'Water is an inorganic compound.', url: `/read/${WIKI}/A/Water`, score: 0.167, kind: 'article' },
    { source: 'nhs', badge: 'NHS', title: 'Dehydration', snippet: 'Dehydration means your body loses more fluids than you take in.', url: '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', score: 0.15, kind: 'article' },
    { source: 'places', badge: 'Place', title: 'Waterlooville', snippet: 'Town, England', url: '/map?lat=50.88&lon=-1.03&z=13&label=Waterlooville', score: 0.14, kind: 'place', lat: 50.88, lon: -1.03 },
    { source: 'docs', badge: 'UK official', title: 'National Risk Register 2025, page 12', snippet: 'loss of water supply', url: '/doc/nrr-2025#page=12', score: 0.12, kind: 'doc', page: 12 },
  ],
  groups: [
    { source: 'playbooks', badge: 'Playbooks', count: 1 }, { source: 'wikipedia', badge: 'Wikipedia', count: 1 },
    { source: 'nhs', badge: 'NHS', count: 1 }, { source: 'places', badge: 'Places', count: 1 }, { source: 'docs', badge: 'UK official', count: 1 },
  ],
  took_ms: 120, partial: false,
};

export const suggestions: Suggestion[] = [
  { value: 'Water', label: 'Water', url: `/read/${WIKI}/A/Water`, source: 'Wikipedia' },
  { value: 'Water disinfection', label: 'Water disinfection', url: '/p/water-disinfection', source: 'page' },
  { value: 'water purification', label: 'water purification', url: null, source: 'query' },
];

export const cards: Card[] = [
  {
    slug: 'cpr-adult', title: 'CPR (adult)', icon: 'heart', order: 1,
    html: '<ol><li>Check for danger, then check for a response.</li><li>Call 999 and put it on speaker.</li><li>Push hard and fast in the centre of the chest, 100 to 120 a minute.</li><li>After 30 compressions give 2 breaths if you are trained.</li></ol><p class="warning">Do not stop until help arrives or the person breathes.</p>',
  },
  {
    slug: 'severe-bleeding', title: 'Severe bleeding', icon: 'drop', order: 2,
    html: '<ol><li>Press hard on the wound with a clean cloth.</li><li>Call 999.</li><li>Keep pressing; do not lift to look.</li></ol>',
  },
];

export const pages: Page[] = [
  { slug: 'pmr446', title: 'PMR446 radio', icon: 'radio', order: 1, html: '', category: 'comms' },
  { slug: 'uk-numbers', title: 'UK emergency numbers', icon: 'phone', order: 2, html: '', category: 'comms' },
  { slug: 'what-still-works', title: 'What still works', icon: 'wifi', order: 3, html: '', category: 'comms' },
  { slug: 'water-disinfection', title: 'Water disinfection', icon: 'drop', order: 1, html: '', category: 'reference' },
  { slug: 'household-plan', title: 'Household plan', icon: 'plan', order: 1, html: '', category: 'plan' },
  { slug: 'about-sos', title: 'About SOS', icon: 'help', order: 1, html: '', category: 'about' },
];
export const page: Page = {
  slug: 'pmr446', title: 'PMR446 radio', icon: 'radio', order: 1, category: 'comms',
  html: '<p>Channel 1 is <strong>446.00625 MHz</strong>.</p><table><tr><th>Channel</th><th>MHz</th></tr><tr><td>1</td><td>446.00625</td></tr></table>',
};
export const householdPlan: Page = {
  slug: 'household-plan', title: 'Household plan', icon: 'plan', order: 1, category: 'plan',
  html: '<h2>Meeting points</h2><p>First: the front gate. Second: the church hall.</p><h2>Out-of-area contact</h2><p>Name and number.</p>',
};

export const mapConfig: MapConfig = {
  bases: [
    { id: 'osm', title: 'OpenStreetMap', styles: { vault: '/maps/styles/osm-vault.json', field: '/maps/styles/osm-field.json', blackout: '/maps/styles/osm-blackout.json' }, available: true },
    { id: 'os', title: 'OS Open Zoomstack', styles: { vault: '/maps/styles/os-vault.json', field: '/maps/styles/os-field.json', blackout: '/maps/styles/os-blackout.json' }, available: true },
  ],
  terrain: { contours: '/maps/contours.pmtiles', hillshade: '/maps/hillshade.pmtiles' },
  overlays: [
    { id: 'health', title: 'Hospitals, pharmacies, GP surgeries', kind: 'geojson', layer_id: null, url: '/maps/overlays/health.geojson', default_on: false, scenarios_on: ['pandemic'], coverage: ['england', 'wales', 'scotland', 'ni', 'roi', 'iom', 'ci'], color: '#e53935', icon: 'medical', available: true },
    { id: 'footpaths', title: 'Footpaths and rights of way', kind: 'pmtiles', layer_id: null, url: '/maps/overlays/footpaths.pmtiles', default_on: true, scenarios_on: [], coverage: ['england', 'wales', 'scotland', 'ni', 'roi', 'iom', 'ci'], color: '#2e7d32', icon: null, available: true },
    { id: 'access-land', title: 'Open access land', kind: 'geojson', layer_id: null, url: '/maps/overlays/access-land.geojson', default_on: false, scenarios_on: [], coverage: ['england', 'wales'], color: '#f9a825', icon: null, available: true },
    { id: 'flood-zones', title: 'Flood zones', kind: 'pmtiles', layer_id: null, url: '/maps/overlays/flood-zones.pmtiles', default_on: false, scenarios_on: ['storms-flooding'], coverage: ['england', 'wales', 'scotland', 'ni'], color: '#1e88e5', icon: null, available: false },
    { id: 'contour-labels', title: 'Contour labels', kind: 'style-layer', layer_id: 'contour_label', url: null, default_on: false, scenarios_on: [], coverage: ['england', 'wales', 'scotland', 'ni', 'roi', 'iom', 'ci'], color: '#8d6e63', icon: null, available: true },
  ],
  packs: [{ title: 'UK_England_South', url: '/maps/packs/UK_England_South.mwm', size_bytes: 1_200_000_000 }],
  packs_index_url: '/maps/packs/index.html',
};

export const places: Place[] = [
  { name: 'Oxford', kind: 'City', lat: 51.752, lon: -1.2577, region: 'England', postcode: null },
  { name: 'SO16 0AS', kind: 'Postcode', lat: 50.9379, lon: -1.4708, region: 'England', postcode: 'SO16 0AS' },
];

export const notes: Note[] = [
  { id: 1, kind: 'note', title: 'Meeting point', body: 'The church hall on Mill Lane', lat: null, lon: null, updated_at: '2026-09-03T09:00:00Z' },
  { id: 2, kind: 'pin', title: 'Well', body: '', lat: 50.94, lon: -1.47, updated_at: '2026-09-03T09:30:00Z' },
];

export const updateProgress: UpdateProgress = { running: true, lines: ['Resolving wikipedia_en_all_maxi', 'Downloading 12%'], done: false, ok: null };

export const aiEvents: AiEvent[] = [
  { event: 'verbatim', data: { title: 'Dehydration', url: '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', paragraphs: ['Dehydration means your body loses more fluids than you take in.', 'Drink fluids when you feel any dehydration symptoms.'], as_at: '2026-08' } },
  { event: 'retrieving', data: { query: 'dehydration signs', passages: [
    { n: 1, title: 'Dehydration', url: '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', source: 'NHS', text: 'Signs of dehydration include dark yellow urine and feeling dizzy.' },
    { n: 2, title: 'Water', url: '/m/water', source: 'Playbook', text: 'Store 3 litres per person per day.' },
  ] } },
  { event: 'token', data: { text: 'Signs include ' } },
  { event: 'token', data: { text: 'dark urine [1].' } },
  { event: 'done', data: { answer: 'Signs include dark yellow urine and dizziness [1].', grounded: true, citations: [{ n: 1, title: 'Dehydration', url: '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', source: 'NHS' }] } },
];

/** Serialise events as the server does: `event:` + `data:` frames, blank-line separated, with a ping comment. */
export function sseBody(events: AiEvent[]): string {
  return events.map((e, i) => `${i === 1 ? ': ping\n\n' : ''}event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`).join('');
}

/* The situation engine's View, at a fixed clock so countdowns are stable. */
export const VIEW_NOW = '2026-09-06T14:00:00.000Z';
const CONDITION_TITLES: Record<ConditionId, string> = {
  power: 'Mains power', water: 'Water supply', mobile: 'Mobile network', landline: 'Landline and 999', internet: 'Internet',
  gas: 'Gas', heating: 'Heating', roads: 'Roads and transport', shops: 'Shops and cash', sewage: 'Sewage and drains',
};

export function condition(id: ConditionId, state: ConditionState = 'working', over: Partial<Condition> = {}): Condition {
  const now = Date.parse(VIEW_NOW);
  const since = over.since ?? new Date(now - (state === 'working' ? 0 : 3600_000)).toISOString();
  return {
    id, title: CONDITION_TITLES[id], state, since,
    for_s: Math.round((now - Date.parse(since)) / 1000),
    source: 'manual', confidence: 1, note: '', set_by: 'phone',
    updated_at: since, confirmed_at: since, stale: false, ...over,
  };
}

/** A whole View: peacetime by default, with the pieces a test cares about overridden. */
export function makeView(over: Partial<SituationView> = {}): SituationView {
  const conditions = Object.fromEntries(CONDITION_IDS.map((id) => [id, condition(id)])) as Conditions;
  return {
    meta: { now: VIEW_NOW, dark: false, sunrise: '2026-09-06T05:22:00.000Z', sunset: '2026-09-06T18:41:00.000Z', home: null, drill: false },
    scenario: null,
    conditions,
    inferred: [], forecast: [], tasks: [], briefing: [],
    modes: { theme: null, dim: false, calls: 'shown', map_first: false, board: false },
    readiness: { score: 62, gaps: [{ title: 'Water: 1.5 days for 3 people', link: '/plan#stock', points: 12 }] },
    bulletins: { next: { station: 'BBC Radio 4', frequency: '198 kHz LW', at: '2026-09-06T18:00:00.000Z' } },
    ...over,
    ...(over.conditions ? { conditions: { ...conditions, ...over.conditions } } : {}),
  };
}

export const view: SituationView = makeView();

/** Power off for an hour: a freezer countdown, a bath to fill, and the box guessing about the mobile network. */
export const powerOffView: SituationView = makeView({
  conditions: { power: condition('power', 'off'), mobile: condition('mobile', 'degraded') } as Conditions,
  inferred: [{ condition: 'mobile', state: 'off', confidence: 0.7, due_at: '2026-09-06T21:00:00.000Z', why: 'Masts run about 8 hours on battery.', rule: 'power-off-mobile-off', source: 'page:what-still-works' }],
  forecast: [
    { id: 'fridge', title: 'Fridge food unsafe', due_at: '2026-09-06T17:00:00.000Z', severity: 'warn', why: 'A closed fridge holds about 4 hours.', link: 'module:food', passed: false },
    { id: 'freezer', title: 'Freezer food unsafe', due_at: '2026-09-07T13:00:00.000Z', severity: 'danger', why: 'A half-full freezer holds about 24 hours.', link: 'module:food', passed: false },
  ],
  tasks: [
    { id: 'fill-bath', title: 'Fill the bath and every container', bucket: 'now', why: 'Pumped supplies fail once the power has been off a day.', link: 'module:water', person: null, done: false, done_at: null, source: 'rule:fill-bath' },
    { id: 'freezer-shut', title: 'Keep the fridge and freezer shut', bucket: 'now', why: 'Every opening costs hours.', link: 'module:food', person: 'Sam', done: false, done_at: null, source: 'rule:freezer-shut' },
    { id: 'cash', title: 'Get cash out while the shops take cards', bucket: 'hour', why: 'Card terminals need power.', link: 'module:money', person: null, done: false, done_at: null, source: 'rule:cash' },
    { id: 'street', title: 'Knock on both neighbours', bucket: 'today', why: 'Check on anyone medically dependent.', link: 'page:neighbours', person: null, done: true, done_at: '2026-09-06T13:00:00.000Z', source: 'rule:street' },
  ],
  briefing: [
    { title: 'Right now', kind: 'playbook-section', ref: 'grid-collapse#right-now' },
    { title: 'Power', kind: 'module', ref: 'power' },
    { title: 'What still works in an outage', kind: 'page', ref: 'what-still-works' },
  ],
});

/* Phase 2 and 3 fixtures: the event log, the stock, the facilities round the home and the box's senses. */
export const events: Note[] = [
  { id: 44, kind: 'event', title: 'Mains power off since 13:00 (phone)', body: '', lat: null, lon: null, updated_at: '2026-09-06T13:02:00.000Z' },
  { id: 43, kind: 'event', title: 'Fill the bath ticked by Sam', body: '', lat: null, lon: null, updated_at: '2026-09-06T13:20:00.000Z' },
  { id: 42, kind: 'event', title: 'Drill started: National grid collapse', body: '', lat: null, lon: null, updated_at: '2026-09-06T12:00:00.000Z' },
];

export const stockResponse: StockResponse = {
  people: 3,
  items: [
    { id: 1, name: 'Bottled water', category: 'water', quantity: 13.5, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: 1.5 },
    { id: 2, name: 'Tins', category: 'food', quantity: 42, unit: 'meals', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: 4.6 },
  ],
};

export const nearby: NearbyResponse = {
  lat: 50.9379, lon: -1.4708,
  method: "Straight-line distance and bearing; walking time by Naismith's rule (5 km/h). Roads and paths will be longer.",
  facilities: [
    {
      id: 'pharmacy', title: 'Pharmacy', found: true, searched: ['health'], note: null,
      nearest: { name: 'Boots, High Street', lat: 50.9345, lon: -1.4331, distance_m: 620, bearing_deg: 92, compass: 'E', walk_minutes: 8, source: 'overlay:health', properties: { amenity: 'pharmacy', opening_hours: 'Mo-Sa 09:00-17:30' } },
      also: [{ name: 'Shirley Pharmacy', lat: 50.9290, lon: -1.4460, distance_m: 1400, bearing_deg: 200, compass: 'SSW', walk_minutes: 17, source: 'overlay:health', properties: {} }],
    },
    {
      id: 'emergency-department', title: 'Emergency department', found: true, searched: ['health'],
      note: 'Hospitals from OpenStreetMap. The overlay does not carry the emergency=yes tag, so a small hospital without an A&E can appear: ring ahead if the phones are up.',
      nearest: { name: 'Southampton General Hospital', lat: 50.9331, lon: -1.4342, distance_m: 4300, bearing_deg: 270, compass: 'W', walk_minutes: 52, source: 'overlay:health', properties: { amenity: 'hospital' } },
      also: [],
    },
    {
      id: 'rest-centre', title: 'Rest centre', found: false, searched: [], nearest: null, also: [],
      note: 'Rest centres are opened by the council on the day and are not mapped in advance.',
      why: 'No searchable copy of the emergency-services overlay on this box.',
    },
  ],
};

/* Phase 4: the street, and carrying the situation to another box. */
export const neighbours: Neighbour[] = [
  { id: 1, name: 'Joan Reeve', address: '14 Mill Lane', needs: 'oxygen concentrator, cannot manage stairs', skills: '', contacts: '07700 900123', notes: 'key is with number 12', updated_at: '2026-09-05T10:00:00Z' },
  { id: 2, name: 'Ade Okafor', address: '18 Mill Lane', needs: '', skills: 'nurse, has a petrol generator', contacts: '07700 900456', notes: '', updated_at: '2026-09-05T10:00:00Z' },
];

export const exportChunks: ExportChunks = {
  chunks: ['{"i":0,"n":2,"d":"H4sIAAAAAAACA61W247bIBD9FcRTq"}', '{"i":1,"n":2,"d":"8ar0iFOzA90K7V9aCv1oapWGHC"}'],
};

export const importSummary: ImportSummary = {
  ok: true, version: 1, exported_at: '2026-09-06T13:00:00Z',
  counts: {
    conditions: { updated: 2, kept: 8 },
    household: { added: 1, updated: 0, kept: 2 },
    neighbours: { added: 2, updated: 0, kept: 0 },
    events: { added: 3, skipped: 1 },
  },
  home: 'kept', scenario: 'started: grid-collapse',
  changes: ['Mains power set to off', 'Joan Reeve added to the street list'],
};

export const sensors: Sensors = {
  internet: { value: 0, unit: 'up', at: '2026-09-06T13:58:00.000Z' },
  mains: { value: 0, unit: 'on', at: '2026-09-06T13:59:00.000Z' },
  temp_in: { value: 14.5, unit: '°C', at: '2026-09-06T13:57:00.000Z' },
  co_ppm: { value: 3, unit: 'ppm', at: '2026-09-06T13:30:00.000Z' },
};
