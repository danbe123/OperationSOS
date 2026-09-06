// A small in-memory situation engine for the Playwright fixtures: enough of the contract for the
// screens to be exercised without the backend (conditions, a fixed forecast when the power is off,
// tasks with their done state, modes, briefing, readiness).
import { CONDITION_IDS, type Condition, type ConditionId, type ConditionState, type Conditions, type Forecast, type Inferred, type SituationView, type Task } from '../../src/api/types';
import { phaseFor } from '../../src/tools/situation';
import type { FixtureState } from './state';

const HOUR = 3_600_000;
const TITLES: Record<ConditionId, string> = {
  power: 'Mains power', water: 'Water supply', mobile: 'Mobile network', landline: 'Landline and 999', internet: 'Internet',
  gas: 'Gas', heating: 'Heating', roads: 'Roads and transport', shops: 'Shops and cash', sewage: 'Sewage and drains',
};

export function freshConditions(at = new Date().toISOString()): Conditions {
  return Object.fromEntries(CONDITION_IDS.map((id) => [id, {
    id, title: TITLES[id], state: 'working' as ConditionState, since: at, for_s: 0, source: 'manual' as const,
    confidence: 1, note: '', set_by: 'phone', updated_at: at, confirmed_at: at, stale: false,
  }])) as Conditions;
}

function aged(c: Condition, now: number): Condition {
  const since = c.since ? Date.parse(c.since) : now;
  const for_s = Math.max(0, Math.round((now - since) / 1000));
  const confirmed = c.confirmed_at ? Date.parse(c.confirmed_at) : Date.parse(c.updated_at);
  return { ...c, for_s, stale: c.state !== 'working' && now - confirmed >= 24 * HOUR };
}

const sinceOf = (c: Condition): number => (c.since ? Date.parse(c.since) : Date.now());

function task(id: string, title: string, bucket: Task['bucket'], why: string, link: string, state: FixtureState): Task {
  const saved = state.taskState.get(id);
  return { id, title, bucket, why, link, person: saved?.person ?? null, done: saved?.done ?? false, done_at: saved?.done_at ?? null, source: `rule:${id}` };
}

/** The gaps come from the same register and the same stock the household summary counts, so the
 * front door cannot say two different things about the same water. */
function readinessGaps(state: FixtureState): { title: string; link: string; points: number }[] {
  const gaps: { title: string; link: string; points: number }[] = [];
  const people = Math.max(1, state.household.length);
  const water = state.stock.filter((s) => s.category === 'water');
  const food = state.stock.filter((s) => s.category === 'food');
  const daysOf = (items: typeof state.stock) => items.reduce((n, i) => n + (i.days_left ?? 0), 0);
  if (state.household.length === 0) gaps.push({ title: 'Say who lives here', link: '/plan#household', points: 12 });
  if (water.length === 0) gaps.push({ title: 'No water recorded: add what you have', link: '/plan#stock', points: 12 });
  else if (daysOf(water) < 3) gaps.push({ title: `Water: ${daysOf(water).toFixed(1)} days for ${people} ${people === 1 ? 'person' : 'people'}`, link: '/plan#stock', points: 12 });
  if (food.length === 0) gaps.push({ title: 'No food recorded: add what you have', link: '/plan#stock', points: 8 });
  return gaps;
}

export function computeView(state: FixtureState, now = Date.now()): SituationView {
  const conditions = Object.fromEntries(CONDITION_IDS.map((id) => [id, aged(state.conditions[id], now)])) as Conditions;
  const off = (id: ConditionId) => conditions[id].state === 'off';
  const broken = (id: ConditionId) => conditions[id].state !== 'working';
  const power = conditions.power;

  const inferred: Inferred[] = [];
  if (off('power') && power.for_s >= 4 * 3600 && conditions.mobile.state === 'working') {
    inferred.push({
      condition: 'mobile', state: 'degraded', confidence: 0.7, due_at: new Date(sinceOf(power) + 4 * HOUR).toISOString(),
      why: 'Masts run about four hours on battery once the street power goes.', rule: 'power-off-mobile-degraded', source: 'page:what-still-works',
    });
  }

  // A reading never overrides what somebody said; it proposes, flagged as the box's own detection.
  const internet = state.sensors.internet;
  if (internet && internet.value === 0 && conditions.internet.state === 'working') {
    inferred.push({
      condition: 'internet', state: 'off', confidence: 0.8, due_at: internet.at, detected: true,
      why: 'The box has not reached the internet since ' + internet.at.slice(11, 16) + '.',
      rule: 'sensor:internet', source: 'page:what-still-works',
    });
  }

  const forecast: Forecast[] = [];
  if (off('power')) {
    const from = sinceOf(power);
    const item = (id: string, title: string, hours: number, severity: Forecast['severity'], why: string): Forecast => {
      const due = new Date(from + hours * HOUR).toISOString();
      return { id, title, due_at: due, severity: Date.parse(due) <= now ? 'passed' : severity, why, link: 'module:food', passed: Date.parse(due) <= now };
    };
    forecast.push(item('fridge', 'Fridge food unsafe', 4, 'warn', 'A closed fridge holds about four hours.'));
    forecast.push(item('phones', 'Phone batteries flat', 12, 'warn', 'Charge everything while the power lasts.'));
    forecast.push(item('freezer', 'Freezer food unsafe', 24, 'danger', 'A half-full freezer holds about 24 hours; a full one, 48.'));
    forecast.sort((a, b) => a.due_at.localeCompare(b.due_at));
  }

  const tasks: Task[] = [];
  if (off('power')) {
    if (!off('water')) tasks.push(task('fill-bath', 'Fill the bath and every container', 'now', 'Pumped supplies fail about a day after the power does.', 'module:water', state));
    tasks.push(task('freezer-shut', 'Keep the fridge and freezer doors shut', 'now', 'Every opening costs hours of cold.', 'module:food', state));
    tasks.push(task('cooker-off', 'Turn the cooker off at the knobs', 'now', 'It will come back on with the power.', 'module:power', state));
    tasks.push(task('cash', 'Get cash out while the shops can take it', 'hour', 'Card terminals need power.', 'page:what-still-works', state));
  }
  if (broken('water')) tasks.push(task('boil-water', 'Boil water before drinking it', 'today', 'Pressure loss lets dirt into the pipes.', 'page:water-disinfection', state));
  if (off('mobile') && off('landline')) tasks.push(task('meeting-point', 'Agree a meeting point and a runner', 'now', 'Nobody can ring anybody.', 'page:no-phones', state));
  if (state.situation.slug) {
    const list = state.checklists.get(state.situation.slug) ?? [];
    for (const item of list) {
      const id = `checklist:${state.situation.slug}/${item.id}`;
      tasks.push({ id, title: item.text, bucket: 'today', why: 'From this situation’s checklist.', link: `playbook:${state.situation.slug}`, person: state.taskState.get(id)?.person ?? null, done: item.checked, done_at: item.updated_at, source: `checklist:${state.situation.slug}` });
    }
  }
  // Phase 4: a neighbour who needs checking on is a job like any other, with the same id on both sides.
  const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const checkOn = (off('power') || off('water') || off('mobile'))
    ? state.neighbours.filter((n) => n.needs.trim()).map((n) => ({
        id: `neighbour:${slug(n.name)}`, name: n.name, address: n.address, needs: n.needs, contacts: n.contacts,
        title: `Knock on ${n.name}${n.address ? `, ${n.address}` : ''}`, why: n.needs,
        rule: `neighbour-check-${slug(n.name)}`, link: null, bucket: 'today' as const,
        done: state.taskState.get(`neighbour:${slug(n.name)}`)?.done ?? false,
      }))
    : [];
  const skills = state.neighbours.filter((n) => n.skills.trim()).map((n) => ({
    name: n.name, address: n.address, skill: n.skills, text: n.skills, contacts: n.contacts,
    why: 'On the street list.', rule: `neighbour-skill-${slug(n.name)}`, link: null,
  }));
  for (const c of checkOn) {
    tasks.push({ id: c.id, title: c.title, bucket: c.bucket, why: c.why, link: c.link, person: state.taskState.get(c.id)?.person ?? null, done: c.done, done_at: null, source: 'rule:neighbours' });
  }

  const order = { now: 0, hour: 1, today: 2, week: 3 };
  tasks.sort((a, b) => order[a.bucket] - order[b.bucket] || a.title.localeCompare(b.title));

  const briefing: SituationView['briefing'] = [];
  if (state.situation.slug) briefing.push({ title: 'Right now', kind: 'playbook-section', ref: `${state.situation.slug}#right-now` });
  if (broken('power')) {
    briefing.push({ title: 'Power', kind: 'module', ref: 'power' });
    briefing.push({ title: 'What still works in an outage', kind: 'page', ref: 'what-still-works' });
  }
  if (broken('water')) briefing.push({ title: 'Water', kind: 'module', ref: 'water' });

  const callsHidden = off('mobile') && off('landline');
  const scenario = state.situation.slug
    ? { slug: state.situation.slug, title: state.situation.title ?? state.situation.slug, started_at: state.situation.started_at, elapsed_s: Math.max(0, Math.round((now - Date.parse(state.situation.started_at)) / 1000)), phase: phaseFor(Math.max(0, (now - Date.parse(state.situation.started_at)) / 1000)).id }
    : null;

  return {
    meta: {
      now: new Date(now).toISOString(), dark: state.dark,
      sunrise: '2026-09-06T05:22:00.000Z', sunset: '2026-09-06T18:41:00.000Z',
      home: state.home, drill: state.drill,
    },
    scenario,
    conditions,
    inferred,
    forecast,
    tasks,
    briefing,
    modes: {
      theme: off('power') && state.dark ? 'mono' : null,
      dim: off('power') && state.dark,
      calls: callsHidden ? 'hidden' : 'shown',
      map_first: state.situation.slug === 'storms-flooding',
      board: Boolean(state.situation.slug),
    },
    readiness: { score: 62, gaps: readinessGaps(state) },
    bulletins: { next: { station: 'BBC Radio 4', frequency: '198 kHz LW', at: '2026-09-06T18:00:00.000Z' } },
    neighbours: { check_on: checkOn, skills },
  };
}

/** The hand-over sheet: what the print button opens. */
export function report(state: FixtureState): string {
  const view = computeView(state);
  const lines = ['# Situation report', '', `As at ${view.meta.now}.`, '', '## Conditions', ''];
  for (const id of CONDITION_IDS) lines.push(`- ${view.conditions[id].title}: ${view.conditions[id].state}`);
  lines.push('', '## Tasks', '');
  for (const t of view.tasks) lines.push(`- [${t.done ? 'x' : ' '}] ${t.title}`);
  return `${lines.join('\n')}\n`;
}
