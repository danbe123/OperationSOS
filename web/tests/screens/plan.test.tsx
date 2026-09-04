import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Note } from '../../src/api/types';
import { householdPlan, notes } from '../fixtures/api';

function mockNotes() {
  const list: Note[] = notes.map((n) => ({ ...n }));
  vi.spyOn(api, 'page').mockResolvedValue(householdPlan);
  vi.spyOn(api, 'notes').mockImplementation(async (kind) => list.filter((n) => !kind || n.kind === kind));
  const create = vi.spyOn(api, 'createNote').mockImplementation(async (n) => {
    const note: Note = { id: 10, kind: 'note', title: n.title ?? '', body: n.body ?? '', lat: null, lon: null, updated_at: '2026-09-03T12:00:00Z' };
    list.push(note);
    return note;
  });
  const update = vi.spyOn(api, 'updateNote').mockImplementation(async (id, n) => {
    const i = list.findIndex((x) => x.id === id);
    list[i] = { ...list[i], ...n, updated_at: '2026-09-03T12:05:00Z' } as Note;
    return list[i];
  });
  const del = vi.spyOn(api, 'deleteNote').mockImplementation(async (id) => {
    list.splice(list.findIndex((x) => x.id === id), 1);
    return { ok: true as const };
  });
  return { create, update, del };
}

describe('Plan', () => {
  it('shows the household plan, the notes and the pins with map links', async () => {
    mockNotes();
    renderRoute('/plan');
    expect(await screen.findByRole('heading', { name: 'Meeting points' })).toBeInTheDocument();
    const notesList = screen.getByRole('list', { name: 'Notes' });
    expect(within(notesList).getByText('Meeting point')).toBeInTheDocument();
    const pins = screen.getByRole('list', { name: 'Pins' });
    expect(within(pins).getByRole('link', { name: /Well/ })).toHaveAttribute('href', '/map?lat=50.94000&lon=-1.47000&z=15&label=Well');
    expect(screen.getByRole('button', { name: /Print/ })).toBeInTheDocument();
  });

  it('adds, edits and deletes a note', async () => {
    const { create, update, del } = mockNotes();
    const user = userEvent.setup();
    renderRoute('/plan');
    await screen.findByRole('list', { name: 'Notes' });
    await user.type(screen.getByLabelText('Title'), 'Water stash');
    await user.type(screen.getByLabelText('Note'), 'Ten litres in the shed');
    await user.click(screen.getByRole('button', { name: 'Add note' }));
    expect(create).toHaveBeenCalledWith({ kind: 'note', title: 'Water stash', body: 'Ten litres in the shed' });
    expect(await screen.findByText('Water stash')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Edit Water stash' }));
    const body = screen.getByLabelText('Edit note');
    await user.clear(body);
    await user.type(body, 'Twenty litres');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(update).toHaveBeenCalledWith(10, { title: 'Water stash', body: 'Twenty litres' });
    expect(await screen.findByText('Twenty litres')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Delete Water stash' }));
    await user.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(del).toHaveBeenCalledWith(10);
    expect(screen.queryByText('Water stash')).toBeNull();
  });

  it('hides Print in kiosk mode', async () => {
    mockNotes();
    renderRoute('/plan', { kiosk: true });
    await screen.findByRole('list', { name: 'Notes' });
    expect(screen.queryByRole('button', { name: /Print/ })).toBeNull();
  });
});
