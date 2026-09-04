import type { ChecklistItem, Note, Status } from '../../src/api/types';
import { notes, playbook, status } from '../../tests/fixtures/api';

export const PIN = '1234';
export const TOKEN = 'e2e-token';

export type FixtureState = {
  status: Status;
  checklists: Map<string, ChecklistItem[]>;
  notes: Note[];
  nextNoteId: number;
  ethMode: 'client' | 'direct';
};

/** One state object per test; share it between browser contexts to model "another phone". */
export function createFixtureState(overrides: Partial<Status> = {}): FixtureState {
  return {
    status: { ...status, ...overrides },
    checklists: new Map([[playbook.slug, playbook.checklist.map((i) => ({ ...i }))]]),
    notes: notes.map((n) => ({ ...n })),
    nextNoteId: 100,
    ethMode: 'client',
  };
}
