import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError, setToken, parseSse } from '../../src/api/client';
import type { AiEvent } from '../../src/api/types';
import { status, search, aiEvents, sseBody, condition, view } from '../fixtures/api';

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' }, ...init });
}
function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(enc.encode(chunk));
      controller.close();
    },
  });
}
async function collect(iter: AsyncIterable<AiEvent>): Promise<AiEvent[]> {
  const out: AiEvent[] = [];
  for await (const ev of iter) out.push(ev);
  return out;
}

const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  setToken(null);
});
afterEach(() => vi.unstubAllGlobals());

describe('api request helpers', () => {
  it('GETs /api/status and returns the parsed body', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(status));
    const s = await api.status();
    expect(s.hotspot.ssid).toBe('SOS');
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/status');
    expect(init.method).toBe('GET');
  });

  it('encodes search q, sources and limit', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(search));
    await api.search("st john's", { sources: ['nhs', 'wikipedia'], limit: 10 });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/search?q=st+john%27s&sources=nhs%2Cwikipedia&limit=10');
  });

  it('sends JSON bodies with the bearer token when one is set', async () => {
    setToken('tok123');
    fetchMock.mockResolvedValueOnce(jsonResponse(status));
    await api.powerMode('low');
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    expect(url).toBe('/api/system/power-mode');
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"mode":"low"}');
    expect(init.headers.Authorization).toBe('Bearer tok123');
    expect(init.headers['Content-Type']).toBe('application/json');
  });

  it('omits the Authorization header when no token is set', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(status));
    await api.status();
    const init = fetchMock.mock.calls[0][1] as { headers: Record<string, string> };
    expect(init.headers.Authorization).toBeUndefined();
  });

  it('throws ApiError carrying status and detail on a non-2xx response', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'wrong PIN' }, { status: 401 }));
    const err = await api.pin('0000').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 401, detail: 'wrong PIN' });
  });

  it('builds the checklist, notes and kiosk paths from the endpoint table', async () => {
    fetchMock.mockImplementation(async () => jsonResponse([]));
    await api.setChecklist('grid-collapse', 'fill-bath', true);
    await api.resetChecklist('grid-collapse');
    await api.notes('pin');
    await api.updateNote(7, { title: 'Well' });
    await api.deleteNote(7);
    await api.kioskBacklight(10);
    await api.settings({ idle_minutes: 7 });
    const calls = fetchMock.mock.calls.map((c) => [c[0], (c[1] as RequestInit).method, (c[1] as RequestInit).body]);
    expect(calls).toEqual([
      ['/api/playbooks/grid-collapse/checklist/fill-bath', 'PUT', '{"checked":true}'],
      ['/api/playbooks/grid-collapse/checklist', 'DELETE', undefined],
      ['/api/notes?kind=pin', 'GET', undefined],
      ['/api/notes/7', 'PUT', '{"title":"Well"}'],
      ['/api/notes/7', 'DELETE', undefined],
      ['/api/kiosk/backlight', 'POST', '{"level":10}'],
      ['/api/system/settings', 'POST', '{"idle_minutes":7}'],
    ]);
  });

  it('writes the one setting a household is ever asked for, and ticks a kit item', async () => {
    fetchMock.mockImplementation(async () => jsonResponse({ people: 3 }));
    await api.setPeople(3);
    await api.setKitItem('water', 'stored-water', { checked: true });
    const calls = fetchMock.mock.calls.map((c) => [c[0], (c[1] as RequestInit).method, (c[1] as RequestInit).body]);
    expect(calls).toEqual([
      ['/api/settings/people', 'PUT', '{"people":3}'],
      // A tick and nothing else: there is no cupboard to hand the item off into.
      ['/api/kits/water/items/stored-water', 'PUT', '{"checked":true}'],
    ]);
  });
});

describe('parseSse', () => {
  it('yields events split across chunk boundaries and ignores ": ping" comments', async () => {
    const text = sseBody(aiEvents);
    const chunks = [text.slice(0, 13), text.slice(13, 90), text.slice(90, 91), text.slice(91)];
    const events = await collect(parseSse(streamOf(chunks)));
    expect(events.map((e) => e.event)).toEqual(['verbatim', 'retrieving', 'token', 'token', 'done']);
    expect(events[4]).toEqual(aiEvents[4]);
  });

  it('accepts a frame whose data is a whole AiEvent object', async () => {
    const events = await collect(parseSse(streamOf(['data: {"event":"token","data":{"text":"x"}}\n\n'])));
    expect(events).toEqual([{ event: 'token', data: { text: 'x' } }]);
  });

  it('handles CRLF line endings and a final frame with no trailing blank line', async () => {
    const events = await collect(parseSse(streamOf(['event: token\r\ndata: {"text":"a"}\r\n\r\nevent: done\r\ndata: {"answer":"a","grounded":false,"citations":[]}'])));
    expect(events.map((e) => e.event)).toEqual(['token', 'done']);
  });
});

describe('askAi', () => {
  it('POSTs the request and streams the events', async () => {
    fetchMock.mockResolvedValueOnce(new Response(streamOf([sseBody(aiEvents.slice(2))]), { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
    const events = await collect(api.askAi({ question: 'q', history: [] }));
    expect(events.map((e) => e.event)).toEqual(['token', 'token', 'done']);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/ai/ask');
    expect(JSON.parse(String(init.body))).toEqual({ question: 'q', history: [] });
  });

  it('throws ApiError when the server refuses the stream', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'AI is off' }, { status: 503 }));
    await expect(collect(api.askAi({ question: 'q', history: [] }))).rejects.toMatchObject({ status: 503, detail: 'AI is off' });
  });
});

describe('the situation engine endpoints', () => {
  it('reads the View', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(view));
    const v = await api.situationView();
    expect(v.conditions.power.state).toBe('working');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/situation/view');
  });

  it('sends a condition with the row it was based on, and reports a conflict', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(condition('power', 'off')));
    await api.setCondition('power', { state: 'off', since: '2026-09-06T13:00:00.000Z', note: 'street dark', expected_updated_at: '2026-09-06T12:00:00.000Z' });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/conditions/power');
    expect(init.method).toBe('PUT');
    expect(JSON.parse(init.body as string)).toEqual({ state: 'off', since: '2026-09-06T13:00:00.000Z', note: 'street dark', expected_updated_at: '2026-09-06T12:00:00.000Z' });
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'stale write' }, { status: 409 }));
    await expect(api.setCondition('power', { state: 'off' })).rejects.toMatchObject({ status: 409 });
  });

  it('confirms and accepts', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(condition('power', 'off')));
    await api.confirmCondition('power');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/conditions/power/confirm');
    fetchMock.mockResolvedValueOnce(jsonResponse(condition('mobile', 'off')));
    await api.acceptInferred('mobile', 'power-off-mobile-off');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/conditions/mobile/accept');
    expect(JSON.parse((fetchMock.mock.calls[1][1] as RequestInit).body as string)).toEqual({ rule: 'power-off-mobile-off' });
  });

  it('encodes a checklist task id in the path', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await api.setTask('checklist:grid-collapse/fill-bath', { done: true });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/tasks/checklist%3Agrid-collapse%2Ffill-bath');
  });

  it('starts and ends a drill', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(view));
    await api.startDrill({ scenario: 'grid-collapse', conditions: { power: 'off' }, hours_ago: 2 });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/drill');
    expect(JSON.parse(init.body as string)).toEqual({ scenario: 'grid-collapse', conditions: { power: 'off' }, hours_ago: 2 });
    fetchMock.mockResolvedValueOnce(jsonResponse(view));
    await api.endDrill();
    expect((fetchMock.mock.calls[1][1] as RequestInit).method).toBe('DELETE');
  });
});
