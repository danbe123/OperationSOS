import { CONDITION_IDS, type SituationView } from '../api/types';
import { CONDITION_INFO, STATE_LABEL } from './conditions';
import { describeElapsed } from '../tools/situation';

/** Join names the way a person would: "power", "power and water", "power, water and mobile". */
function joinNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? '';
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

function sentenceCase(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

/** Peacetime, in one line. "Everything is working" over "Food: 0 days · Water: 0 days · Nobody is
 * registered yet" is only half the truth, and it is the reassuring half: nothing is wrong with the
 * services, and the box is not ready.
 *
 * Whether the cupboard is empty is the cupboard's own answer, not the readiness gaps': a household
 * with 48 litres put by still has a `/plan#stock` gap the moment a category is under its target,
 * and reading "Nothing stored yet" over four full crates is the box calling the household a liar.
 * `stockEmpty` is null while the stock is still being read, and an unknown cupboard is not an
 * empty one. */
export function peacetimeTitle(view: SituationView, stockEmpty: boolean | null = null): string {
  const gaps = view.readiness?.gaps ?? [];
  if (!gaps.length) return 'Everything is working';
  if (stockEmpty) return 'Everything is working. Nothing stored yet.';
  return 'Everything is working. Not ready yet.';
}

/** The answer at the top of Now. The rail already says which screen this is, so the heading says
 * what is happening instead: the situation and how long it has been running, what is not working,
 * or that nothing is wrong. */
export function nowTitle(view: SituationView | null, stockEmpty: boolean | null = null): string {
  if (!view) return 'Situation unknown';
  if (view.scenario) return `${view.scenario.title} · ${describeElapsed(view.scenario.elapsed_s)}`;
  const broken = CONDITION_IDS.map((id) => view.conditions[id]).filter((c) => c && c.state !== 'working');
  if (!broken.length) return peacetimeTitle(view, stockEmpty);
  if (broken.length > 3) return `${broken.length} services are not working`;
  const parts: string[] = [];
  for (const state of ['off', 'degraded'] as const) {
    const names = broken.filter((c) => c.state === state).map((c) => CONDITION_INFO[c.id].short.toLowerCase());
    if (names.length) parts.push(`${joinNames(names)} ${STATE_LABEL[state]}`);
  }
  return sentenceCase(parts.join(', '));
}
