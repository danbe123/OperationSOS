# Household, Stock and Situation Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Household as a hub with sub-screens, Stock as a read-first list with category meters and one days figure computed in the API, Situation as ten rows with the event log beneath, and the band as one line.

**Architecture:** The existing section components under `web/src/screens/plan/` are split into a list part and a form part and mounted on their own routes; the hub reads the same API calls to write one state line per row; `GET /stock` gains `days` (sum per category over non-expired rows) and the engine consumes the same figure so Stock, Now and the score agree; `ConditionRow` keeps its save logic and loses its always-open fields; the band drops the per-service chips.

**Tech Stack:** Python 3.12 + FastAPI + SQLite (api/), React 19 + react-router 7 + Vite + vitest + testing-library (web/).

**Spec:** `docs/superpowers/specs/2026-09-06-household-simplification-design.md`. Code map used to write this plan: `.superpowers/household-context.md` (line numbers there are as of commit a0ab057).

## Global Constraints

- Repo root `/home/dan/OperationSOS`, branch `main`, tree clean at `51bbc8e`. Commit after every task with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; stage files by name.
- Commands: API `api/.venv/bin/python -m pytest api/tests -q`; web `pnpm --dir web exec tsc --noEmit` and `pnpm --dir web test`; a single file `pnpm --dir web exec vitest run <path>`. The e2e suite is stale in other areas and is not a gate; update the specs named in each task only where the task changes what they select.
- British English in every string. No new tokens, radii or shadows: reuse `.panel`, `.list`, `.row`, `.field`, `.btn`, `.btn-small`, `.btn-primary`, `.btn-danger`, `.badge`, `.badge-ok|warn|danger`, `.chip`, `.muted`, `--touch` (48 px).
- The old anchors keep working: `/plan#stock` → `/plan/stock`, `/plan#household` → `/plan/people`, `/plan#notes` and `/plan#pins` → `/plan/notes`, `/plan#log` → `/situation#log`. `web/tests/screens/plan-sections.test.tsx`'s Medical assertion (`Edit the register` → `/plan#household`) must keep passing.
- Category rates: water 3 L per person-day; food 1 person-day; medicine 1 day of supply; fuel and other none. Day thresholds for tone: `< 3` danger, `< 7` warn, else ok (as `daysBadge` today). Two-week target = 14 days.
- Every form sits behind a button and hides after a successful save or Cancel; a list's empty state is one sentence plus that button.

---

## File map

| File | Responsibility after this plan |
|---|---|
| `api/sos/routers/household.py` | `GET /stock` returns `people`, `days: {water, food, medicine}`, rows with `expired`; `stock_days_by_category(rows, people)` helper |
| `api/sos/routers/situation.py` | `build_model_for` passes `days_left` 0 for expired rows |
| `web/src/api/types.ts`, `client.ts` | `StockResponse.days`, `StockItem.expired` |
| `web/src/shell/SituationBand.tsx` | one line: scenario/clock, "N off" chip, drill control |
| `web/src/situation/ConditionRow.tsx` | collapsed row; since choices on change; Details toggle |
| `web/src/screens/Situation.tsx` | ten rows, "What happened" section with the event log |
| `web/src/screens/plan/EventLog.tsx` | `EventLogList` and `EventLogForm` (button-revealed) |
| `web/src/screens/tools/Log.tsx`, `Tools.tsx` | redirect to `/situation#log`; tile points there |
| `web/src/screens/plan/Household.tsx`, `Neighbours.tsx`, `Notes.tsx`, `Pins.tsx` | list + button-revealed form; exported list/form parts |
| `web/src/screens/plan/People.tsx`, `NeighboursScreen.tsx`, `NotesScreen.tsx`, `PlanPage.tsx` (new) | the sub-screens |
| `web/src/screens/plan/StockScreen.tsx` (new), `Stock.tsx` | meters, sorted rows, expand-to-edit, "Add something else" |
| `web/src/screens/Plan.tsx` | the hub: six rows, anchor redirect |
| `web/src/screens/Now.tsx`, `web/src/situation/board.ts`, `BoardView.tsx` | use `days` from the API; `stockDays` deleted |
| `web/src/router.tsx` | new routes |
| `web/src/screens/plan/plan.css` (new) | hub rows, meters, the collapsed condition row bits that `situation.css` does not cover |
| Tests as listed per task | |

---

### Task 1: `GET /stock` computes days once; the engine uses the same figure

**Files:**
- Modify: `api/sos/routers/household.py`, `api/sos/routers/situation.py`
- Test: `api/tests/test_household.py`, `api/tests/test_engine.py` (only if a golden changes), `api/tests/test_api.py` (key set for stock rows if asserted)

**Interfaces:**
- Produces: `stock_days_by_category(rows: list[dict], people: int, today: date | None = None) -> dict[str, float]` in `household.py`; `_item(...)` gains `expired: bool`; `GET /stock` → `{people, days: {water, food, medicine}, items}`.

- [ ] **Step 1: Failing tests**

Append to `api/tests/test_household.py`:

```python
def test_stock_days_sum_per_category_and_ignore_expired(client):
    client.post("/api/household", json={"name": "Dan"})
    client.post("/api/household", json={"name": "Sam"})
    client.post("/api/stock", json={"name": "Bottles", "category": "water", "quantity": 12, "unit": "L"})            # rate defaults to 3
    client.post("/api/stock", json={"name": "Butt", "category": "water", "quantity": 12, "unit": "L"})
    client.post("/api/stock", json={"name": "Tins", "category": "food", "quantity": 6, "unit": "person-days"})      # rate defaults to 1
    client.post("/api/stock", json={"name": "Old pills", "category": "medicine", "quantity": 14, "unit": "days of supply", "expires": "2020-01-01"})
    client.post("/api/stock", json={"name": "Gas", "category": "fuel", "quantity": 2, "unit": "canisters"})
    body = client.get("/api/stock").json()
    assert body["people"] == 2
    assert body["days"] == {"water": 4.0, "food": 3.0, "medicine": 0.0}
    rows = {r["name"]: r for r in body["items"]}
    assert rows["Bottles"]["days_left"] == 2.0 and rows["Bottles"]["expired"] is False
    assert rows["Old pills"]["expired"] is True and rows["Old pills"]["days_left"] == 0.0
    assert rows["Gas"]["days_left"] is None and rows["Gas"]["per_person_day"] is None


def test_readiness_ignores_expired_stock(client):
    client.post("/api/household", json={"name": "Dan"})
    client.post("/api/stock", json={"name": "Old pills", "category": "medicine", "quantity": 140, "unit": "days of supply", "expires": "2020-01-01"})
    gaps = client.get("/api/situation/view").json()["readiness"]["gaps"]
    assert any(g["title"].startswith("Medicine: 0 days") for g in gaps)
```

- [ ] **Step 2: Run to see them fail**

`api/.venv/bin/python -m pytest api/tests/test_household.py -q -k "days or expired"` → FAIL (`days` missing; medicine rate not defaulted; expired not present).

- [ ] **Step 3: Implement**

In `api/sos/routers/household.py`:

```python
DEFAULT_PER_PERSON_DAY = {"water": 3.0, "food": 1.0, "medicine": 1.0}   # L, person-days, days of supply
COUNTED = ("water", "food", "medicine")


def is_expired(expires: Optional[str], today: Optional[date] = None) -> bool:
    if not expires:
        return False
    try:
        return date.fromisoformat(expires[:10]) < (today or date.today())
    except ValueError:
        return False


def _item(r, people: int, content=None) -> dict:
    expired = is_expired(r["expires"])
    dl = days_left(r["quantity"], r["per_person_day"], people)
    return {"id": r["id"], "name": r["name"], "category": r["category"], "quantity": r["quantity"], "unit": r["unit"],
            "per_person_day": r["per_person_day"], "expires": r["expires"], "notes": r["notes"] or "",
            "updated_at": r["updated_at"], "kit_item": r["kit_item"], "kit_title": _kit_title(content, r["kit_item"]),
            "expired": expired, "days_left": (0.0 if expired and dl is not None else dl)}


def stock_days_by_category(items: list[dict], people: int) -> dict[str, float]:
    """One figure per counted category: the sum of days over rows that have a rate and are not expired."""
    out = {c: 0.0 for c in COUNTED}
    for i in items:
        if i["category"] in out and i["days_left"] is not None and not i["expired"]:
            out[i["category"]] += i["days_left"]
    return {c: round(v, 1) for c, v in out.items()}
```

`list_stock` returns `{"people": people, "days": stock_days_by_category(items, people), "items": items}`. `add_stock` already defaults the rate from `DEFAULT_PER_PERSON_DAY`; keep that. Add `from datetime import date`.

In `api/sos/routers/situation.py` `build_model_for`, where `stock` rows are built for the model (grep `days_left`), use `household._item(r, people, content)` (import the helper) so the engine sees the same `days_left`, including `0.0` for expired rows.

- [ ] **Step 4: Run** `api/.venv/bin/python -m pytest api/tests -q -x` → pass. If `api/tests/test_api.py` asserts the exact key set of a stock row, add `expired`.

- [ ] **Step 5: Commit** `git add api/sos/routers/household.py api/sos/routers/situation.py api/tests/test_household.py [api/tests/test_api.py]` — `feat(stock): one days figure per category from the API, expired rows count for nothing`.

---

### Task 2: The band is one line

**Files:**
- Modify: `web/src/shell/SituationBand.tsx`, `web/src/styles/shell.css` (band rules only)
- Test: `web/tests/shell/shell.test.tsx` ("the situation band" block), `web/tests/screens/drill.test.tsx`, `web/e2e/situation.spec.ts` (the band selectors only)

**Interfaces:** the band renders `<div className="band no-print" role="group" aria-label="Situation now">` with, in order: drill badge + `EndDrillButton` when drilling; `Link.band-scenario` to `/s/<slug>` with title and `describeElapsed` when a scenario runs, else nothing; `Link.btn.btn-small.band-off` to `/situation` reading `"7 off"` (or `"1 off"`) when anything is broken; `Link.band-jobs` "N to do" as today. No `ConditionChip`s, no `band-more`, no `band-open`. The band still returns `null` when nothing is broken, no scenario and no drill.

- [ ] **Step 1: Failing tests** — rewrite the band block in `shell.test.tsx`: on phone and on kiosk widths the link texts are exactly `[<scenario title…>, '2 off', '3 to do']`; the "2 off" link has href `/situation`; `queryByRole('link', { name: /Mains power/ })` is null at both widths; band absent when everything works. `drill.test.tsx`: "Drill" badge and "End drill" still inside the band.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** implement: delete `chipBudget`, the chip rendering, `band-more` and `band-open`; add `band-off`. Remove `useWide` if now unused. In `shell.css` drop `.band-chips` rules that become dead; keep the band one row (`flex-wrap: nowrap; overflow: hidden`).
- [ ] **Step 4:** `pnpm --dir web exec vitest run tests/shell tests/screens/drill.test.tsx` → pass; then `pnpm --dir web test`.
- [ ] **Step 5:** in `web/e2e/situation.spec.ts` replace the band chip expectation (`/Mains power: off for 1 h/`) with `getByRole('link', { name: '1 off' })`.
- [ ] **Step 6: Commit** — `feat(shell): the band is one line`.

---

### Task 3: Situation rows, and the event log moves under them

**Files:**
- Modify: `web/src/situation/ConditionRow.tsx`, `web/src/situation/since.ts`, `web/src/screens/Situation.tsx`, `web/src/screens/plan/EventLog.tsx`, `web/src/screens/tools/Log.tsx`, `web/src/screens/Tools.tsx`, `web/src/styles/situation.css` (or wherever `.cond-row` lives)
- Test: `web/tests/screens/situation-sheet.test.tsx`, `web/tests/screens/tools.test.tsx`, `web/tests/screens/plan-sections.test.tsx` (event log part moves to a new `web/tests/screens/situation-log.test.tsx`)

**Interfaces:**
- `ConditionRow` props unchanged (`condition, onSaved, open, onOpen`). Collapsed row markup: `li.cond-row` > `.cond-row-head` (icon, `h3` title, state badge, "for 2 h") and `.row.cond-states[role=group][aria-label=title]` with the three state buttons, always visible. Tapping a button whose state differs from the current one opens `.cond-since` on that row only: three radio-style buttons "Just now", "About an hour ago", "Earlier" (Earlier reveals the existing custom time field), "Save" (`btn-primary`) and "Cancel"; Save calls `save(pendingState, choice, custom)` with the existing body shape. A "Details" toggle button (`aria-expanded`) at the end of the head reveals the note field with "Save note", the `cond-meta` line and the stale prompt. The since options shrink to `SinceChoice = 'now' | 'hour' | 'custom'` with labels "Just now", "About an hour ago", "Earlier" (`since.ts`; `sinceChoiceFor` maps morning/yesterday to `custom`).
- `EventLog.tsx` exports `EventLogList()` (the list, newest first, with Edit/Delete as today) and `EventLogForm({ onAdded })` (the one-line form); default `EventLog` renders list + a button "Add an entry" that reveals the form and hides it after "Log it".
- `Situation.tsx`: after the rows and the print table, `<section className="panel" id="log" aria-label="What happened"><h2>What happened</h2><EventLog /></section>`; the sensors, clock, export and drill sections stay below. `Log.tsx` becomes `<Navigate to="/situation#log" replace />`; the Tools tile "Event log" points to `/situation#log`.

- [ ] **Step 1: Failing tests** — rewrite `situation-sheet.test.tsx` to the new behaviour: ten listitems each with the three state buttons visible and the current one `aria-pressed`; no "Change" button; clicking "Off" on Mains power shows the group "Mains power: since when?" with the three choices and Save/Cancel, and nothing opens on Water; choosing "About an hour ago" then Save calls `setCondition('power', {state:'off', since: <about an hour before now>, note: '', expected_updated_at})`; Cancel closes without a call; "Details" reveals the note field and "Set from kiosk at …"; the stale prompt is visible only under Details; deep link `/situation#water` opens Water's Details; the drill flow assertions stay. New `situation-log.test.tsx`: the "What happened" region lists events newest first, "Add an entry" reveals the form, "Log it" calls `createNote({kind:'event', title})` and hides the form. `tools.test.tsx`: the Event log tile href is `/situation#log`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** implement. Keep `save`, the 409 handling and `confirm()` untouched. The pending state lives in `useState<ConditionState | null>`; Save clears it. Keep `.state-set`/`.state-glyph` on the chosen button.
- [ ] **Step 4:** `pnpm --dir web exec vitest run tests/screens/situation-sheet.test.tsx tests/screens/situation-log.test.tsx tests/screens/tools.test.tsx tests/screens/board.test.tsx` → pass; `pnpm --dir web test`.
- [ ] **Step 5:** `web/e2e/situation.spec.ts` `openCondition` helper: no "Change" button; select the state button directly, then "Just now", then "Save".
- [ ] **Step 6: Commit** — `feat(situation): ten rows, since-when on the row you change, the log beneath`.

---

### Task 4: Sections become list-plus-button, and get their own screens

**Files:**
- Modify: `web/src/screens/plan/Household.tsx`, `Neighbours.tsx`, `Notes.tsx`, `Pins.tsx`
- Create: `web/src/screens/plan/People.tsx`, `NeighboursScreen.tsx`, `NotesScreen.tsx`, `PlanPage.tsx`, `web/src/screens/plan/plan.css`
- Modify: `web/src/router.tsx`
- Test: `web/tests/screens/neighbours.test.tsx`, `web/tests/screens/plan.test.tsx` (notes part → `notes.test.tsx`), new `people.test.tsx`

**Interfaces:**
- Each section module exports `<X>List` (renders `ul.list[aria-label]` of rows with inline edit and confirm-remove, and the one-sentence empty state) and `<X>Form` (the existing form, with `onSaved`/`onCancel`), and a default section component that composes list + an "Add …" button revealing the form. Section components no longer render `section.panel` with `h2`; the screens do.
- Screens: `People` at `/plan/people` (`Screen title="People"`, back to `/plan`): sentence "Who lives here, what they need and who to call. Medical needs also show on the Medical screen.", `HouseholdList`, button "Add a person". `NeighboursScreen` at `/plan/neighbours` ("Neighbours", "Printable street list" action, the "What the street can do" panel when present, list, button "Add a neighbour"). `NotesScreen` at `/plan/notes` ("Notes and pins"): one list of notes and pins by `updated_at` desc, pins with the pin icon, map link and grid ref; button "Add a note" reveals the note form which has a checkbox "Pin it on the map" revealing the existing lat/lon or map-pick affordance if one exists, else the note is a plain note. `PlanPage` at `/plan/plan` ("The plan"): the household-plan page HTML as today.
- `plan.css`: `.hub-rows` and `.hub-row` (a `Link` styled like a `.quick-card`: icon, title, state line, chevron, min-height `--touch`), `.meter` rules for Task 5, `.reveal` for the button+form pattern if needed.

- [ ] **Step 1: Failing tests** — `people.test.tsx`: `/plan/people` shows the list with "Sam" and "salbutamol inhaler"; no form until "Add a person" is pressed; after "Add person" the form hides and `addPerson` was called with the same payload the old test asserted. `neighbours.test.tsx`: same shape on `/plan/neighbours` (keep its exact field labels and call args). `notes.test.tsx`: `/plan/notes` lists the note and the pin (link to `/map?…`), "Add a note" reveals the form, the old add/edit/delete flow passes.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run the four test files, then `pnpm --dir web test`.
- [ ] **Step 5: Commit** — `feat(household): people, neighbours, notes and the plan on their own screens`.

---

### Task 5: The hub

**Files:**
- Modify: `web/src/screens/Plan.tsx`, `web/src/router.tsx`, `web/src/shell/destinations.ts` (comment only if the `starts('/plan')` match already covers sub-routes; it does)
- Test: `web/tests/screens/plan.test.tsx` (rewritten as the hub test), `web/tests/screens/plan-sections.test.tsx` (the Medical assertion stays; the rest moves to the sub-screen tests or is deleted)

**Interfaces:** `Plan()` renders `Screen title="Household"` with `PrintButton`; on mount, if `location.hash` is one of the old anchors it `navigate(target, { replace: true })` per the Global Constraints table; otherwise it fetches `api.household()`, `api.neighbours()`, `api.stock()`, `api.notes('note')`, `api.notes('pin')`, `api.notes('event')` and renders `nav.hub-rows[aria-label="Household"]` of six `Link.hub-row`s:

```tsx
export function stateLines(d: { people: Person[]; neighbours: Neighbour[]; stock: StockResponse | null; notes: Note[]; pins: Note[]; events: Note[]; meeting: boolean }): Record<string, string> {
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
```

`meeting` is true when any note or pin title matches `/meeting point/i` (the same test the engine uses for `meeting_point`; grep `meeting` in `api/sos/routers/situation.py` and mirror it). Rows: People → `/plan/people`, Neighbours → `/plan/neighbours`, Stock → `/plan/stock`, The plan → `/plan/plan`, Notes and pins → `/plan/notes`, What happened → `/situation#log`. Print: the hub's print button prints the six rows; the sub-screens have their own print buttons.

- [ ] **Step 1: Failing tests** — `plan.test.tsx`: `/plan` shows the six links in order with their state lines from fixtures ("2 registered, 1 with medical needs", "Water 4 days · Food 3 days · Medicine none", "1 note, 1 pin"…); no forms on the page (`queryByRole('form')` null); `/plan#stock` ends at `/plan/stock`, `/plan#household` at `/plan/people`, `/plan#log` at `/situation#log` (assert `router.state.location`). Keep the Medical `Edit the register` → `/plan#household` assertion where it lives.
- [ ] **Step 2:** FAIL. **Step 3:** implement (delete `JUMPS`, the chips and the section mounts). **Step 4:** tests green. **Step 5: Commit** — `feat(household): the hub`.

---

### Task 6: Stock screen with meters; Now and the Board use the API's days

**Files:**
- Create: `web/src/screens/plan/StockScreen.tsx`
- Modify: `web/src/screens/plan/Stock.tsx` (becomes list, row, meters, form parts), `web/src/api/types.ts`, `web/src/screens/Now.tsx`, `web/src/situation/BoardView.tsx` (if it uses `stockDays`), `web/src/situation/board.ts` (delete `stockDays`), `web/src/router.tsx`, `web/src/screens/plan/plan.css`
- Test: `web/tests/screens/stock.test.tsx` (rewritten), `web/tests/screens/now.test.tsx`, `web/tests/screens/board.test.tsx`, `web/tests/fixtures/api.ts` (`stockResponse` gains `days` and `expired`)

**Interfaces:**
- Types: `StockItem.expired: boolean`; `StockResponse = { people: number; days: { water: number; food: number; medicine: number }; items: StockItem[] }`.
- `RATE_BY_CATEGORY = { water: { rate: 3, unit: 'L' }, food: { rate: 1, unit: 'person-days' }, medicine: { rate: 1, unit: 'days of supply' } }`; fuel `unit: 'L'`, other `unit: ''`, no rate.
- Meters (exported for the test):

```tsx
export function meter(c: 'water' | 'food' | 'medicine', stock: StockResponse): { title: string; held: string; days: number; need: string; fraction: number } {
  const { rate, unit } = RATE_BY_CATEGORY[c];
  const rows = stock.items.filter((i) => i.category === c && !i.expired);
  const held = rows.reduce((n, i) => n + i.quantity, 0);
  const days = stock.days[c];
  const needQty = rate * stock.people * 14;
  return { title: { water: 'Water', food: 'Food', medicine: 'Medicine' }[c], held: `${held} ${unit}`.trim(), days, need: `two weeks needs ${needQty} ${unit}`.trim(), fraction: Math.min(1, days / 14) };
}
```
Rendered as `ul.meters[aria-label="Stock meters"]` of `li.meter` with `strong` title, "24 L · 4 days for 2 people · two weeks needs 84 L" (people word singular/plural), and `<progress className="progress-line" value={days} max={14} aria-label={`${title} against two weeks`} />`.
- Sorting (exported): `sortStock(items)` by category order water, food, medicine, fuel, other; then `days_left` ascending with `null` last; then name.
- Rows: `li.stock-row` collapsed: name, quantity + unit, `daysBadge` (unchanged, plus `expired` from the row), "from the Water kit" link; a "Change" button (`aria-label="Change {name}"`) expands the edit: quantity, use-by, "counts as N {unit} per person a day" (rate), Save, Remove (confirm as today). The date is never shown outside the badge or the edit.
- Adding: button "Add something else" reveals the form: Type, Item, Quantity, Unit (prefilled from type), Use by. No rate field; `per_person_day` is omitted from the POST so the API default applies.
- `StockScreen` at `/plan/stock`: `Screen title="Stock"`, sentence "Days are for {people} on the register. Water counts drinking and basic hygiene at 3 litres a person a day; food in person-days; medicine in days of supply.", meters, list, button.
- Now: `HouseholdSummary` reads `stock.data.days` and renders the three categories with the existing badge tones and the link `to="/plan/stock"`; `stockDays` deleted; `BoardView`'s "Stock left" list uses the same `days`.

- [ ] **Step 1: Failing tests** — `stock.test.tsx`: meters text for the fixture ("12 L · 4 days for 2 people · two weeks needs 84 L"), an expired row shows "expired" and is not in the meter's held quantity, rows sorted with the shortest run first, "Change Bottled water" reveals the edit and Save calls `updateStock(id, {quantity})`, kit link kept, "Add something else" reveals the form and `addStock` is called without `per_person_day`. `now.test.tsx`: the panel shows "Water 4 days" from `days` and links to `/plan/stock`. `board.test.tsx`: "Stock left" unchanged text from `days`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** the four test files, then `tsc` and `pnpm --dir web test`. **Step 5: Commit** — `feat(stock): meters, one days figure, read-first rows`.

---

### Task 7: Redirects, docs, verification, screenshots

**Files:**
- Modify: `web/src/router.tsx` (route `tools/log` → `Navigate`), `docs/superpowers/specs/2026-09-06-interface-redesign.md` (the `/plan` and `/situation` rows of the screen table), `README.md` if it names the plan sections
- Test: none new

- [ ] **Step 1:** grep `plan#` in `playbooks/rules`, `api/sos/engine.py`, `web/src` and confirm every target is covered by the hub redirect; grep `/tools/log`.
- [ ] **Step 2:** run everything: `api/.venv/bin/python -m pytest api/tests -q`, `pnpm --dir web exec tsc --noEmit`, `pnpm --dir web test`, `api/.venv/bin/ruff check api/sos/routers/household.py api/sos/routers/situation.py`.
- [ ] **Step 3:** `pnpm --dir web build`; restart the stack (`kill -TERM $(pgrep -f 'run-dev\.[s]h')`, wait 3 s, `(SOS_MANIFEST_DIR=/home/dan/OperationSOS/.dev/full-manifest setsid nohup dev/run-dev.sh > .dev/run-dev.log 2>&1 < /dev/null &)`, poll `/api/stock`); screenshot `/plan`, `/plan/stock`, `/situation` and `/` at 853×480 (`?kiosk=1`) and 390×844 with the Playwright snippet used in the kits plan (Chromium at `~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome`, `LD_LIBRARY_PATH=$HOME/.local/chromium-deps/usr/lib/x86_64-linux-gnu`, script placed under `web/` so `@playwright/test` resolves) into `docs/screenshots/2026-09-06-household/`. Do not change the box's conditions; do not leave stock rows you added.
- [ ] **Step 4: Commit** — `docs: household, stock and situation screens`.

---

## Self-review notes

- Spec §2 → Task 5; §3 → Task 4 (+ the redirect in Task 5); §4 → Tasks 1 and 6; §5 → Task 3; §6 → Task 2; §7 → the tests in each task. The spec's "Notes and pins" pin-creation affordance depends on what `Pins`/the map already offer; Task 4 keeps the map's "drop a pin" path and adds no new geolocation UI.
- Names used across tasks: `StockResponse.days`, `StockItem.expired`, `RATE_BY_CATEGORY`, `meter`, `sortStock`, `stateLines`, `EventLogList`/`EventLogForm`, routes `/plan/people|neighbours|stock|plan|notes`, anchor `#log` on `/situation`.
