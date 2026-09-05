import type { Condition, SituationView, Task } from '../api/types';

/** Optimistic updates: put a saved row back into the View so the screen moves before the next poll. */
export function withTask(view: SituationView, task: Task): SituationView {
  return { ...view, tasks: view.tasks.map((t) => (t.id === task.id ? task : t)) };
}

export function withCondition(view: SituationView, condition: Condition): SituationView {
  return {
    ...view,
    conditions: { ...view.conditions, [condition.id]: condition },
    // the proposal that suggested this state has been answered
    inferred: view.inferred.filter((i) => i.condition !== condition.id),
  };
}
