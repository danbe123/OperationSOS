import type {
  AiEvent, Card, Condition, ConditionId, ConditionState, Conditions, Kit, KitsResponse, LibraryItem, LibraryResponse, MapConfig, NearbyResponse, Note,
  ExportChunks, ImportSummary, Page, Place, Playbook, PlaybookSummary, SearchResponse, Sensors, SituationView, Status, Suggestion, UpdateProgress,
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
  pin_required: false, dev: true, default_theme: 'field',
  conditions: Object.fromEntries(CONDITION_IDS.map((id) => [id, 'working' as ConditionState])) as Record<ConditionId, ConditionState>,
  modes: { theme: null, dim: false, calls: 'shown', map_first: false, board: false },
  drill: false,
};

export const WIKI = 'wikipedia_en_100_mini_2026-01';

export const wikiItem: LibraryItem = {
  id: WIKI, title: 'Wikipedia (100 articles, test)', kind: 'zim', tier: 'core', category: 'reference', scenarios: [],
  size_bytes: 4_700_000, as_at: '2026-01', licence: 'CC BY-SA 4.0', available: true,
  url: `/read/${WIKI}/A/Main_Page`, file_url: null, description: 'A tiny Wikipedia sample', drive_label: 'Core',
};
export const nhsItem: LibraryItem = {
  id: 'nhs_uk', title: 'NHS website: conditions, symptoms, medicines', kind: 'zim', tier: 'core', category: 'medical', scenarios: ['pandemic'],
  size_bytes: 1_900_000_000, as_at: '2026-08', licence: 'OGL v3', available: true,
  url: '/read/nhs_uk/www.nhs.uk/index.html', file_url: null,
  description: 'The NHS website saved for offline use: conditions A to Z, symptoms, medicines, mental health and healthy living.',
  drive_label: 'Core',
};
export const nhsMedicinesItem: LibraryItem = {
  id: 'nhs_medicines', title: 'NHS Medicines A to Z', kind: 'zim', tier: 'core', category: 'medical', scenarios: [],
  size_bytes: 120_000_000, as_at: '2025-12', licence: 'OGL v3', available: true,
  url: '/read/nhs_medicines/A/index', file_url: null, description: 'Every medicine the NHS lists, with doses and side effects.', drive_label: 'Core',
};
/* The two shapes the document viewer meets, exactly as `/api/library/<id>` gives them: `url` is the
   app route the library links to and `file_url` is the file on the drive the viewer must load. The
   round-3 fixture put the file path in `url` and had no `file_url` at all, which is why 354
   screenshots never showed the fault that every PDF on the real box failed to open. */
export const pdfItem: LibraryItem = {
  id: 'nrr-2025', title: 'National Risk Register 2025', kind: 'pdf', tier: 'core', category: 'uk-official', scenarios: [],
  size_bytes: 9_400_000, as_at: '2025-01-16', licence: 'OGL v3', available: true,
  url: '/doc/nrr-2025', file_url: '/docs/core/nrr-2025.pdf', description: 'The government risk register', drive_label: 'Core',
};
export const epubItem: LibraryItem = {
  id: 'where-there-is-no-doctor', title: 'Where There Is No Doctor (Hesperian, 1992 revised edition)', kind: 'epub', tier: 'core', category: 'medical', scenarios: [],
  size_bytes: 22_000_000, as_at: '2023', licence: 'CC BY-NC-SA', available: true,
  url: '/doc/where-there-is-no-doctor', file_url: '/docs/core/where-there-is-no-doctor.epub',
  description: 'Village health care handbook', drive_label: 'Core',
};
/* A document the catalogue lists and the drive does not carry: the missing state, with a file_url
   that answers 404. */
export const missingDocItem: LibraryItem = {
  id: 'fm-21-76-survival', title: 'FM 21-76 Survival (US Army)', kind: 'pdf', tier: 'extended', category: 'practical', scenarios: [],
  size_bytes: 12_000_000, as_at: '1992', licence: 'Public domain', available: true,
  url: '/doc/fm-21-76-survival', file_url: '/docs/extended/fm-21-76-survival.pdf',
  description: 'The US Army survival manual', drive_label: 'External drive',
};
export const extItem: LibraryItem = {
  id: 'gutenberg_en_all', title: 'Project Gutenberg', kind: 'zim', tier: 'extended', category: 'books', scenarios: [],
  size_bytes: 206_000_000_000, as_at: '2025-11', licence: 'Public domain', available: false,
  url: null, file_url: null, description: '70,000 books', drive_label: 'On external drive (not connected)',
};
export const mapsItem: LibraryItem = {
  id: 'uk-ie-base', title: 'Base map (UK and Ireland)', kind: 'pmtiles', tier: 'core', category: 'maps', scenarios: [],
  size_bytes: 3_400_000_000, as_at: '2026-09-02', licence: 'ODbL', available: true,
  url: '/maps/uk-ie.pmtiles', file_url: null, description: 'Protomaps extract', drive_label: 'Core',
};

export const library: LibraryResponse = {
  categories: [
    { id: 'medical', title: 'Medical', items: [nhsItem, nhsMedicinesItem, epubItem] },
    { id: 'uk-official', title: 'UK official', items: [pdfItem] },
    { id: 'practical', title: 'Practical', items: [missingDocItem] },
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

/* What `/api/search?q=water` really answers: the engine wraps every match in `<b>`, the box's own
   pages carry section anchors on their URLs, and a mirrored NHS page's snippet can be the site's own
   furniture rather than an answer. The screen has to cope with all three. */
export const search: SearchResponse = {
  q: 'water', query: 'water',
  results: [
    { source: 'playbooks', badge: 'Playbook', title: 'Water', snippet: 'Store 3 litres of <b>water</b> per person per day.', url: '/m/water', score: 0.32, kind: 'module' },
    { source: 'playbooks', badge: 'Page', title: 'Water disinfection', snippet: 'Boil the <b>water</b> for one minute, or add the tablets and wait.', url: '/p/water-disinfection#dosing', score: 0.3, kind: 'page' },
    { source: 'playbooks', badge: 'Page', title: 'Water disinfection', snippet: 'Sources of <b>water</b> outdoors, and which ones to leave alone.', url: '/p/water-disinfection#sources', score: 0.24, kind: 'page' },
    { source: 'wikipedia', badge: 'Wikipedia (100 articles, test) (Kiwix build, December 2025)', title: 'Water', snippet: '<b>Water</b> is an inorganic compound.', url: `/read/${WIKI}/A/Water`, score: 0.167, kind: 'article' },
    { source: 'nhs', badge: 'NHS', title: 'Dehydration - NHS', snippet: 'Dehydration means your body loses more fluids than you take in.', url: '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', score: 0.15, kind: 'article' },
    { source: 'nhs', badge: 'NHS', title: 'Anticoagulant medicines – Side effects', snippet: 'Help us improve our website Can you answer a 5 minute survey about your visit today? Take our survey Support links Home Health A to Z NHS services Live Well © Crown copyright', url: '/read/nhs_uk/www.nhs.uk/conditions/anticoagulants/side-effects/', score: 0.14, kind: 'article' },
    { source: 'places', badge: 'Place', title: 'Waterlooville', snippet: 'Town, England', url: '/map?lat=50.88&lon=-1.03&z=13&label=Waterlooville', score: 0.14, kind: 'place', lat: 50.88, lon: -1.03 },
    { source: 'docs', badge: 'UK official', title: 'National Risk Register 2025, page 12', snippet: 'loss of <b>water</b> supply', url: '/doc/nrr-2025#page=12', score: 0.12, kind: 'doc', page: 12 },
  ],
  groups: [
    { source: 'playbooks', badge: 'Playbooks', count: 3 }, { source: 'wikipedia', badge: 'Wikipedia', count: 1 },
    { source: 'nhs', badge: 'NHS', count: 2 }, { source: 'places', badge: 'Places', count: 1 }, { source: 'docs', badge: 'UK official', count: 1 },
  ],
  took_ms: 120, partial: false,
};

export const suggestions: Suggestion[] = [
  { value: 'Water', label: 'Water', url: `/read/${WIKI}/A/Water`, source: 'Wikipedia' },
  { value: 'Water disinfection', label: 'Water disinfection', url: '/p/water-disinfection', source: 'page' },
  { value: 'water purification', label: 'water purification', url: null, source: 'query' },
];

/* The real CPR (adult) card, as `/api/cards/cpr-adult` renders it: a "When to use" section, eight
   steps of which six are whole sentences, two warnings and a "Stop or escalate". Round 3's fixture
   had four short steps, which is why the shrink ladder looked as though it worked and every real
   card on the box rendered its steps at 18 px body type. */
const CPR_WHEN = '<h2>When to use</h2><p>Someone has collapsed, does not respond when you shout and shake them, and is not breathing normally.</p>';
const CPR_STEPS_TAIL = [
  'Send someone for a defibrillator (AED) if one is nearby.',
  'Kneel beside them. Heel of one hand on the centre of the chest.',
  'Other hand on top, arms straight. Press down 5 to 6 cm, 100 to 120 times a minute (two a second), letting the chest come back up fully each time.',
  'After 30 presses, tilt the head back, lift the chin, pinch the nose and give 2 breaths, each one second, watching the chest rise. If you cannot or will not give breaths, keep pressing without stopping.',
  'Carry on 30 presses then 2 breaths. Swap with someone every two minutes if you can.',
  'When the AED arrives, turn it on and follow its voice instructions; keep pressing while the pads go on.',
  'Do not stop until they breathe normally, help takes over, or you are exhausted.',
];
const CPR_TAIL =
  '<h2>Warnings</h2><p class="warning">Gasping, snoring or occasional gulps are not normal breathing. Start CPR.</p>'
  + '<p class="warning">Broken ribs are common and do not mean stop.</p>'
  + '<h2>Stop or escalate</h2><p>Stop only when the person breathes normally on their own, or a paramedic takes over.</p>';
const cprHtml = (step1: string) =>
  `${CPR_WHEN}<h2>Steps</h2><ol><li>${step1}</li>${CPR_STEPS_TAIL.map((t) => `<li>${t}</li>`).join('')}</ol>${CPR_TAIL}`;

const CHOKING_STEPS = [
  'If they can cough, tell them to keep coughing. Stay with them.',
  'If not: lean them forward, 5 hard blows between the shoulder blades.',
  'Check the mouth after each blow and remove anything you can see.',
  'If still choking: stand behind, fist above the navel, other hand over it, pull sharply inwards and upwards 5 times.',
  'Keep alternating 5 back blows and 5 abdominal thrusts.',
  'Baby under one: lay face down along your forearm, head low, 5 back blows; then face up, 5 chest thrusts with two fingers on the breastbone. Never abdominal thrusts on a baby.',
];
const chokingHtml = (last: string) =>
  '<h2>When to use</h2><p>Someone cannot breathe, cough or speak, is clutching their throat, or is turning blue.</p>'
  + `<h2>Steps</h2><ol>${CHOKING_STEPS.map((t) => `<li>${t}</li>`).join('')}<li>${last}</li></ol>`
  + '<h2>Warnings</h2><p class="warning">Anyone who has had abdominal thrusts must be checked by a doctor afterwards.</p>';

export const cards: Card[] = [
  { slug: 'cpr-adult', title: 'CPR (adult)', icon: 'heart', order: 1, summary: 'Collapsed, unresponsive and not breathing normally.', html: cprHtml('Shout for help, a phone on speaker beside you — call 999.') },
  {
    slug: 'severe-bleeding', title: 'Severe bleeding', icon: 'drop', order: 2, summary: 'Blood that soaks through and does not stop.',
    html: '<h2>Steps</h2><ol><li>Press hard on the wound with a clean cloth or your hand, and keep pressing.</li>'
      + '<li>Call 999 and put the phone on speaker beside you.</li>'
      + '<li>Lay them down and raise the bleeding part above the heart if you can.</li>'
      + '<li>Keep pressing; do not lift the cloth to look, and add another on top if it soaks through.</li></ol>'
      + '<h2>Warnings</h2><p class="warning">A tourniquet is a last resort for a limb that will not stop bleeding. Write the time on it.</p>',
  },
  {
    slug: 'choking', title: 'Choking', icon: 'lungs', order: 3,
    html: chokingHtml('If they become unresponsive, start CPR, and call 999.'),
  },
];

/* The box resolves a card's `[[call 999]]` against the situation before it renders the Markdown, so
 * with both networks down the card that arrives is a different card: the step that says to ring
 * says who to send instead. The fixture has to do the same, or the calls-off screenshots photograph
 * a card telling a household to do the one thing the banner above it says will not work. */
const NO_PHONES = '999 will not connect while the phones are down: <a href="/p/no-phones">get help without phones</a>';
export const cardsNoPhones: Card[] = [
  { ...cards[0], html: cprHtml(`Shout for help, a phone on speaker beside you — ${NO_PHONES}.`) },
  {
    ...cards[1],
    html: cards[1].html.replace('Call 999 and put the phone on speaker beside you.', 'Send someone to a landline, a neighbour or a payphone: 999 will not connect from here.'),
  },
  { ...cards[2], html: chokingHtml(`If they become unresponsive, start CPR, and ${NO_PHONES}.`) },
];

/* The ten field craft pages. `/fieldcraft` renders whatever the box has in this category, and the
   fixture used to have none, so every field-craft screenshot was a title and one sentence. */
const FIELDCRAFT: [string, string, string, string][] = [
  ['shelter-and-warmth', 'Shelter and warmth', 'home', 'Staying dry and out of the wind, indoors and out.'],
  ['fire-and-fuel', 'Fire and fuel', 'fire', 'Lighting one, feeding it, and the law about where.'],
  ['finding-water', 'Finding water', 'drop', 'Where it is, and how to make it safe to drink.'],
  ['wild-food', 'Wild food', 'wheat', 'What is safe to eat in Britain and Ireland, and when.'],
  ['moving-about', 'Moving about', 'boot', 'On foot, by bike, and what a flooded road really costs.'],
  ['navigation', 'Finding your way', 'compass', 'Map, compass, the sun, and a grid reference.'],
  ['weather', 'Reading the weather', 'cloud', 'What the sky and the wind say about the next few hours.'],
  ['first-aid-outdoors', 'First aid outdoors', 'medical', 'Cold, heat, sprains and cuts, away from a hospital.'],
  ['animals-and-plants', 'Animals and plants', 'leaf', 'What bites, what stings, and what will make you ill.'],
  ['staying-put', 'Deciding to stay put', 'plan', 'The commonest right answer, and how to tell.'],
];

export const pages: Page[] = [
  ...FIELDCRAFT.map(([slug, title, icon, summary], i) => ({ slug, title, icon, order: i + 1, html: '', category: 'fieldcraft', summary })),
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
/** One field craft page in full, so the ten are photographed as a list and as a page. */
export const fieldcraftPage: Page = {
  slug: 'shelter-and-warmth', title: 'Shelter and warmth', icon: 'home', order: 1, category: 'fieldcraft',
  summary: 'Staying dry and out of the wind, indoors and out.',
  html: '<p>Warmth before food. A dry, still, insulated space keeps a person alive far longer than a meal does.</p><h2>Indoors, with no heating</h2><p>Pick one room, ideally south-facing with the fewest outside walls. Close the doors to the rest of the house. Put something over the windows at dusk and take it down at first light.</p><h2>Outdoors</h2><p>Get off the ground first: bracken, leaves, a rucksack, anything. The ground takes more heat than the air does.</p><table><tr><th>Layer</th><th>What it does</th></tr><tr><td>Next to the skin</td><td>Moves sweat away; never cotton</td></tr><tr><td>Middle</td><td>Traps still air: fleece, wool, down</td></tr><tr><td>Outside</td><td>Stops wind and rain</td></tr></table>',
};

export const householdPlan: Page = {
  slug: 'household-plan', title: 'Household plan', icon: 'plan', order: 1, category: 'plan',
  html: '<h2>Meeting points</h2><p>First: the front gate. Second: the church hall.</p><h2>Out-of-area contact</h2><p>Name and number.</p>',
};

export const mapConfig: MapConfig = {
  bases: [
    { id: 'osm', title: 'OpenStreetMap', styles: { field: '/maps/styles/osm-field.json', mono: '/maps/styles/osm-mono.json' }, available: true },
    { id: 'os', title: 'OS Open Zoomstack', styles: { field: '/maps/styles/os-field.json', mono: '/maps/styles/os-mono.json' }, available: true },
  ],
  terrain: { contours: '/maps/contours.pmtiles', hillshade: '/maps/hillshade.pmtiles' },
  overlays: [
    { id: 'health', title: 'Hospitals, pharmacies, GP surgeries', kind: 'geojson', layer_id: null, url: '/maps/overlays/health.geojson', default_on: false, scenarios_on: ['pandemic'], coverage: ['england', 'wales', 'scotland', 'ni', 'roi', 'iom', 'ci'], color: '#e53935', icon: 'medical', available: true, coverage_note: null },
    { id: 'footpaths', title: 'Footpaths and rights of way', kind: 'pmtiles', layer_id: null, url: '/maps/overlays/footpaths.pmtiles', default_on: true, scenarios_on: [], coverage: ['england', 'wales', 'scotland', 'ni', 'roi', 'iom', 'ci'], color: '#2e7d32', icon: null, available: true, coverage_note: null },
    { id: 'access-land', title: 'Open access land', kind: 'geojson', layer_id: null, url: '/maps/overlays/access-land.geojson', default_on: false, scenarios_on: [], coverage: ['england', 'wales'], color: '#f9a825', icon: null, available: true, coverage_note: null },
    { id: 'flood-zones', title: 'Flood zones', kind: 'pmtiles', layer_id: null, url: '/maps/overlays/flood-zones.pmtiles', default_on: false, scenarios_on: ['storms-flooding'], coverage: ['england', 'wales', 'scotland', 'ni'], color: '#1e88e5', icon: null, available: false, coverage_note: null },
    { id: 'contour-labels', title: 'Contour labels', kind: 'style-layer', layer_id: 'contour_label', url: null, default_on: false, scenarios_on: [], coverage: ['england', 'wales', 'scotland', 'ni', 'roi', 'iom', 'ci'], color: '#8d6e63', icon: null, available: true, coverage_note: null },
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
    { n: 2, title: 'Water', url: '/m/water', source: 'playbooks', text: 'Store 3 litres per person per day.' },
  ] } },
  { event: 'token', data: { text: 'Signs include ' } },
  { event: 'token', data: { text: 'dark urine [1], and stored water helps [2].' } },
  { event: 'done', data: { answer: 'Signs include dark yellow urine and dizziness [1], and stored water helps [2].', grounded: true, citations: [{ n: 1, title: 'Dehydration', url: '/read/nhs_uk/www.nhs.uk/conditions/dehydration/', source: 'nhs' }, { n: 2, title: 'Water', url: '/m/water', source: 'playbooks' }] } },
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
    { id: 'radio', title: 'Find the wind-up radio', bucket: 'today', why: 'A bulletin is the only news once the networks go.', link: 'page:what-still-works', person: null, done: true, done_at: '2026-09-06T13:00:00.000Z', source: 'rule:radio' },
  ],
  briefing: [
    { title: 'Right now', kind: 'playbook-section', ref: 'grid-collapse#right-now' },
    { title: 'Power', kind: 'module', ref: 'power' },
    { title: 'What still works in an outage', kind: 'page', ref: 'what-still-works' },
  ],
});

/* Phase 2 and 3 fixtures: the event log, the facilities round the home and the box's senses. */
export const events: Note[] = [
  { id: 44, kind: 'event', title: 'Mains power off since 13:00 (phone)', body: '', lat: null, lon: null, updated_at: '2026-09-06T13:02:00.000Z' },
  { id: 43, kind: 'event', title: 'Fill the bath ticked by Sam', body: '', lat: null, lon: null, updated_at: '2026-09-06T13:20:00.000Z' },
  { id: 42, kind: 'event', title: 'Drill started: National grid collapse', body: '', lat: null, lon: null, updated_at: '2026-09-06T12:00:00.000Z' },
];


export const nearby: NearbyResponse = {
  lat: 50.9379, lon: -1.4708,
  method: "Straight-line distance and bearing; walking time by Naismith's rule (5 km/h). Roads and paths will be longer.",
  facilities: [
    {
      id: 'pharmacy', title: 'Pharmacy', found: true, searched: ['health'], note: null,
      nearest: { name: 'Boots, High Street', lat: 50.9345, lon: -1.4331, distance_m: 620, bearing_deg: 92, compass: 'E', walk_minutes: 8, source: 'overlay:health', properties: { amenity: 'pharmacy', opening_hours: 'Mo-Sa 09:00-17:30' } },
      also: [
        { name: 'Shirley Pharmacy', lat: 50.9290, lon: -1.4460, distance_m: 1400, bearing_deg: 200, compass: 'SSW', walk_minutes: 17, source: 'overlay:health', properties: {} },
        /* OpenStreetMap carries plenty of pharmacies with no name on them, and "Unnamed" is not a place. */
        { name: '', lat: 50.9260, lon: -1.4400, distance_m: 1900, bearing_deg: 150, compass: 'SSE', walk_minutes: 23, source: 'overlay:health', properties: {} },
      ],
    },
    {
      id: 'emergency-department', title: 'Emergency department', found: true, searched: ['health'],
      note: 'These come from OpenStreetMap and include small hospitals with no A&E: ring ahead if the phones are up.',
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

/* Carrying the situation to another box. */

export const exportChunks: ExportChunks = {
  chunks: ['{"i":0,"n":2,"d":"H4sIAAAAAAACA61W247bIBD9FcRTq"}', '{"i":1,"n":2,"d":"8ar0iFOzA90K7V9aCv1oapWGHC"}'],
};

/* The shape `transfer.merge` answers with: one count per part it merged, the home, the scenario and
   the one setting as words, and a line for everything it actually moved. */
export const importSummary: ImportSummary = {
  ok: true, version: 1, exported_at: '2026-09-06T13:00:00Z',
  counts: {
    conditions: { updated: 2, kept: 8 },
    tasks: { updated: 1, kept: 3 },
    checklist: { updated: 0, kept: 2 },
    notes: { added: 1, skipped: 2 },
    events: { added: 3, skipped: 1 },
  },
  home: 'kept', scenario: 'started: grid-collapse', settings: 'set',
  changes: ['Mains power off from the other box', 'People set to 3 from the other box'],
};

export const sensors: Sensors = {
  internet: { value: 0, unit: 'up', at: '2026-09-06T13:58:00.000Z' },
  mains: { value: 0, unit: 'on', at: '2026-09-06T13:59:00.000Z' },
  temp_in: { value: 14.5, unit: '°C', at: '2026-09-06T13:57:00.000Z' },
  co_ppm: { value: 3, unit: 'ppm', at: '2026-09-06T13:30:00.000Z' },
};

export const kitsResponse: KitsResponse = {
  people: 2,
  kits: [
    { slug: 'water', title: 'Water', icon: 'water', order: 2, summary: 'Stored drinking water and the means to make more.', relevant: true,
      tiers: { basic: { done: 1, total: 2 }, serious: { done: 0, total: 1 }, full: { done: 0, total: 1 } } },
    { slug: 'baby-child', title: 'Baby and child', icon: 'baby', order: 11, summary: 'What a household with a baby needs on top of everything else.', relevant: true,
      tiers: { basic: { done: 0, total: 1 }, serious: { done: 0, total: 0 }, full: { done: 0, total: 0 } } },
  ],
};

export const kitWater: Kit = {
  slug: 'water', title: 'Water', icon: 'water', order: 2, summary: 'Stored drinking water and the means to make more.',
  intro_html: '<p>Three litres a person a day is the planning figure.</p>', sources: [{ title: 'Water module', kiwix: 'x/y', as_at: '2026-01' }],
  relevant: true, people: 2,
  tiers: [
    { id: 'basic', title: 'Three days', days: 3, why: "The government's own baseline.", done: 1, total: 2, items: [
      { id: 'stored-water', name: 'Drinking water in sealed containers', why: 'Bottled, or filled containers, rotated yearly ([Prepare](kiwix:prepare_uk/prepare)).', note: 'Rotate every year.',
        why_html: 'Bottled, or filled containers, rotated yearly (<a href="/read/prepare_uk/prepare">Prepare</a>).', note_html: 'Rotate every year.',
        link: 'module:water', href: '/m/water',
        qty: { amount: 3, unit: 'L', scaled: 18, text: '18 L for 2 people over 3 days' },
        checked: true, updated_at: '2026-09-06T10:00:00+00:00' },
      { id: 'containers', name: 'Containers with lids, 10 litres or more', why: '', note: '', why_html: '', note_html: '', link: 'module:water', href: '/m/water',
        qty: { amount: 2, unit: '', scaled: 4, text: '4 for 2 people' }, checked: false, updated_at: null },
    ] },
    { id: 'serious', title: 'Two weeks', days: 14, why: 'What every playbook on this box plans for.', done: 0, total: 1, items: [
      { id: 'tablets', name: 'Water purification tablets', why: 'One pack treats a fortnight of water.', note: '', why_html: 'One pack treats a fortnight of water.', note_html: '', link: null, href: null,
        qty: { amount: 1, unit: 'pack', scaled: 1, text: '1 pack' }, checked: false, updated_at: null },
    ] },
    { id: 'full', title: 'No help coming', days: 90, why: 'A season with no mains and no shops.', done: 0, total: 1, items: [
      { id: 'filter', name: 'Gravity filter with spare elements', why: 'x', note: '', why_html: 'x', note_html: '', link: null, href: null, qty: null, checked: false, updated_at: null },
    ] },
  ],
};
