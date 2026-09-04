import type {
  AiAskRequest, AiEvent, AiState, Card, ChecklistItem, LibraryItem, LibraryResponse, MapConfig, Note, Overlay, Page,
  Place, Playbook, PlaybookSummary, SearchResponse, Status, Suggestion, UpdateProgress,
} from './types';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

let token: string | null = null;
export function setToken(t: string | null): void {
  token = t;
}
export function getToken(): string | null {
  return token;
}

function headers(json: boolean, accept = 'application/json'): Record<string, string> {
  const h: Record<string, string> = { Accept: accept };
  if (json) h['Content-Type'] = 'application/json';
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function readDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // not JSON
  }
  return res.statusText || `HTTP ${res.status}`;
}

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE';

async function request<T>(method: Method, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: headers(body !== undefined),
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new ApiError(res.status, await readDetail(res));
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}

const enc = encodeURIComponent;

function parseFrame(frame: string): AiEvent | null {
  let event = '';
  const data: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith(':')) continue; // comment, e.g. ": ping"
    const colon = line.indexOf(':');
    const field = colon === -1 ? line : line.slice(0, colon);
    const value = colon === -1 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'event') event = value;
    else if (field === 'data') data.push(value);
  }
  if (data.length === 0) return null;
  const parsed: unknown = JSON.parse(data.join('\n'));
  if (event) return { event, data: parsed } as AiEvent;
  if (parsed && typeof parsed === 'object' && 'event' in parsed && 'data' in parsed) return parsed as AiEvent;
  return null;
}

/** Parse a text/event-stream body into AiEvent objects. Frames are separated by a blank line; CRLF is accepted. */
export async function* parseSse(body: ReadableStream<Uint8Array>): AsyncGenerator<AiEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let work = buffer.replace(/\r\n/g, '\n');
    let carry = '';
    if (!done && work.endsWith('\r')) {
      carry = '\r';
      work = work.slice(0, -1);
    }
    let sep: number;
    while ((sep = work.indexOf('\n\n')) !== -1) {
      const frame = work.slice(0, sep);
      work = work.slice(sep + 2);
      const ev = parseFrame(frame);
      if (ev) yield ev;
    }
    buffer = work + carry;
    if (done) break;
  }
  if (buffer.trim()) {
    const ev = parseFrame(buffer);
    if (ev) yield ev;
  }
}

export type SettingsPatch = { default_theme?: Status['default_theme']; thermal_ai_off_c?: number; idle_minutes?: number; home_minutes?: number };

export const api = {
  status: (signal?: AbortSignal) => request<Status>('GET', '/status', undefined, signal),
  library: () => request<LibraryResponse>('GET', '/library'),
  libraryItem: (id: string) => request<LibraryItem>('GET', `/library/${enc(id)}`),
  search: (q: string, opts: { sources?: string[]; limit?: number; signal?: AbortSignal } = {}) =>
    request<SearchResponse>('GET', `/search${qs({ q, sources: opts.sources?.join(','), limit: opts.limit })}`, undefined, opts.signal),
  suggest: (q: string, signal?: AbortSignal) => request<Suggestion[]>('GET', `/suggest${qs({ q })}`, undefined, signal),
  playbooks: () => request<PlaybookSummary[]>('GET', '/playbooks'),
  playbook: (slug: string) => request<Playbook>('GET', `/playbooks/${enc(slug)}`),
  setChecklist: (slug: string, itemId: string, checked: boolean) =>
    request<ChecklistItem[]>('PUT', `/playbooks/${enc(slug)}/checklist/${enc(itemId)}`, { checked }),
  resetChecklist: (slug: string) => request<ChecklistItem[]>('DELETE', `/playbooks/${enc(slug)}/checklist`),
  module: (slug: string) => request<{ slug: string; title: string; html: string }>('GET', `/modules/${enc(slug)}`),
  cards: () => request<Card[]>('GET', '/cards'),
  card: (slug: string) => request<Card>('GET', `/cards/${enc(slug)}`),
  pages: () => request<Page[]>('GET', '/pages'),
  page: (slug: string) => request<Page>('GET', `/pages/${enc(slug)}`),
  mapConfig: () => request<MapConfig>('GET', '/map/config'),
  mapOverlays: () => request<Overlay[]>('GET', '/map/overlays'),
  places: (q: string, limit?: number, signal?: AbortSignal) => request<Place[]>('GET', `/places${qs({ q, limit })}`, undefined, signal),
  notes: (kind?: 'note' | 'pin') => request<Note[]>('GET', `/notes${qs({ kind })}`),
  createNote: (note: Partial<Note>) => request<Note>('POST', '/notes', note),
  updateNote: (id: number, note: Partial<Note>) => request<Note>('PUT', `/notes/${id}`, note),
  deleteNote: (id: number) => request<{ ok: true }>('DELETE', `/notes/${id}`),
  aiStatus: () => request<{ state: AiState; model: string | null; message: string | null }>('GET', '/ai/status'),
  aiEnable: () => request<{ state: AiState }>('POST', '/ai/enable', {}),
  aiDisable: () => request<{ state: AiState }>('POST', '/ai/disable', {}),
  kioskBacklight: (level: number) => request<{ level: number }>('POST', '/kiosk/backlight', { level }),
  kioskIdle: (state: 'idle' | 'active') => request<{ ok: true }>('POST', '/kiosk/idle', { state }),
  systemBacklight: (level: number) => request<{ level: number }>('POST', '/system/backlight', { level }),
  powerMode: (mode: 'normal' | 'low') => request<Status>('POST', '/system/power-mode', { mode }),
  ethMode: (mode: 'client' | 'direct') => request<Status>('POST', '/system/eth-mode', { mode }),
  hotspot: (body: { ssid: string; passphrase?: string }) => request<Status>('POST', '/system/hotspot', body),
  settings: (patch: SettingsPatch) => request<Status>('POST', '/system/settings', patch),
  rescan: () => request<{ items: number; available: number }>('POST', '/system/rescan', {}),
  update: (tiers: ('core' | 'extended')[]) => request<{ started: true }>('POST', '/system/update', { tiers }),
  updateProgress: () => request<UpdateProgress>('GET', '/system/update/progress'),
  pin: (pin: string) => request<{ token: string; expires_in: number }>('POST', '/system/pin', { pin }),
  changePin: (pin: string) => request<{ ok: true }>('POST', '/system/pin/change', { pin }),
  async *askAi(req: AiAskRequest, signal?: AbortSignal): AsyncGenerator<AiEvent> {
    const res = await fetch('/api/ai/ask', {
      method: 'POST',
      headers: headers(true, 'text/event-stream'),
      body: JSON.stringify(req),
      signal,
    });
    if (!res.ok) throw new ApiError(res.status, await readDetail(res));
    if (!res.body) throw new ApiError(0, 'No response body');
    yield* parseSse(res.body);
  },
};

export type Api = typeof api;
