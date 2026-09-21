import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  PROBE_DELAYS_MS, isConnectionError, isDown, onReconnect, reportFailure, reportSuccess, resetConnectionForTests,
} from '../../src/api/connection';
import { ApiError, api } from '../../src/api/client';

const fetchMock = vi.fn();
function ok(body: unknown = {}) { return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }); }
function gateway(status = 502) { return new Response('', { status }); }

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  resetConnectionForTests();
});
afterEach(() => {
  resetConnectionForTests();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('what counts as the box not answering', () => {
  it('is a network failure or a gateway error, never the API saying no', () => {
    expect(isConnectionError(new ApiError(0, 'x'))).toBe(true);
    expect(isConnectionError(new ApiError(502, 'x', true))).toBe(true);
    expect(isConnectionError(new ApiError(503, 'x', true))).toBe(true);
    expect(isConnectionError(new ApiError(504, 'x', true))).toBe(true);
    expect(isConnectionError(new ApiError(503, 'the API said so'))).toBe(false);
    expect(isConnectionError(new ApiError(404, 'x'))).toBe(false);
    expect(isConnectionError(new ApiError(500, 'x'))).toBe(false);
    expect(isConnectionError(new Error('x'))).toBe(false);
  });

  it('a request that cannot reach the box becomes an ApiError with status 0', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(api.status()).rejects.toMatchObject({ status: 0, detail: 'The box is not answering' });
    expect(isDown()).toBe(true);
  });

  it("the API's own 503 (Piper not installed) is an answer, so the box is not 'down'", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: 'Piper is not installed' }), { status: 503, headers: { 'Content-Type': 'application/json' } }));
    await expect(api.status()).rejects.toMatchObject({ status: 503, detail: 'Piper is not installed' });
    expect(isDown()).toBe(false);
  });

  it("Caddy's empty 502 while sos-api restarts is the box not answering", async () => {
    fetchMock.mockResolvedValue(gateway(502));
    await expect(api.status()).rejects.toMatchObject({ status: 502 });
    expect(isDown()).toBe(true);
  });

  it('an answer from the API of any kind ends the outage', async () => {
    reportFailure(new ApiError(0, 'x'));
    expect(isDown()).toBe(true);
    fetchMock.mockResolvedValue(ok({ hotspot: {} }));
    await api.status();
    expect(isDown()).toBe(false);
  });
});

describe('getting back', () => {
  it('probes with a growing pause, never in a tight loop, and tells everybody once when the box answers', async () => {
    const back = vi.fn();
    onReconnect(back);
    fetchMock.mockResolvedValue(gateway(502));
    reportFailure(new ApiError(0, 'x'));
    const minute = 60_000;
    await vi.advanceTimersByTimeAsync(minute);
    const probes = fetchMock.mock.calls.length;
    expect(probes).toBeGreaterThanOrEqual(4);
    expect(probes).toBeLessThanOrEqual(8);   // a minute of an outage is a handful of probes, not hundreds
    expect(PROBE_DELAYS_MS[0]).toBeGreaterThanOrEqual(500);
    expect(PROBE_DELAYS_MS.at(-1)).toBeGreaterThanOrEqual(10_000);
    expect(back).not.toHaveBeenCalled();

    fetchMock.mockResolvedValue(ok({}));
    await vi.advanceTimersByTimeAsync(20_000);
    expect(back).toHaveBeenCalledTimes(1);
    expect(isDown()).toBe(false);
    const after = fetchMock.mock.calls.length;
    await vi.advanceTimersByTimeAsync(minute);
    expect(fetchMock.mock.calls.length).toBe(after);   // it stops asking once the box has answered
  });

  it('asks again at once when the window comes back to the front', async () => {
    fetchMock.mockResolvedValue(gateway(502));
    reportFailure(new ApiError(0, 'x'));
    await vi.advanceTimersByTimeAsync(100);
    const before = fetchMock.mock.calls.length;
    window.dispatchEvent(new Event('focus'));
    await vi.advanceTimersByTimeAsync(10);
    expect(fetchMock.mock.calls.length).toBe(before + 1);
  });

  it('a listener that stops listening is not called', async () => {
    const back = vi.fn();
    const off = onReconnect(back);
    off();
    reportFailure(new ApiError(0, 'x'));
    reportSuccess();
    expect(back).not.toHaveBeenCalled();
  });
});

describe('writes are retried while the box restarts, and reported when it does not come back', () => {
  it('retries a PUT across a short outage and succeeds without the caller noticing', async () => {
    fetchMock
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValue(ok([]));
    const done = api.setChecklist('grid-collapse', 'cooker-off', true);
    await vi.advanceTimersByTimeAsync(10_000);
    await expect(done).resolves.toEqual([]);
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/checklist/')).length).toBe(3);
  });

  it('gives up after a bounded time with an error that says nothing was saved', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const done = api.setChecklist('grid-collapse', 'cooker-off', true).catch((e: ApiError) => e);
    await vi.advanceTimersByTimeAsync(30_000);
    const err = await done;
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(0);
    expect((err as ApiError).detail).toMatch(/nothing was saved/i);
    const puts = fetchMock.mock.calls.filter(([url]) => String(url).includes('/checklist/')).length;
    expect(puts).toBeGreaterThan(1);
    expect(puts).toBeLessThanOrEqual(6);
  });

  it('retries the creation of a note (the API was not reached), but not other POSTs', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValue(ok({ id: 1 }));
    const created = api.createNote({ kind: 'note', title: 't', body: 'b' });
    await vi.advanceTimersByTimeAsync(5_000);
    await expect(created).resolves.toEqual({ id: 1 });
    fetchMock.mockReset();
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const started = api.startSituation('grid-collapse').catch((e: ApiError) => e);
    await vi.advanceTimersByTimeAsync(30_000);
    expect(await started).toBeInstanceOf(ApiError);
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === '/api/situation').length).toBe(1);
  });

  it('does not retry an answer of no, such as a stale condition (409) or a bad request', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: 'stale' }), { status: 409, headers: { 'Content-Type': 'application/json' } }));
    await expect(api.setChecklist('a', 'b', true)).rejects.toMatchObject({ status: 409 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('a GET is not retried by the client: the query layer refetches when the box is back', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(api.playbooks()).rejects.toMatchObject({ status: 0 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
