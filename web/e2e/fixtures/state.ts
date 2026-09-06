import type { ChecklistItem, Conditions, Home, Neighbour, Note, Person, Recording, Sensors, Situation, Status, StockItem } from '../../src/api/types';
import { notes, playbook, status } from '../../tests/fixtures/api';
import { freshConditions } from './engine';

export const PIN = '1234';
export const TOKEN = 'e2e-token';

export type FixtureState = {
  status: Status;
  checklists: Map<string, ChecklistItem[]>;
  notes: Note[];
  nextNoteId: number;
  household: Person[];
  stock: StockItem[];
  situation: Situation;
  conditions: Conditions;
  /** done and who, by task id; checklist tasks keep their state in `checklists` instead */
  taskState: Map<string, { done: boolean; person: string | null; done_at: string | null }>;
  home: Home | null;
  drill: boolean;
  savedConditions: Conditions | null;
  dark: boolean;
  nextId: number;
  ethMode: 'client' | 'direct';
  /** Facilities round the box; the /nearby route works out distance, bearing and walking time per request. */
  places: FixturePlace[];
  /** Facility ids the box has no searchable data for, so /nearby answers them with a `why`. */
  missingNearby: string[];
  neighbours: Neighbour[];
  sensors: Sensors;
  /** Piper installed? When false /speak answers 503 and the read-aloud buttons take themselves away. */
  speaks: boolean;
  recordings: Recording[];
};

/** One place the fixture box knows about, keyed by the facility id `/nearby` answers under. */
export type FixturePlace = { facility: string; name: string; lat: number; lon: number };

/** Around the fixture map's postcode (SO16 0AS), close enough to walk to in the panel's terms. */
export const FIXTURE_PLACES: FixturePlace[] = [
  { facility: 'pharmacy', name: 'Boots, High Street', lat: 50.9400, lon: -1.4680 },
  { facility: 'pharmacy', name: 'Shirley Pharmacy', lat: 50.9290, lon: -1.4455 },
  /* OpenStreetMap carries pharmacies with no name on them; "Unnamed" is not a place. */
  { facility: 'pharmacy', name: '', lat: 50.9260, lon: -1.4400 },
  { facility: 'emergency-department', name: 'Southampton General Hospital', lat: 50.9331, lon: -1.4342 },
  /* The same hospital mapped twice, a hundred metres apart: the box keeps one. */
  { facility: 'emergency-department', name: 'Southampton General Hospital', lat: 50.9340, lon: -1.4350 },
  { facility: 'gp', name: 'Shirley Health Centre', lat: 50.9290, lon: -1.4460 },
  { facility: 'water-works', name: 'Testwood water works', lat: 50.9310, lon: -1.4930 },
];

/** One state object per test; share it between browser contexts to model "another phone". */
export function createFixtureState(overrides: Partial<Status> = {}): FixtureState {
  return {
    status: { ...status, ...overrides },
    checklists: new Map([[playbook.slug, playbook.checklist.map((i) => ({ ...i }))]]),
    notes: notes.map((n) => ({ ...n })),
    nextNoteId: 100,
    household: [],
    stock: [],
    situation: { slug: null },
    conditions: freshConditions(new Date(Date.now() - 3_600_000).toISOString()),
    taskState: new Map(),
    home: null,
    drill: false,
    savedConditions: null,
    dark: false,
    nextId: 1,
    ethMode: 'client',
    places: FIXTURE_PLACES.map((x) => ({ ...x })),
    missingNearby: ['rest-centre', 'fire-station', 'fuel'],
    neighbours: [],
    sensors: {
      internet: { value: 1, unit: 'up', at: new Date(Date.now() - 120_000).toISOString() },
      mains: { value: 1, unit: 'on', at: new Date(Date.now() - 60_000).toISOString() },
      temp_in: { value: 14.5, unit: '\u00b0C', at: new Date(Date.now() - 300_000).toISOString() },
    },
    speaks: true,
    recordings: [],
  };
}
