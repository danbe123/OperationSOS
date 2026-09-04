import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act, within } from '@testing-library/react';
import { api } from '../../src/api/client';
import { StatusProvider } from '../../src/api/status';
import { StatusStrip } from '../../src/components/StatusStrip';
import { wifiQrPayload } from '../../src/kiosk/ConnectPanel';
import { status } from '../fixtures/api';

afterEach(() => vi.useRealTimers());

describe('StatusStrip', () => {
  it('shows SSID, both addresses, drive state and temperature, and polls /api/status every 10 s', async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, 'status').mockResolvedValue(status);
    render(<StatusProvider><StatusStrip /></StatusProvider>);
    await act(async () => {});
    expect(screen.getByText('SOS')).toBeInTheDocument();
    expect(screen.getByText('http://10.42.0.1')).toBeInTheDocument();
    expect(screen.getByText('http://sos.box')).toBeInTheDocument();
    expect(screen.getByText('External drive: not connected')).toBeInTheDocument();
    expect(screen.getByText('CPU 51°C')).toBeInTheDocument();
    expect(spy).toHaveBeenCalledTimes(1);
    await act(async () => { vi.advanceTimersByTime(10_000); });
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('shows the mounted drive with free space', async () => {
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, disks: { ...status.disks, extended: { mounted: true, path: '/srv/sos/extended', total_gb: 1863, free_gb: 900 } } });
    render(<StatusProvider><StatusStrip /></StatusProvider>);
    expect(await screen.findByText('External drive: 900 GB free')).toBeInTheDocument();
  });

  it('Connect a phone opens a full-screen panel with two 220 px QR codes and 32 px addresses', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(status);
    render(<StatusProvider><StatusStrip /></StatusProvider>);
    const button = await screen.findByRole('button', { name: 'Connect a phone' });
    await act(async () => { button.click(); });
    const dialog = screen.getByRole('dialog', { name: 'Connect a phone' });
    const imgs = await within(dialog).findAllByRole('img');
    expect(imgs).toHaveLength(2);
    expect(imgs[0]).toHaveAttribute('src', `data:image/png;base64,${btoa('WIFI:T:nopass;S:SOS;;')}`);
    expect(imgs[1]).toHaveAttribute('src', `data:image/png;base64,${btoa('http://10.42.0.1/')}`);
    expect(imgs[0]).toHaveAttribute('width', '220');
    expect(imgs[1]).toHaveAttribute('width', '220');
    expect(within(dialog).getByText('http://10.42.0.1/').closest('.connect-big')).not.toBeNull();
    expect(within(dialog).getByText('http://sos.box').closest('.connect-big')).not.toBeNull();
    expect(within(dialog).getByText('If the page will not load, turn mobile data off.')).toBeInTheDocument();
    await act(async () => { within(dialog).getByRole('button', { name: 'Close' }).click(); });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('escapes special characters in the WIFI payload', () => {
    expect(wifiQrPayload('My;Net')).toBe('WIFI:T:nopass;S:My\\;Net;;');
  });
});
