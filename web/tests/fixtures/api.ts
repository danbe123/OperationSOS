import type {
  AiEvent, Card, LibraryItem, LibraryResponse, MapConfig, Note, Page, Place, Playbook, PlaybookSummary,
  SearchResponse, Status, Suggestion, UpdateProgress,
} from '../../src/api/types';

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

const scenarioRows: [string, string, string][] = [
  ['nuclear-war', 'Nuclear war', 'radiation'], ['nuclear-accident', 'Nuclear accident', 'plume'],
  ['pandemic', 'Pandemic', 'virus'], ['grid-collapse', 'National grid collapse', 'power'],
  ['solar-storm', 'Solar superstorm', 'sun'], ['emp', 'EMP attack', 'bolt'],
  ['cyber-attack', 'Cyber attack', 'lock'], ['invasion', 'Invasion or occupation', 'shield'],
  ['civil-unrest', 'Civil unrest', 'fire'], ['economic-collapse', 'Economic collapse', 'coins'],
  ['supply-chain', 'Supply chain collapse', 'truck'], ['storms-flooding', 'Storms and flooding', 'wave'],
  ['severe-winter', 'Severe winter', 'snowflake'], ['heat-drought', 'Heat and drought', 'thermometer'],
  ['volcanic', 'Volcanic ash', 'volcano'], ['chemical', 'Chemical disaster', 'flask'],
  ['famine', 'Famine', 'wheat'], ['impact-winter', 'Impact winter', 'moon'],
  ['terrorism', 'Terrorism', 'alert'], ['long-rebuild', 'The long rebuild', 'hammer'],
];
export const playbooks: PlaybookSummary[] = scenarioRows.map(([slug, title, icon], i) => ({
  slug, title, icon, order: i + 1, summary: `${title}: what to do right now and over the months after.`,
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
    { source: 'playbooks', badge: 'Playbook', count: 1 }, { source: 'wikipedia', badge: 'Wikipedia', count: 1 },
    { source: 'nhs', badge: 'NHS', count: 1 }, { source: 'places', badge: 'Place', count: 1 }, { source: 'docs', badge: 'UK official', count: 1 },
  ],
  took_ms: 120, partial: false,
};

export const suggestions: Suggestion[] = [
  { value: 'Water', label: 'Water', url: `/read/${WIKI}/A/Water`, source: 'wikipedia' },
  { value: 'Water disinfection', label: 'Water disinfection', url: '/p/water-disinfection', source: 'pages' },
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
