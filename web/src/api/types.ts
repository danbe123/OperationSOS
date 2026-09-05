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
  pin_required: boolean; dev: boolean; default_theme: 'vault' | 'field' | 'blackout';
  situation?: { slug: string; started_at: string } | null;
  conditions?: Record<ConditionId, ConditionState>;
  modes?: Modes;
  drill?: boolean;
  readiness_score?: number;
};
export type LibraryItem = {
  id: string; title: string; kind: string; tier: 'core' | 'extended'; category: string;
  scenarios: string[]; size_bytes: number; as_at: string | null; licence: string | null;
  available: boolean; url: string | null; description: string | null; drive_label: string;   // "Core" | "External drive" | "On external drive (not connected)"
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
export type Card = { slug: string; title: string; icon: string; order: number; html: string };
export type Page = { slug: string; title: string; icon: string; order: number; html: string; category: string; summary?: string };
export type Overlay = {
  id: string; title: string; kind: 'geojson' | 'pmtiles' | 'style-layer'; layer_id: string | null; url: string | null;
  default_on: boolean; scenarios_on: string[]; coverage: string[]; color: string; icon: string | null; available: boolean;
};
export type MapConfig = {
  bases: { id: 'osm' | 'os'; title: string; styles: { vault: string; field: string; blackout: string }; available: boolean }[];
  terrain: { contours: string | null; hillshade: string | null };
  overlays: Overlay[];
  packs: { title: string; url: string; size_bytes: number }[]; packs_index_url: string | null;
};
export type Place = { name: string; kind: string; lat: number; lon: number; region: string; postcode: string | null };
export type Note = { id: number; kind: 'note' | 'pin' | 'event'; title: string; body: string; lat: number | null; lon: number | null; updated_at: string };
export type Person = { id: number; name: string; age: number | null; needs: string; medications: string; contacts: string; updated_at: string };
export type StockCategory = 'water' | 'food' | 'fuel' | 'medicine' | 'other';
export type StockItem = {
  id: number; name: string; category: StockCategory; quantity: number; unit: string; per_person_day: number | null;
  expires: string | null; notes: string; updated_at: string; days_left: number | null;
};
export type StockResponse = { people: number; items: StockItem[] };
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
export type Inferred = { condition: ConditionId; state: ConditionState; confidence: number; due_at: string; why: string; rule: string; source: string };
export type Severity = 'info' | 'warn' | 'danger' | 'passed';
export type Forecast = { id: string; title: string; due_at: string; severity: Severity; why: string; link: string | null; passed: boolean; rule?: string };
export type TaskBucket = 'now' | 'hour' | 'today' | 'week';
export type Task = { id: string; title: string; bucket: TaskBucket; why: string; link: string | null; person: string | null; done: boolean; done_at: string | null; source: string };
/** An empty `person` clears the assignment; leaving a field out means "unchanged". */
export type TaskPatch = { done?: boolean; person?: string };
export type BriefingKind = 'playbook' | 'playbook-section' | 'module' | 'page' | 'card' | 'doc' | 'map' | 'kiwix';
export type BriefingItem = { title: string; kind: BriefingKind; ref: string; html?: string };
export type Modes = { theme: 'vault' | 'field' | 'blackout' | null; dim: boolean; calls: 'shown' | 'hidden'; map_first: boolean; board: boolean };
export type Home = { lat: number | null; lon: number | null; label: string; flood_zone: string | null };
export type ReadinessGap = { title: string; link: string; points: number };
export type Readiness = { score: number; gaps: ReadinessGap[] };
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
  readiness: Readiness;
  bulletins: { next: Bulletin | null };
};
export type DrillRequest = { scenario: string; conditions: Partial<Record<ConditionId, ConditionState>>; hours_ago?: number };
