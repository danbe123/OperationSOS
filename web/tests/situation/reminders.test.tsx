import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, waitFor } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { dueNow, readSeen, reminderKey, reminderText, SEEN_KEY, writeSeen } from '../../src/situation/reminders';
import * as audio from '../../src/tools/audio';
import { makeView, playbooks, powerOffView, VIEW_NOW, view } from '../fixtures/api';

const NOW = Date.parse(VIEW_NOW);
const passed = { id: 'fridge', title: 'Fridge food unsafe', due_at: '2026-09-06T13:00:00.000Z', severity: 'warn' as const, why: 'A closed fridge holds about 4 hours.', link: 'module:food', passed: true };
const later = powerOffView.forecast[1];

/** The in-app toasts, whichever screen they landed on. */
const toasts = () => document.querySelector('.notices')?.textContent ?? '';

afterEach(() => { localStorage.clear(); vi.useRealTimers(); });

describe('forecast reminders', () => {
  it('picks the items whose time has come and nobody has been told about', () => {
    const v = makeView({ forecast: [passed, later] });
    expect(dueNow(v, [], NOW).map((f) => f.id)).toEqual(['fridge']);
    expect(dueNow(v, [reminderKey(passed)], NOW)).toEqual([]);
    expect(dueNow(null, [], NOW)).toEqual([]);
    // the same item at a new due time is a new reminder
    expect(dueNow(makeView({ forecast: [{ ...passed, due_at: '2026-09-06T13:30:00.000Z' }] }), [reminderKey(passed)], NOW)).toHaveLength(1);
  });

  it('remembers what it has said, and keeps the list short', () => {
    writeSeen(localStorage, ['a', 'b']);
    expect(readSeen(localStorage)).toEqual(['a', 'b']);
    writeSeen(localStorage, Array.from({ length: 60 }, (_, i) => `k${i}`));
    expect(readSeen(localStorage)).toHaveLength(40);
    localStorage.setItem(SEEN_KEY, 'not json');
    expect(readSeen(localStorage)).toEqual([]);
  });

  it('says the item and why it matters', () => {
    expect(reminderText(passed)).toBe('▲ Fridge food unsafe. A closed fridge holds about 4 hours.');
    expect(reminderText({ ...passed, severity: 'danger', why: '' })).toBe('⚠ Fridge food unsafe.');
  });
});

describe('the app while a countdown runs out', () => {
  it('takes what was already past as read, then toasts and sounds the alarm on the next one', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    const alarm = vi.spyOn(audio, 'alarm').mockImplementation(() => {});
    const start = makeView({ forecast: [passed, later] });
    const next = makeView({ forecast: [passed, { ...later, due_at: '2026-09-06T13:59:00.000Z', passed: true }] });
    const situationView = vi.spyOn(api, 'situationView').mockResolvedValue(start);
    renderRoute('/');
    await screen.findByRole('navigation', { name: 'Scenarios' });
    expect(toasts()).toBe('');
    expect(alarm).not.toHaveBeenCalled();
    expect(readSeen(localStorage)).toEqual([reminderKey(passed)]);

    situationView.mockResolvedValue(next);
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    await waitFor(() => expect(toasts()).toContain('Freezer food unsafe'));
    expect(toasts()).toContain('A half-full freezer holds about 24 hours.');
    expect(alarm).toHaveBeenCalledTimes(1);

    // and never twice for the same item
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    expect(alarm).toHaveBeenCalledTimes(1);
  });

  it('says nothing while nothing is due', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    const alarm = vi.spyOn(audio, 'alarm').mockImplementation(() => {});
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    await screen.findByRole('navigation', { name: 'Scenarios' });
    expect(alarm).not.toHaveBeenCalled();
    expect(readSeen(localStorage)).toEqual([]);
  });
});
