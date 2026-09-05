import type { ChecklistItem, Conditions, Home, Note, Person, Situation, Status, StockItem } from '../../src/api/types';
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
};

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
  };
}
