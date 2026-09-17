import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { resetSpeech } from '../../src/tools/speech';
import { page as pmrPage, pages, powerOffView } from '../fixtures/api';

/** jsdom has no media stack: play resolves and the clip "ends" at once. */
beforeEach(() => {
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(function play(this: HTMLMediaElement) {
    setTimeout(() => this.dispatchEvent(new Event('ended')), 0);
    return Promise.resolve();
  });
  globalThis.URL.createObjectURL = () => 'blob:speech';
  globalThis.URL.revokeObjectURL = () => {};
});
afterEach(() => { resetSpeech(); sessionStorage.clear(); });

function mockPage() {
  vi.spyOn(api, 'pages').mockResolvedValue(pages);
  vi.spyOn(api, 'page').mockResolvedValue({ ...pmrPage, html: '<h2>PMR446</h2><p>Channel 3 is the calling channel.</p>' });
  vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
}

describe('Read aloud', () => {
  it('sends the visible text to the box in chunks and offers a stop while it reads', async () => {
    mockPage();
    let release: (b: Blob) => void = () => {};
    const speak = vi.spyOn(api, 'speak').mockImplementation(() => new Promise<Blob>((resolve) => { release = resolve; }));
    const user = userEvent.setup();
    renderRoute('/p/pmr446');
    await user.click(await screen.findByRole('button', { name: 'Read aloud' }));
    expect(speak).toHaveBeenCalledWith('PMR446 Channel 3 is the calling channel.', expect.anything());
    const stop = await screen.findByRole('button', { name: 'Stop reading' });
    await user.click(stop);
    await act(async () => { release(new Blob(['x'])); });
    expect(await screen.findByRole('button', { name: 'Read aloud' })).toBeInTheDocument();
  });

  it.each([[503, 'Piper is not installed'], [404, 'Not Found']])('takes every read-aloud button away when the box answers %i', async (status, detail) => {
    mockPage();
    vi.spyOn(api, 'speak').mockRejectedValue(new ApiError(status, detail));
    const user = userEvent.setup();
    renderRoute('/p/pmr446');
    await user.click(await screen.findByRole('button', { name: 'Read aloud' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Read aloud' })).toBeNull());
    expect(screen.getByText(/no voice installed/)).toBeInTheDocument();
  });

  it('reads the briefing on the situation sheet', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue([]);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    const speak = vi.spyOn(api, 'speak').mockResolvedValue(new Blob(['x']));
    const user = userEvent.setup();
    renderRoute('/situation');
    await user.click(await screen.findByRole('button', { name: 'Read aloud' }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    const spoken = speak.mock.calls.map((c) => c[0]).join(' ');
    expect(spoken).toContain('Freezer food unsafe');
    expect(spoken).toContain('Fill the bath and every container');
    expect(spoken).not.toContain('Read aloud');
  });
});
