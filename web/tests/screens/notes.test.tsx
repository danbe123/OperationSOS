import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
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
  return { create, update, del, list };
}

describe('Notes and pins', () => {
  it('lists the notes and the pins together, newest first, pins linking to the map', async () => {
    mockNotes();
    renderRoute('/notes');
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
    renderRoute('/notes');
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
    renderRoute('/notes');
    await user.click(await screen.findByRole('button', { name: 'Add a note' }));
    await user.click(within(screen.getByRole('form', { name: 'Add a note' })).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form', { name: 'Add a note' })).toBeNull();
    expect(create).not.toHaveBeenCalled();
  });

  it('asks the box for notes and pins by kind, never for every note in it', async () => {
    mockNotes();
    const notesApi = vi.mocked(api.notes);
    renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    // The event log is hundreds of rows on a busy day and not one of them belongs on this screen:
    // two requests for the two kinds shown, and no call that asks for the lot.
    expect(notesApi.mock.calls.map((c) => c[0]).sort()).toEqual(['note', 'pin']);
  });

  it('reads the list back after an add, leaving a note that was open for editing open', async () => {
    mockNotes();
    const user = userEvent.setup();
    renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Edit Meeting point' }));
    expect(screen.getByLabelText('Edit note')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    const form = screen.getByRole('form', { name: 'Add a note' });
    await user.type(within(form).getByLabelText('Title'), 'Water stash');
    await user.click(within(form).getByRole('button', { name: 'Add note' }));
    // The new note is on the screen that wrote it, and the editor beside it was not thrown away.
    expect(await screen.findByText('Water stash')).toBeInTheDocument();
    expect(screen.getByLabelText('Edit note')).toBeInTheDocument();
  });

  it('says so when there is nothing written down yet', async () => {
    vi.spyOn(api, 'notes').mockResolvedValue([]);
    renderRoute('/notes');
    const list = await screen.findByRole('list', { name: 'Notes and pins' });
    expect(await within(list).findByText(/Nothing written down yet/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add a note' })).toBeInTheDocument();
  });
});

describe('A note in the middle of being written', () => {
  it('is kept when the note cannot be saved, says so, and is saved when the box is back', async () => {
    const { create } = mockNotes();
    const user = userEvent.setup();
    renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    const form = screen.getByRole('form', { name: 'Add a note' });
    await user.type(within(form).getByLabelText('Title'), 'Rendezvous');
    await user.type(within(form).getByLabelText('Note'), 'Church car park at noon');
    create.mockRejectedValueOnce(new ApiError(0, 'The box is not answering, so nothing was saved'));
    await user.click(within(form).getByRole('button', { name: 'Add note' }));
    expect(await screen.findByText(/Not saved yet/)).toBeInTheDocument();
    expect(within(form).getByLabelText('Title')).toHaveValue('Rendezvous');
    expect(within(form).getByLabelText('Note')).toHaveValue('Church car park at noon');
    await user.click(within(form).getByRole('button', { name: 'Add note' }));
    expect(await screen.findByText('Rendezvous')).toBeInTheDocument();
    expect(screen.queryByText(/Not saved yet/)).toBeNull();
    expect(localStorage.getItem('sos.draft.note')).toBeNull();
  });

  it('comes back after the screen is reloaded, or the browser restarted, until it is saved or cancelled', async () => {
    mockNotes();
    const user = userEvent.setup();
    const first = renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    await user.type(screen.getByLabelText('Title'), 'Half a thought');
    await user.type(screen.getByLabelText('Note'), 'Gas bottles: two in the');
    first.unmount();   // Chromium restarted: everything in memory is gone, the page comes up again
    renderRoute('/notes');
    const form = await screen.findByRole('form', { name: 'Add a note' });
    expect(within(form).getByLabelText('Title')).toHaveValue('Half a thought');
    expect(within(form).getByLabelText('Note')).toHaveValue('Gas bottles: two in the');
    expect(screen.getByText(/Restored what you were writing/)).toBeInTheDocument();
    await user.click(within(form).getByRole('button', { name: 'Cancel' }));
    expect(localStorage.getItem('sos.draft.note')).toBeNull();
  });

  it('still works when the browser will not store anything', async () => {
    mockNotes();
    const user = userEvent.setup();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota'); });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('denied'); });
    renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    await user.type(screen.getByLabelText('Title'), 'Still here');
    expect(screen.getByLabelText('Title')).toHaveValue('Still here');
    vi.restoreAllMocks();
  });
});

describe('Add note while a save is in flight', () => {
  it('takes one tap, however many follow, and one Enter, and keeps the draft', async () => {
    const { create, list } = mockNotes();
    let finish: (n: Note) => void = () => {};
    create.mockImplementationOnce(() => new Promise<Note>((resolve) => { finish = resolve; }));
    const user = userEvent.setup();
    renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    const form = screen.getByRole('form', { name: 'Add a note' });
    await user.type(within(form).getByLabelText('Title'), 'Once only');
    const add = within(form).getByRole('button', { name: 'Add note' });
    await user.click(add);
    await user.click(add);
    await user.click(add);
    await user.type(within(form).getByLabelText('Title'), '{Enter}');
    expect(create).toHaveBeenCalledTimes(1);
    expect(add).toBeDisabled();
    expect(localStorage.getItem('sos.draft.note')).not.toBeNull();   // the draft is kept until the box has it
    const saved: Note = { id: 11, kind: 'note', title: 'Once only', body: '', lat: null, lon: null, updated_at: '2026-09-03T12:00:00Z' };
    list.push(saved);
    finish(saved);
    expect(await screen.findByText('Once only')).toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(1);
  });

  it('lets the person try again when the save failed', async () => {
    const { create } = mockNotes();
    create.mockRejectedValueOnce(new ApiError(0, 'The box is not answering, so nothing was saved'));
    const user = userEvent.setup();
    renderRoute('/notes');
    await screen.findByRole('list', { name: 'Notes and pins' });
    await user.click(screen.getByRole('button', { name: 'Add a note' }));
    const form = screen.getByRole('form', { name: 'Add a note' });
    await user.type(within(form).getByLabelText('Note'), 'Try me');
    await user.click(within(form).getByRole('button', { name: 'Add note' }));
    await screen.findByText(/Not saved yet/);
    expect(within(form).getByRole('button', { name: 'Add note' })).toBeEnabled();
    await user.click(within(form).getByRole('button', { name: 'Add note' }));
    expect(await screen.findByText('Try me')).toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(2);
  });
});
