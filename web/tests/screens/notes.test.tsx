import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Note } from '../../src/api/types';
import { notes } from '../fixtures/api';

function mockNotes() {
  const list: Note[] = notes.map((n) => ({ ...n }));
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

describe('Notes and pins', () => {
  it('lists the notes and the pins together, newest first, pins linking to the map', async () => {
    mockNotes();
    renderRoute('/plan/notes');
    expect(await screen.findByRole('heading', { name: 'Notes and pins', level: 1 })).toBeInTheDocument();
    const list = await screen.findByRole('list', { name: 'Notes and pins' });
    const items = await within(list).findAllByRole('listitem');
    expect(items).toHaveLength(2);
    // The pin was written at 09:30, the note at 09:00.
    expect(within(items[0]).getByRole('link', { name: /Well/ })).toHaveAttribute('href', '/map?lat=50.94000&lon=-1.47000&z=15&label=Well');
    expect(items[0]).toHaveTextContent(/SU \d{3} \d{3}/);
    expect(items[1]).toHaveTextContent('Meeting point');
    expect(screen.queryByRole('form', { name: 'Add a note' })).toBeNull();
  });

  it('adds, edits and deletes a note, with the form behind the button', async () => {
    const { create, update, del } = mockNotes();
    const user = userEvent.setup();
    renderRoute('/plan/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    const form = screen.getByRole('form', { name: 'Add a note' });
    await user.type(within(form).getByLabelText('Title'), 'Water stash');
    await user.type(within(form).getByLabelText('Note'), 'Ten litres in the shed');
    await user.click(within(form).getByRole('button', { name: 'Add note' }));
    expect(create).toHaveBeenCalledWith({ kind: 'note', title: 'Water stash', body: 'Ten litres in the shed' });
    expect(await screen.findByText('Water stash')).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Add a note' })).toBeNull();

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

  it('cancels the form without writing anything', async () => {
    const { create } = mockNotes();
    const user = userEvent.setup();
    renderRoute('/plan/notes');
    await user.click(await screen.findByRole('button', { name: 'Add a note' }));
    await user.click(within(screen.getByRole('form', { name: 'Add a note' })).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form', { name: 'Add a note' })).toBeNull();
    expect(create).not.toHaveBeenCalled();
  });

  it('says so when there is nothing written down yet', async () => {
    vi.spyOn(api, 'notes').mockResolvedValue([]);
    renderRoute('/plan/notes');
    const list = await screen.findByRole('list', { name: 'Notes and pins' });
    expect(await within(list).findByText(/Nothing written down yet/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add a note' })).toBeInTheDocument();
  });
});
