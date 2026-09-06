import { Link, Navigate, useLocation } from 'react-router';
import { api } from '../api/client';
import type { Neighbour, Note, Person, StockResponse } from '../api/types';
import { useQuery } from '../api/useQuery';
import { eventTitle } from '../api/words';
import { PrintButton } from '../components/PrintButton';
import { Icon, type IconName } from '../icons';
import { Screen, Body } from '../shell/Screen';
import { formatStamp } from './plan/EventLog';
import './plan/plan.css';

/** Household used to be one long screen with seven sections and a row of jump chips above them; the
 * chips were the admission that it was too long to read. Each part now has a screen of its own, and
 * this is the way in: six rows that each say where that part stands, so "is there anything to do
 * here" is answered before anything is opened. */
const ROWS: { key: string; to: string; icon: IconName; title: string }[] = [
  { key: 'people', to: '/plan/people', icon: 'face', title: 'People' },
  { key: 'neighbours', to: '/plan/neighbours', icon: 'home', title: 'Neighbours' },
  { key: 'stock', to: '/plan/stock', icon: 'drop', title: 'Stock' },
  { key: 'plan', to: '/plan/plan', icon: 'plan', title: 'The plan' },
  { key: 'notes', to: '/plan/notes', icon: 'pin', title: 'Notes and pins' },
  { key: 'log', to: '/situation#log', icon: 'book', title: 'What happened' },
];

/** The old section anchors are written on printed sheets, in the readiness gaps and in other
 * screens' links, so every one of them still lands on the part it named. */
const ANCHORS: Record<string, string> = {
  '#household': '/plan/people',
  '#neighbours': '/plan/neighbours',
  '#stock': '/plan/stock',
  '#plan': '/plan/plan',
  '#notes': '/plan/notes',
  '#pins': '/plan/notes',
  '#log': '/situation#log',
};

/** One line under each row's title: the state of that part, in the household's own words. */
export function stateLines(d: {
  people: Person[]; neighbours: Neighbour[]; stock: StockResponse | null;
  notes: Note[]; pins: Note[]; events: Note[]; meeting: boolean;
}): Record<string, string> {
  const withNeeds = d.people.filter((p) => p.needs || p.medications).length;
  const cat = (c: 'water' | 'food' | 'medicine', label: string) => {
    const days = d.stock?.days[c] ?? 0;
    return `${label} ${days > 0 ? `${days} ${days === 1 ? 'day' : 'days'}` : 'none'}`;
  };
  return {
    people: d.people.length === 0 ? 'Nobody registered yet' : `${d.people.length} registered${withNeeds ? `, ${withNeeds} with medical needs` : ''}`,
    neighbours: d.neighbours.length === 0 ? 'No neighbours listed' : `${d.neighbours.length} on the street list`,
    stock: !d.stock || d.stock.items.length === 0 ? 'Nothing tracked yet' : `${cat('water', 'Water')} · ${cat('food', 'Food')} · ${cat('medicine', 'Medicine')}`,
    plan: d.meeting ? 'Meeting point set' : 'No meeting point yet',
    notes: d.notes.length + d.pins.length === 0 ? 'Nothing written down' : `${d.notes.length} ${d.notes.length === 1 ? 'note' : 'notes'}, ${d.pins.length} ${d.pins.length === 1 ? 'pin' : 'pins'}`,
    log: d.events.length === 0 ? 'No entries yet' : `Last entry ${formatStamp(d.events[0].updated_at)}, ${eventTitle(d.events[0].title)}`,
  };
}

/** The engine's own test for a meeting point: the words in the title or the body of any note or pin
 * (`api/sos/routers/situation.py`). The hub must agree with the readiness score about whether the
 * household has one. */
function hasMeetingPoint(notes: Note[]): boolean {
  return notes.some((n) => /meeting point/i.test(`${n.title ?? ''} ${n.body ?? ''}`));
}

function Hub() {
  const peopleQ = useQuery(() => api.household(), []);
  const neighboursQ = useQuery(() => api.neighbours(), []);
  const stockQ = useQuery(() => api.stock(), []);
  const notesQ = useQuery(() => api.notes('note'), []);
  const pinsQ = useQuery(() => api.notes('pin'), []);
  const eventsQ = useQuery(() => api.notes('event'), []);
  const notes = notesQ.data ?? [];
  const pins = pinsQ.data ?? [];
  const lines = stateLines({
    people: peopleQ.data ?? [],
    neighbours: neighboursQ.data ?? [],
    stock: stockQ.data,
    notes,
    pins,
    events: eventsQ.data ?? [],
    meeting: hasMeetingPoint([...notes, ...pins]),
  });
  return (
    <Screen title="Household" actions={<PrintButton />}>
      <Body>
        <nav className="hub-rows" aria-label="Household">
          {ROWS.map((row) => (
            <Link className="hub-row" key={row.key} to={row.to}>
              <Icon name={row.icon} size={24} />
              <span className="hub-row-text">
                <span className="hub-row-title">{row.title}</span>
                <span className="hub-row-state">{lines[row.key]}</span>
              </span>
              <Icon name="forward" size={22} className="hub-row-go" />
            </Link>
          ))}
        </nav>
      </Body>
    </Screen>
  );
}

export function Plan() {
  const { hash } = useLocation();
  const anchored = ANCHORS[hash.toLowerCase()];
  if (anchored) return <Navigate to={anchored} replace />;
  return <Hub />;
}
