import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError, setToken } from '../../src/api/client';
import { formatUptime } from '../../src/screens/System';
import { status, updateProgress } from '../fixtures/api';

afterEach(() => { vi.useRealTimers(); setToken(null); });

describe('formatUptime', () => {
  it('formats days, hours and minutes', () => {
    expect(formatUptime(65)).toBe('1 min');
    expect(formatUptime(3600 * 5 + 120)).toBe('5 h 2 min');
    expect(formatUptime(86400 * 2 + 3600)).toBe('2 days 1 h');
  });
});

describe('System', () => {
  it('shows the status error in place of the loading message when /api/status fails', async () => {
    vi.spyOn(api, 'status').mockRejectedValue(new Error('network down'));
    renderRoute('/system');
    expect(await screen.findByText('Box status unavailable: network down')).toBeInTheDocument();
    expect(screen.queryByText('Reading the box status…')).toBeNull();
  });

  it('shows status cards', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(status);
    renderRoute('/system');
    expect(await screen.findByText('0.1.0')).toBeInTheDocument();
    expect(screen.getByText('51°C')).toBeInTheDocument();
    // Load averages and megabytes are the box talking to itself.
    expect(screen.getByText('26% used')).toBeInTheDocument();
    expect(screen.queryByText(/Load 0\./)).toBeNull();
    expect(screen.getByText('260 of 465 GB free')).toBeInTheDocument();
    expect(screen.getByText('Not connected')).toBeInTheDocument();
    expect(screen.getByText('1 device')).toBeInTheDocument();
    expect(screen.getByText('PIN protection off')).toBeInTheDocument();
  });

  it('power mode, ethernet mode and hotspot settings post and apply the returned status', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(status);
    const power = vi.spyOn(api, 'powerMode').mockResolvedValue({ ...status, power_mode: 'low' });
    const eth = vi.spyOn(api, 'ethMode').mockResolvedValue({ ...status, eth_mode: 'direct' });
    const hotspot = vi.spyOn(api, 'hotspot').mockResolvedValue({ ...status, hotspot: { ...status.hotspot, ssid: 'SOS2' } });
    const user = userEvent.setup();
    renderRoute('/system');
    await user.click(await screen.findByRole('button', { name: 'Low power' }));
    expect(power).toHaveBeenCalledWith('low');
    expect(screen.getByRole('button', { name: 'Low power' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'Direct laptop link' }));
    expect(eth).toHaveBeenCalledWith('direct');
    expect(screen.getByRole('button', { name: 'Direct laptop link' })).toHaveAttribute('aria-pressed', 'true');
    const ssid = screen.getByLabelText('Network name (SSID)');
    await user.clear(ssid);
    await user.type(ssid, 'SOS2');
    await user.type(screen.getByLabelText('Passphrase (blank for an open network)'), 'letmein12');
    await user.click(screen.getByRole('button', { name: 'Save hotspot' }));
    expect(hotspot).toHaveBeenCalledWith({ ssid: 'SOS2', passphrase: 'letmein12' });
    expect(await screen.findByDisplayValue('SOS2')).toBeInTheDocument();
  });

  it('gated calls open the PIN pad on 401 and retry with the token', async () => {
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, pin_required: true });
    const eth = vi.spyOn(api, 'ethMode').mockRejectedValueOnce(new ApiError(401, 'PIN required')).mockResolvedValueOnce({ ...status, pin_required: true, eth_mode: 'direct' });
    vi.spyOn(api, 'pin').mockResolvedValue({ token: 'tok', expires_in: 600 });
    const user = userEvent.setup();
    renderRoute('/system');
    expect(await screen.findByText('PIN protection on')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Direct laptop link' }));
    await user.type(await screen.findByLabelText('PIN'), '1234{Enter}');
    await act(async () => {});
    expect(eth).toHaveBeenCalledTimes(2);
    expect(screen.getByRole('button', { name: 'Direct laptop link' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('AI card: enable, disable, and the off-thermal message', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(status);
    const enable = vi.spyOn(api, 'aiEnable').mockResolvedValue({ state: 'starting' });
    const user = userEvent.setup();
    const a = renderRoute('/system');
    await user.click(await screen.findByRole('button', { name: 'Turn AI on' }));
    expect(enable).toHaveBeenCalled();
    expect(await screen.findByText('starting')).toBeInTheDocument();
    a.unmount();

    vi.spyOn(api, 'status').mockResolvedValue({ ...status, ai: { state: 'off-thermal', model: 'gemma-4-E2B-it-Q4_K_M.gguf', message: 'Stopped at 81°C' } });
    renderRoute('/system');
    expect(await screen.findByText('Stopped at 81°C')).toBeInTheDocument();
    expect(screen.getByText(/switched off because the box got too hot/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Turn AI on' })).toBeInTheDocument();
  });

  it('settings form posts thresholds, minutes and the default theme', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(status);
    const settings = vi.spyOn(api, 'settings').mockResolvedValue({ ...status, idle_minutes: 7, default_theme: 'mono' });
    const user = userEvent.setup();
    renderRoute('/system');
    const idle = await screen.findByLabelText('Dim after (minutes)');
    await user.clear(idle);
    await user.type(idle, '7');
    await user.selectOptions(screen.getByLabelText('Default theme'), 'mono');
    await user.click(screen.getByRole('button', { name: 'Save settings' }));
    expect(settings).toHaveBeenCalledWith({ thermal_ai_off_c: 80, idle_minutes: 7, home_minutes: 30, default_theme: 'mono' });
  });

  it('backlight slider posts the level (debounced) and explains a 501', async () => {
    vi.useFakeTimers();
    vi.spyOn(api, 'status').mockResolvedValue(status);
    const backlight = vi.spyOn(api, 'systemBacklight').mockRejectedValue(new ApiError(501, 'no backlight'));
    renderRoute('/system');
    await act(async () => {});
    const slider = screen.getByLabelText('Screen brightness');
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(slider, '40');
      slider.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => { vi.advanceTimersByTime(300); });
    expect(backlight).toHaveBeenCalledWith(40);
    expect(screen.getByText('No backlight control on this display')).toBeInTheDocument();
  });

  it('update starts, polls progress and reports the result', async () => {
    // shouldAdvanceTime: true — plain vi.useFakeTimers() hangs userEvent's click simulation in
    // this environment (see tests/screens/map.test.tsx for the same workaround).
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(api, 'status').mockResolvedValue(status);
    const start = vi.spyOn(api, 'update').mockResolvedValue({ started: true });
    const poll = vi.spyOn(api, 'updateProgress')
      .mockRejectedValueOnce(new Error('Connection interrupted'))
      .mockResolvedValueOnce(updateProgress)
      .mockResolvedValue({ running: false, lines: [...updateProgress.lines, 'Done'], done: true, ok: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderRoute('/system');
    await act(async () => {});
    await user.click(screen.getByRole('button', { name: 'Start update' }));
    expect(start).toHaveBeenCalledWith(['core']);
    // Flushes the passive effect that schedules the poll timeout; without it the timeout isn't
    // registered yet when we advance fake time below.
    await act(async () => {});
    await act(async () => { vi.advanceTimersByTime(2000); });
    expect(screen.getByText(/Update progress unavailable: Connection interrupted/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start update' })).toBeDisabled();
    await act(async () => { vi.advanceTimersByTime(2000); });
    expect(screen.getByText('Downloading 12%')).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(2000); });
    expect(screen.getByText('Update finished')).toBeInTheDocument();
    expect(within(screen.getByRole('log')).getByText('Done')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start update' })).toBeEnabled();
    await act(async () => { vi.advanceTimersByTime(6000); });
    expect(poll).toHaveBeenCalledTimes(3);
  });
});
