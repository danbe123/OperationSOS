import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Note, Person, StockResponse } from '../../src/api/types';
import { formatStamp } from '../../src/screens/plan/EventLog';
import { householdPlan, neighbours, notes } from '../fixtures/api';

const people: Person[] = [
  { id: 1, name: 'Sam', age: 7, needs: 'asthma', medications: 'salbutamol inhaler', contacts: '', updated_at: '2026-09-05T10:00:00Z' },
  { id: 2, name: 'Ali', age: null, needs: '', medications: '', contacts: 'Gran 0161 000', updated_at: '2026-09-05T10:00:00Z' },
];
const stock: StockResponse = {
  people: 2,
  days: { water: 4, food: 3, medicine: 0 },
  items: [
    { id: 1, name: 'Bottled water', category: 'water', quantity: 24, unit: 'L', per_person_day: 3, expires: null, notes: '', updated_at: '2026-09-05T10:00:00Z', days_left: 4, expired: false, kit_item: null },
  ],
};
const events: Note[] = [
  { id: 30, kind: 'event', title: 'Heard sirens (phone)', body: '', lat: null, lon: null, updated_at: '2026-09-05T11:30:00Z' },
  { id: 29, kind: 'event', title: 'Water off', body: '', lat: null, lon: null, updated_at: '2026-09-05T10:15:00Z' },
];

/** The hub reads six lists and writes one line about each. */
function mockHub(over: { people?: Person[]; neighbours?: typeof neighbours; stock?: StockResponse | null; notes?: Note[]; events?: Note[] } = {}) {
  const noteList = over.notes ?? notes;
  vi.spyOn(api, 'page').mockResolvedValue(householdPlan);
  vi.spyOn(api, 'household').mockResolvedValue(over.people ?? people);
  vi.spyOn(api, 'neighbours').mockResolvedValue(over.neighbours ?? neighbours);
  vi.spyOn(api, 'stock').mockResolvedValue(over.stock === undefined ? stock : (over.stock as StockResponse));
  vi.spyOn(api, 'notes').mockImplementation(async (kind) => (kind === 'event' ? over.events ?? events : noteList.filter((n) => n.kind === kind)));
}

describe('The Household hub', () => {
  it('shows the six rows in order, each with where that part stands', async () => {
    mockHub();
    renderRoute('/plan');
    const nav = await screen.findByRole('navigation', { name: 'Household' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual([
      '/plan/people', '/plan/neighbours', '/plan/stock', '/plan/plan', '/plan/notes', '/situation#log',
    ]);
    expect(links.map((a) => within(a).getByText(/^(People|Neighbours|Stock|The plan|Notes and pins|What happened)$/).textContent)).toEqual([
      'People', 'Neighbours', 'Stock', 'The plan', 'Notes and pins', 'What happened',
    ]);
    expect(await within(nav).findByText('2 registered, 1 with medical needs')).toBeInTheDocument();
    expect(within(nav).getByText('2 on the street list')).toBeInTheDocument();
    expect(within(nav).getByText('Water 4 days · Food 3 days · Medicine none')).toBeInTheDocument();
    expect(within(nav).getByText('Meeting point set')).toBeInTheDocument();
    expect(within(nav).getByText('1 note, 1 pin')).toBeInTheDocument();
    expect(within(nav).getByText(`Last entry ${formatStamp('2026-09-05T11:30:00Z')}, Heard sirens on a phone`)).toBeInTheDocument();
  });

  it('carries no forms of its own: every one of them lives on the screen the row opens', async () => {
    mockHub();
    renderRoute('/plan');
    await screen.findByRole('navigation', { name: 'Household' });
    expect(screen.queryByRole('form')).toBeNull();
    expect(screen.queryByRole('button', { name: /Add/ })).toBeNull();
  });

  it('says so, in a sentence each, when the household has written nothing down', async () => {
    mockHub({ people: [], neighbours: [], stock: { people: 0, days: { water: 0, food: 0, medicine: 0 }, items: [] }, notes: [], events: [] });
    renderRoute('/plan');
    const nav = await screen.findByRole('navigation', { name: 'Household' });
    expect(await within(nav).findByText('Nobody registered yet')).toBeInTheDocument();
    expect(within(nav).getByText('No neighbours listed')).toBeInTheDocument();
    expect(within(nav).getByText('Nothing tracked yet')).toBeInTheDocument();
    expect(within(nav).getByText('No meeting point yet')).toBeInTheDocument();
    expect(within(nav).getByText('Nothing written down')).toBeInTheDocument();
    expect(within(nav).getByText('No entries yet')).toBeInTheDocument();
  });

  it('counts a meeting point written in the body of a pin, as the engine does', async () => {
    mockHub({ notes: [{ id: 7, kind: 'pin', title: 'The church hall', body: 'Our meeting point if the street is closed', lat: 50.94, lon: -1.47, updated_at: '2026-09-03T09:30:00Z' }] });
    renderRoute('/plan');
    const nav = await screen.findByRole('navigation', { name: 'Household' });
    expect(await within(nav).findByText('Meeting point set')).toBeInTheDocument();
  });

  it('sends the old anchors to the screen that holds that part now', async () => {
    mockHub();
    for (const [hash, pathname] of [['#stock', '/plan/stock'], ['#household', '/plan/people'], ['#pins', '/plan/notes'], ['#notes', '/plan/notes']]) {
      const at = renderRoute(`/plan${hash}`);
      await waitFor(() => expect(at.router.state.location.pathname).toBe(pathname));
      at.unmount();
    }
    const log = renderRoute('/plan#log');
    await waitFor(() => expect(log.router.state.location.pathname).toBe('/situation'));
    expect(log.router.state.location.hash).toBe('#log');
  });

  it('shows the household plan on its own screen', async () => {
    mockHub();
    renderRoute('/plan/plan');
    expect(await screen.findByRole('heading', { name: 'The plan', level: 1 })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Meeting points' })).toBeInTheDocument();
  });

  it('offers Print, and hides it in kiosk mode', async () => {
    mockHub();
    const shown = renderRoute('/plan');
    await screen.findByRole('navigation', { name: 'Household' });
    expect(screen.getByRole('button', { name: /Print/ })).toBeInTheDocument();
    shown.unmount();

    renderRoute('/plan', { kiosk: true });
    await screen.findByRole('navigation', { name: 'Household' });
    expect(screen.queryByRole('button', { name: /Print/ })).toBeNull();
  });
});
