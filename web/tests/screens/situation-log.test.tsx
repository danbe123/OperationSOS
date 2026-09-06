import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { playbooks, view } from '../fixtures/api';

const events = [
  { id: 30, kind: 'event' as const, title: 'Heard sirens', body: '', lat: null, lon: null, updated_at: '2026-09-05T11:30:00Z' },
  { id: 29, kind: 'event' as const, title: 'Water off', body: '', lat: null, lon: null, updated_at: '2026-09-05T10:15:00Z' },
];

function mockSheet() {
  vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
  vi.spyOn(api, 'situationView').mockResolvedValue(view);
  vi.spyOn(api, 'notes').mockResolvedValue(events);
}

/** What happened lives under the sheet that says what is working: one screen, not two. */
describe('The event log under the situation sheet', () => {
  it('lists what happened, newest first', async () => {
    mockSheet();
    renderRoute('/situation');
    const log = await screen.findByRole('region', { name: 'What happened' });
    expect(within(log).getByRole('heading', { name: 'What happened' })).toBeInTheDocument();
    expect(within(log).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      expect.stringContaining('Heard sirens'),
      expect.stringContaining('Water off'),
    ]);
  });

  it('keeps the form behind a button, and puts it away once the entry is logged', async () => {
    mockSheet();
    const createNote = vi.spyOn(api, 'createNote').mockResolvedValue(events[0]);
    renderRoute('/situation');
    const user = userEvent.setup();
    const log = await screen.findByRole('region', { name: 'What happened' });
    expect(within(log).queryByRole('form', { name: 'Log an event' })).toBeNull();

    await user.click(within(log).getByRole('button', { name: 'Add an entry' }));
    const form = within(log).getByRole('form', { name: 'Log an event' });
    await user.type(within(form).getByLabelText('What happened'), 'Gave Sam 5ml paracetamol');
    await user.click(within(form).getByRole('button', { name: 'Log it' }));
    expect(createNote).toHaveBeenCalledWith({ kind: 'event', title: 'Gave Sam 5ml paracetamol' });
    expect(within(log).queryByRole('form', { name: 'Log an event' })).toBeNull();
  });

  it('puts the form away again on Cancel', async () => {
    mockSheet();
    renderRoute('/situation');
    const user = userEvent.setup();
    const log = await screen.findByRole('region', { name: 'What happened' });
    await user.click(within(log).getByRole('button', { name: 'Add an entry' }));
    await user.click(within(within(log).getByRole('form', { name: 'Log an event' })).getByRole('button', { name: 'Cancel' }));
    expect(within(log).queryByRole('form', { name: 'Log an event' })).toBeNull();
    expect(within(log).getByRole('button', { name: 'Add an entry' })).toBeInTheDocument();
  });
});
