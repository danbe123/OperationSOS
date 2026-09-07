export type DiskInfo = { mounted: boolean; path: string; total_gb: number; free_gb: number };
export type AiState = 'off' | 'starting' | 'ready' | 'error' | 'off-thermal' | 'busy';
export type Status = {
  version: string; uptime_s: number; cpu_temp_c: number | null; load: number[];
  mem: { total_mb: number; used_mb: number };
  disks: { core: DiskInfo; extended: DiskInfo };
  hotspot: { ssid: string; ip: string; clients: number; enabled: boolean };
  eth_mode: 'client' | 'direct'; power_mode: 'normal' | 'low';
  ai: { state: AiState; model: string | null; message: string | null };
  thermal_ai_off_c: number; idle_minutes: number; home_minutes: number;
  pin_required: boolean; dev: boolean; default_theme: 'field' | 'mono';
  situation?: { slug: string; started_at: string } | null;
  conditions?: Record<ConditionId, ConditionState>;
  modes?: Modes;
  drill?: boolean;
  /** How many people the kits are scaled for: the one number the box is ever told (1 to 20). */
  people?: number;
};
export type LibraryItem = {
  id: string; title: string; kind: string; tier: 'core' | 'extended'; category: string;
  scenarios: string[]; size_bytes: number; as_at: string | null; licence: string | null;
  available: boolean;
  /** The app route the item opens at: `/doc/<id>` or `/read/<id>/<home>`. Never handed to a viewer. */
  url: string | null;
  /** Where the file itself is served: `/docs/core/<file>` or `/docs/extended/<file>`. Null for a ZIM,
   * and null on a box built before the field existed. The PDF and EPUB viewers load this. */
  file_url?: string | null;
  description: string | null; drive_label: string;   // "Core" | "External drive" | "On external drive (not connected)"
};
export type LibraryResponse = { categories: { id: string; title: string; items: LibraryItem[] }[] };
export type SearchResult = {
  source: string; badge: string; title: string; snippet: string; url: string; score: number;
  kind: 'article' | 'playbook' | 'module' | 'card' | 'page' | 'doc' | 'place' | 'item';
  lat?: number; lon?: number; page?: number;
};
export type SearchResponse = { q: string; query: string; results: SearchResult[]; groups: { source: string; badge: string; count: number }[]; took_ms: number; partial: boolean };
export type Suggestion = { value: string; label: string; url: string | null; source: string };
export type PlaybookSummary = { slug: string; title: string; icon: string; summary: string; order: number };
export type Section = { id: 'right-now' | 'first-72-hours' | 'first-month' | 'long-term' | 'uk-specifics' | 'go-deeper'; title: string; html: string };
export type ChecklistItem = { id: string; text: string; checked: boolean; updated_at: string | null };
export type Playbook = PlaybookSummary & {
  sections: Section[]; checklist: ChecklistItem[];
  modules: { slug: string; title: string; html: string }[];
  overlays: string[]; sources: { title: string; doc?: string; kiwix?: string; url?: string; as_at?: string }[];
  reviewed: string | null;
};
export type Card = { slug: string; title: string; icon: string; order: number; html: string; summary?: string };
export type Page = { slug: string; title: string; icon: string; order: number; html: string; category: string; summary?: string };
export type Overlay = {
  id: string; title: string; kind: 'geojson' | 'pmtiles' | 'style-layer'; layer_id: string | null; url: string | null;
  default_on: boolean; scenarios_on: string[]; coverage: string[]; color: string; icon: string | null; available: boolean;
};
export type MapConfig = {
  bases: { id: 'osm' | 'os'; title: string; styles: { field: string; mono: string }; available: boolean }[];
  terrain: { contours: string | null; hillshade: string | null };
  overlays: Overlay[];
  packs: { title: string; url: string; size_bytes: number }[]; packs_index_url: string | null;
};
export type Place = { name: string; kind: string; lat: number; lon: number; region: string; postcode: string | null };
export type Note = { id: number; kind: 'note' | 'pin' | 'event'; title: string; body: string; lat: number | null; lon: number | null; updated_at: string };
/** `GET/PUT /api/settings/people`: how many people the kits are scaled for, 1 to 20. */
export type PeopleSetting = { people: number };
export type SituationPhase = 'right-now' | 'first-72-hours' | 'first-month' | 'long-term';
export type Situation = { slug: string; title: string | null; started_at: string; elapsed_s: number; phase: SituationPhase } | { slug: null };
export type Passage = { n: number; title: string; url: string; source: string; text: string };
export type AiEvent =
  | { event: 'verbatim'; data: { title: string; url: string; paragraphs: string[]; as_at: string | null } }
  | { event: 'retrieving'; data: { query: string; passages: Passage[] } }
  | { event: 'token'; data: { text: string } }
  | { event: 'done'; data: { answer: string; grounded: boolean; citations: { n: number; title: string; url: string; source: string }[] } }
  | { event: 'error'; data: { code: 'busy' | 'timeout' | 'unavailable' | 'internal'; message: string; retry_after?: number } };
export type AiAskRequest = { question: string; history: { role: 'user' | 'assistant'; content: string }[] };
export type UpdateProgress = { running: boolean; lines: string[]; done: boolean; ok: boolean | null };

/* The situation engine (spec 2026-09-06). The View is one snapshot of the household's situation. */
export const CONDITION_IDS = ['power', 'water', 'mobile', 'landline', 'internet', 'gas', 'heating', 'roads', 'shops', 'sewage'] as const;
export type ConditionId = (typeof CONDITION_IDS)[number];
export type ConditionState = 'working' | 'degraded' | 'off';
export type ConditionSource = 'manual' | 'detected' | 'inferred';
export type Condition = {
  id: ConditionId; title: string; state: ConditionState; since: string | null; for_s: number;
  source: ConditionSource; confidence: number; note: string; set_by: string;
  updated_at: string; confirmed_at: string | null; stale: boolean;
};
export type Conditions = Record<ConditionId, Condition>;
export type ConditionPatch = { state: ConditionState; since?: string; note?: string; expected_updated_at?: string };
/** `detected` marks a proposal the box's own sensors raised, rather than one worked out from a rule. */
export type Inferred = { condition: ConditionId; state: ConditionState; confidence: number; due_at: string; why: string; rule: string; source: string; detected?: boolean };
export type Severity = 'info' | 'warn' | 'danger' | 'passed';
export type Forecast = { id: string; title: string; due_at: string; severity: Severity; why: string; link: string | null; passed: boolean; rule?: string };
export type TaskBucket = 'now' | 'hour' | 'today' | 'week';
export type Task = { id: string; title: string; bucket: TaskBucket; why: string; link: string | null; person: string | null; done: boolean; done_at: string | null; source: string };
/** An empty `person` clears the assignment; leaving a field out means "unchanged". */
export type TaskPatch = { done?: boolean; person?: string };
export type BriefingKind = 'playbook' | 'playbook-section' | 'module' | 'page' | 'card' | 'doc' | 'map' | 'kiwix';
export type BriefingItem = { title: string; kind: BriefingKind; ref: string; html?: string };
export type Modes = { theme: 'field' | 'mono' | null; dim: boolean; calls: 'shown' | 'hidden'; map_first: boolean; board: boolean };
export type Home = { lat: number | null; lon: number | null; label: string; flood_zone: string | null; nearby?: NearbySummary[] };

/* Phase 2 and 3: the nearest facilities, the box's own senses, and reading aloud. */
export const NEARBY_KINDS = ['emergency-department', 'pharmacy', 'gp', 'fuel', 'water-works', 'fire-station', 'rest-centre'] as const;
export type NearbyKind = (typeof NEARBY_KINDS)[number];
/** One place the box found, as `GET /api/nearby` returns it: how far, which way, how long on foot,
 * where the answer came from, and whatever OpenStreetMap tags were worth keeping. */
export type NearbyPlace = {
  name: string; lat: number; lon: number;
  distance_m: number; bearing_deg: number; compass: string; walk_minutes: number;
  source: string; properties: Record<string, string>;
};
/** One kind of facility. `found` is false when the box has no data for it here, and `why` says so. */
export type NearbyFacility = {
  id: string; title: string; found: boolean;
  nearest: NearbyPlace | null; also: NearbyPlace[];
  searched?: string[]; note?: string | null; why?: string;
};
export type NearbyResponse = { lat: number; lon: number; method: string; facilities: NearbyFacility[] };
/** The short form the View carries in `meta.home.nearby`: one line per facility that was found. */
export type NearbySummary = {
  id: string; title: string; name: string; lat: number; lon: number;
  distance_m: number; bearing_deg: number; compass: string; walk_minutes: number;
};
export type SensorReading = { value: number; unit: string; at: string };
/** Whatever the box can sense, by sensor id (`internet`, `mains`, `temp_in`, `co_ppm`, `broadcast`, ...). */
export type Sensors = Record<string, SensorReading | null>;
export type Recording = { file: string; station: string; at: string; url: string };
export type Bulletin = { station: string; frequency: string; at: string; note?: string };
export type SituationScenario = { slug: string; title: string; started_at: string; elapsed_s: number; phase: SituationPhase };
export type SituationView = {
  meta: { now: string; dark: boolean; sunrise: string | null; sunset: string | null; home: Home | null; drill: boolean };
  scenario: SituationScenario | null;
  conditions: Conditions;
  inferred: Inferred[];
  forecast: Forecast[];
  tasks: Task[];
  briefing: BriefingItem[];
  modes: Modes;
  bulletins: { next: Bulletin | null };
};
/** `GET /api/situation/export/qr`: the situation split into chunks of at most 800 characters. */
export type ExportChunks = { chunks: string[]; total?: number };
/** What `POST /api/situation/import` brought in, per kind of row. */
export type ImportCounts = Record<string, Record<string, number>>;
export type ImportSummary = {
  ok: boolean; version?: number; exported_at?: string;
  counts?: ImportCounts; home?: string; scenario?: string; changes?: string[];
};
export type DrillRequest = { scenario: string; conditions: Partial<Record<ConditionId, ConditionState>>; hours_ago?: number };

export type KitTierId = 'basic' | 'serious' | 'full';
export type KitSummary = {
  slug: string; title: string; icon: string; order: number; summary: string; relevant: boolean;
  tiers: Record<KitTierId, { done: number; total: number }>;
};
export type KitsResponse = { people: number; kits: KitSummary[] };
export type KitItem = {
  id: string; name: string; why: string; note: string; link: string | null; href: string | null;
  /** `why` and `note` as inline HTML (no paragraph wrapper), so their citations are links on the row. */
  why_html: string; note_html: string;
  qty: { amount: number; unit: string; scaled: number; text: string } | null;
  checked: boolean; updated_at: string | null;
};
export type KitTier = { id: KitTierId; title: string; days: number; why: string; done: number; total: number; items: KitItem[] };
export type Kit = {
  slug: string; title: string; icon: string; order: number; summary: string; intro_html: string;
  sources: { title: string; doc?: string; kiwix?: string; as_at?: string }[]; relevant: boolean; people: number; tiers: KitTier[];
};
