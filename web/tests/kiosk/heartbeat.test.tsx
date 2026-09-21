import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act } from '@testing-library/react';
import { KioskProvider } from '../../src/kiosk/KioskProvider';
import { HEARTBEAT_MS } from '../../src/kiosk/Heartbeat';

const fetchMock = vi.fn();
const beats = () => fetchMock.mock.calls.filter(([url]) => url === '/api/kiosk/alive');

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(new Response('{"ok":true}', { status: 200 }));
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe('the kiosk page heartbeat', () => {
  it('posts at once and every 30 s on the kiosk, with keepalive and nothing in the body', async () => {
    render(<KioskProvider force><p>page</p></KioskProvider>);
    await act(async () => {});
    expect(beats()).toHaveLength(1);
    const [, init] = beats()[0] as [string, RequestInit];
    expect(init).toMatchObject({ method: 'POST', keepalive: true });
    expect(init.body).toBeUndefined();
    expect(HEARTBEAT_MS).toBe(30_000);
    await act(async () => { await vi.advanceTimersByTimeAsync(HEARTBEAT_MS); });
    expect(beats()).toHaveLength(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 2); });
    expect(beats()).toHaveLength(4);
  });

  it('is silent on a phone', async () => {
    render(<KioskProvider force={false}><p>page</p></KioskProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 4); });
    expect(beats()).toHaveLength(0);
  });

  it('carries on when the box does not answer, and stops when the page goes', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const { unmount } = render(<KioskProvider force><p>page</p></KioskProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 2); });
    expect(beats()).toHaveLength(3);   // a failed beat is just a failed beat: the next one is still sent
    unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 3); });
    expect(beats()).toHaveLength(3);
  });
});
