import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError, setToken, parseSse } from '../../src/api/client';
import type { AiEvent } from '../../src/api/types';
import { status, search, aiEvents, sseBody } from '../fixtures/api';

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
