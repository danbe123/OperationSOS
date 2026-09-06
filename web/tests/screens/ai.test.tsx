import { describe, it, expect, vi } from 'vitest';
import { screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { AiAskRequest, AiEvent } from '../../src/api/types';
import { MAX_QUESTION, WARNING_LINE } from '../../src/screens/Ai';
import { status, aiEvents } from '../fixtures/api';

const ready = { ...status, ai: { state: 'ready' as const, model: 'gemma-4-E2B-it-Q4_K_M.gguf', message: null } };

/** An askAi mock that yields the given events, pausing before each one until `step()` is called. */
function gatedAsk(events: AiEvent[]) {
  const gates: (() => void)[] = [];
  const requests: AiAskRequest[] = [];
  const spy = vi.spyOn(api, 'askAi').mockImplementation(async function* (req) {
    requests.push(req);
    for (const ev of events) {
      await new Promise<void>((resolve) => gates.push(resolve));
      yield ev;
    }
  });
  const step = async () => { await act(async () => { gates.shift()?.(); await Promise.resolve(); }); };
  return { spy, step, requests };
}

describe('Ai screen', () => {
  it('shows the status error in place of the loading message when /api/status fails', async () => {
    vi.spyOn(api, 'status').mockRejectedValue(new Error('network down'));
    renderRoute('/ai');
    expect(await screen.findByText('Box status unavailable: network down')).toBeInTheDocument();
    expect(screen.queryByText('Checking the box…')).toBeNull();
  });

  it('aborts the in-flight askAi stream when the screen unmounts, and does not patch turn state afterwards', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(ready);
    let capturedSignal: AbortSignal | undefined;
    const spy = vi.spyOn(api, 'askAi').mockImplementation(async function* (_req, signal) {
      capturedSignal = signal;
      // Waits until the signal aborts and rejects, mirroring a real fetch's body read once its
      // AbortController fires, rather than resolving or yielding anything on its own.
      await new Promise<void>((_resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
      });
      yield { event: 'retrieving', data: { query: 'q', passages: [] } };
    });
    const user = userEvent.setup();
    const view = renderRoute('/ai');
    const input = await screen.findByLabelText('Your question');
    await user.type(input, 'signs of dehydration{Enter}');
    expect(spy).toHaveBeenCalledTimes(1);
    expect(capturedSignal?.aborted).toBe(false);

    view.unmount();
    expect(capturedSignal?.aborted).toBe(true);

    // Let the generator's rejection (triggered by the abort listener above) propagate through the
    // component's catch block; this must not throw or touch an unmounted component's state.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
  });

  it('shows an explanatory card when the AI is not ready', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(status);
    const a = renderRoute('/ai');
    expect(await screen.findByText(/The assistant is off/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Turn it on in System/ })).toHaveAttribute('href', '/system');
    a.unmount();
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, ai: { state: 'off-thermal', model: null, message: 'Stopped at 81°C' } });
    renderRoute('/ai');
    expect(await screen.findByText(/too hot/)).toBeInTheDocument();
    expect(screen.getByText('Stopped at 81°C')).toBeInTheDocument();
  });

  it('streams an answer: verbatim block first, progress phases, tokens, then the final answer with citations', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(ready);
    const { step } = gatedAsk(aiEvents);
    const user = userEvent.setup();
    renderRoute('/ai');
    const input = await screen.findByLabelText('Your question');
    expect(input).toHaveAttribute('maxlength', String(MAX_QUESTION));
    expect(screen.getByText(WARNING_LINE)).toBeInTheDocument();
    await user.type(input, 'signs of dehydration{Enter}');
    expect(screen.getByText('Searching the library…')).toBeInTheDocument();
    await step(); // verbatim
    const verbatim = screen.getByRole('region', { name: 'From the library, word for word' });
    expect(within(verbatim).getByRole('link', { name: 'Dehydration' })).toHaveAttribute('href', '/read/nhs_uk/www.nhs.uk/conditions/dehydration/');
    expect(within(verbatim).getByText(/Drink fluids/)).toBeInTheDocument();
    await step(); // retrieving
    expect(screen.getByRole('progressbar', { name: /Reading 2 passages and processing the prompt/ })).toBeInTheDocument();
    await step(); // token 1
    expect(screen.getByRole('progressbar', { name: 'Answering' })).toBeInTheDocument();
    expect(screen.getByText('Signs include')).toBeInTheDocument();
    await step(); // token 2
    expect(screen.getByText('Signs include dark urine [1], and stored water helps [2].')).toBeInTheDocument();
    await step(); // done
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.getByText('Signs include dark yellow urine and dizziness [1], and stored water helps [2].')).toBeInTheDocument();
    const citations = screen.getByRole('list', { name: 'Sources' });
    expect(within(citations).getByRole('link', { name: '[1] Dehydration (NHS)' })).toHaveAttribute('href', '/read/nhs_uk/www.nhs.uk/conditions/dehydration/');
  });

  it('ignores retrieving/token/done/error events that arrive after a turn is already done', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(ready);
    const extraToken: AiEvent = { event: 'token', data: { text: 'should not appear' } };
    const { step } = gatedAsk([...aiEvents, extraToken]);
    const user = userEvent.setup();
    renderRoute('/ai');
    const input = await screen.findByLabelText('Your question');
    await user.type(input, 'signs of dehydration{Enter}');
    await step(); // verbatim
    await step(); // retrieving
    await step(); // token 1
    await step(); // token 2
    await step(); // done
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.getByText('Signs include dark yellow urine and dizziness [1], and stored water helps [2].')).toBeInTheDocument();
    const citations = screen.getByRole('list', { name: 'Sources' });
    expect(within(citations).getByRole('link', { name: '[1] Dehydration (NHS)' })).toHaveAttribute('href', '/read/nhs_uk/www.nhs.uk/conditions/dehydration/');
    expect(input).not.toBeDisabled();

    // A stray token event arrives after the turn already reached its terminal phase.
    await step(); // extra token
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.getByText('Signs include dark yellow urine and dizziness [1], and stored water helps [2].')).toBeInTheDocument();
    expect(screen.queryByText('should not appear')).toBeNull();
    expect(within(citations).getByRole('link', { name: '[1] Dehydration (NHS)' })).toBeInTheDocument();
    expect(input).not.toBeDisabled();
    await user.type(input, 'another question');
    expect(screen.getByRole('button', { name: /Ask/ })).not.toBeDisabled();
  });

  it('caps the history sent with a question at 4 turns', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(ready);
    const requests: AiAskRequest[] = [];
    vi.spyOn(api, 'askAi').mockImplementation(async function* (req) {
      requests.push(req);
      yield { event: 'retrieving', data: { query: 'q', passages: [] } };
      yield { event: 'done', data: { answer: `answer ${requests.length}`, grounded: true, citations: [] } };
    });
    const user = userEvent.setup();
    renderRoute('/ai');
    const input = await screen.findByLabelText('Your question');
    for (let i = 1; i <= 6; i++) {
      await user.type(input, `question ${i}{Enter}`);
      await screen.findByText(`answer ${i}`);
    }
    expect(requests[5].history).toHaveLength(8);
    expect(requests[5].history[0]).toEqual({ role: 'user', content: 'question 2' });
    expect(requests[5].history[7]).toEqual({ role: 'assistant', content: 'answer 5' });
  });

  it('shows the not-backed notice and lists the passages when grounded is false', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(ready);
    const events: AiEvent[] = [aiEvents[1], { event: 'done', data: { answer: 'Probably dark urine.', grounded: false, citations: [] } }];
    vi.spyOn(api, 'askAi').mockImplementation(async function* () { yield* events; });
    const user = userEvent.setup();
    renderRoute('/ai');
    await user.type(await screen.findByLabelText('Your question'), 'x{Enter}');
    expect(await screen.findByText('This answer is not backed by a library passage.')).toBeInTheDocument();
    const passages = screen.getByRole('list', { name: 'Passages found' });
    expect(within(passages).getAllByRole('listitem')).toHaveLength(2);
    expect(within(passages).getByText(/Store 3 litres/)).toBeInTheDocument();
  });

  it('explains busy, timeout and transport errors', async () => {
    vi.spyOn(api, 'status').mockResolvedValue(ready);
    const spy = vi.spyOn(api, 'askAi');
    const user = userEvent.setup();
    renderRoute('/ai');
    const input = await screen.findByLabelText('Your question');
    spy.mockImplementationOnce(async function* () { yield { event: 'error', data: { code: 'busy', message: 'busy', retry_after: 30 } }; });
    await user.type(input, 'a{Enter}');
    expect(await screen.findByText('The AI is answering another question. Try again in 30 s.')).toBeInTheDocument();
    spy.mockImplementationOnce(async function* () { yield { event: 'error', data: { code: 'timeout', message: 'timeout' } }; });
    await user.type(input, 'b{Enter}');
    expect(await screen.findByText(/took too long/)).toBeInTheDocument();
    // eslint-disable-next-line require-yield -- simulates askAi throwing before any event arrives
    spy.mockImplementationOnce(async function* () { throw new Error('network down'); });
    await user.type(input, 'c{Enter}');
    expect(await screen.findByText('The AI is not available: network down')).toBeInTheDocument();
  });

  it('keeps the conversation on screen while the slot is busy instead of switching to the off layout', async () => {
    const { vi: v } = await import('vitest');
    const { api: client } = await import('../../src/api/client');
    const { status: base } = await import('../fixtures/api');
    v.spyOn(client, 'status').mockResolvedValue({ ...base, ai: { state: 'busy', model: 'gemma-4-E2B-it-Q4_K_M', message: null } });
    renderRoute('/ai');
    expect(await screen.findByRole('status')).toHaveTextContent('Another phone is asking');
    expect(screen.getByRole('textbox', { name: 'Your question' })).toBeDisabled();
    expect(screen.queryByText(/answering another question/)).not.toBeInTheDocument();
  });
});
