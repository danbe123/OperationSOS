# Household, Stock and Situation simplification: design

Date: 2026-09-06. Status: approved in conversation (the owner: "all this is overcomplications and confusion"; the Stock critique and the proposal below were accepted; build without further gates).

## 1. What this is

Three screens rebuilt so that each one shows its state first and asks for input only when asked to.

- **Household** (`/plan`) becomes a hub: one row per thing the household keeps, each saying its state in one line and opening its own screen. No jump chips, no forms on the hub.
- **Stock** (`/plan/stock`) becomes a read-first list with a meter per category that says what you have, how long it lasts and what two weeks would need. Days are computed once, in the API, and used everywhere.
- **Situation** (`/situation`) becomes ten rows, one per service, with the timestamp and note asked for only on the row you change. The event log moves here.
- The situation band shrinks to one line.

Out of scope: the Board screen, the Tasks screen, the drill mechanics, the neighbours and pins data models, the engine's rules.

## 2. Household hub: `/plan`

Title "Household", back button, print button (prints the hub and every section's list, as the old page did). Under the title, a list of six link rows, each an icon, a title, one line of state, a chevron:

| Row | State line | Opens |
|---|---|---|
| People | "3 registered, 1 with medical needs" / "Nobody registered yet" | `/plan/people` |
| Neighbours | "2 on the street list" / "No neighbours listed" | `/plan/neighbours` |
| Stock | "Water 4 days · Food 3 days · Medicine none" / "Nothing tracked yet" | `/plan/stock` |
| The plan | "Meeting point set" / "No meeting point yet" | `/plan/plan` |
| Notes and pins | "5 notes, 2 pins" / "Nothing written down" | `/plan/notes` |
| What happened | "Last entry 14:20, Power off" / "No entries yet" | `/situation#log` |

The state lines come from the same API calls the sections already make (`household`, `neighbours`, `stock`, `notes`, the household-plan page), fetched by the hub. The hub carries no forms.

## 3. Sub-screens

Every sub-screen has the same shape: title with a back link to Household; the list first; one sentence when the list is empty; a single primary button ("Add a person", "Add a neighbour", "Add something else", "Add a note", "Add a pin") that reveals the form under it; the form hides again after a save or a Cancel. A row expands on tap to edit (the existing fields) and holds its Remove, behind the existing confirm. The section components already exist under `web/src/screens/plan/`; they are split into a list part and a form part rather than rewritten, and each becomes a screen.

- `/plan/people`: the household register (name, age, medical needs, medications, contacts).
- `/plan/neighbours`: the street list, keeping the "Printable street list" button.
- `/plan/plan`: the household-plan page rendered as it is on `/p/household-plan`, with the meeting point and contacts fields the old panel had.
- `/plan/notes`: notes and pins in one list, pins marked with the pin icon and their map link; the form has a "Pin on the map" toggle that adds the location field.
- `/plan/stock`: section 4.

The old `/plan` anchors (`#stock`, `#household`, `#notes`, `#pins`, `#log`) still resolve: the readiness gaps and the kits link to `/plan#stock` and `/plan#household`; the hub redirects an anchor to the sub-screen (`/plan#stock` → `/plan/stock`, `#household` → `/plan/people`, `#notes` and `#pins` → `/plan/notes`, `#log` → `/situation#log`).

## 4. Stock: `/plan/stock`

**Meters.** At the top, one meter per counted category, in this order: Water, Food, Medicine. A meter is a row: the category, the quantity held ("24 L"), the days ("4 days for 2 people"), the two-week need ("two weeks needs 84 L") and a progress line to the 14-day target. Fuel and Other have no meter; their rows just list. The people count is the register's, minimum one.

**Days, computed once.** `GET /stock` returns `days: {water, food, medicine}` and `people`. A category's days are the sum over its rows that have a rate and are not expired of `quantity / (rate × people)`, rounded to one decimal. Expired rows count for nothing and carry `expired: true`. The engine's model takes the same figures (`build_model_for` passes each row's `days_left` as the API computes it, zero when expired), so Stock, Now and the readiness score agree. The Now screen's "Household and stock" panel shows `days` from the API; `web/src/situation/board.ts` `stockDays` is deleted.

**Rates belong to the category.** The add form no longer asks for a rate. Defaults: water 3 L per person per day; food 1 person-day per person per day (the unit is "person-days": a day of meals for one person); medicine 1 day of supply per person per day (unit "days of supply"). Fuel and Other have no rate. A row's rate can still be changed in its expanded edit ("counts as 3 L per person a day"), which keeps the column and the API as they are.

**Rows.** One line per item: name, "24 L", a badge (days in green/amber/red as today, "expires in N days", or "expired"), and "from the Water kit" when `kit_item` is set (linking to the kit). Rows sort by category, then by days ascending (what runs out first at the top), then name. Tap expands to edit: quantity, use-by, rate, Remove behind confirm. The date is shown once, in the badge or the edit, never twice.

**Adding.** The kits are the front door ("Add to Stock" on a kit item fills name, category, unit and rate). On this screen a single "Add something else" button reveals Type, Item, Quantity (unit prefilled from the type and editable) and Use by.

## 5. Situation: `/situation`

Header: "Situation", back, the Board and Print report buttons as today. A one-line summary: "7 of 10 not working" or "Everything working".

**Ten rows**, one per service, in the engine's order. A row is: icon, the service name, its state chip with the duration ("off for 2 h"), and the three state buttons (Working, Patchy, Off) with the current one pressed. Nothing else is visible.

**Changing a state.** Tapping a different state expands that row only: "Since when?" with three choices, Just now, About an hour ago, Earlier (which reveals the date-time field), and Save / Cancel. Saving sends the existing `PUT /conditions/{id}` body. A row also has a small "Details" toggle that shows the note field, the "Set from kiosk at …" line and the detected/inferred source when there is one. The existing `ConditionRow` keeps its logic and loses its always-open fields.

**What happened.** Under the rows, a section with that heading holding the event log list (newest first, time and text) and an "Add an entry" button that reveals the one-line form. This is the same data the Tools "Event log" tile shows; that tile now opens `/situation#log`, and the old `/tools/log` route redirects there.

## 6. The band

One line at every width: on the left the scenario and its clock ("Nuclear war · 2 h in") or "Peacetime"; on the right one chip, "7 off" (or nothing when all is working), which opens `/situation`; the Drill control only while a drill runs ("End drill"). The per-service chips and the "+N more" expansion are removed. The kiosk rail is unaffected.

## 7. Tests

- Web unit tests: a hub test (six rows, state lines from fixtures, anchors redirect), one test per sub-screen (list first, empty sentence, button reveals form, save hides it, expand to edit), the stock meter and sorting, Situation rows (only the tapped row expands, the three since choices, Details toggle), the band (one line, the "N off" chip, no per-service chips), Now's panel using `days`.
- API tests: `GET /stock` `days` (sum, expired excluded, people scaling), the engine consuming the same figure.
- Existing tests that pin the old layout (`plan.test.tsx`, `plan-sections.test.tsx`, `situation.test.tsx`, `situation-sheet.test.tsx`, `shell.test.tsx`, `statusStrip.test.tsx`, `now.test.tsx`, `modes.test.tsx`, `board.test.tsx` where it touches the band) are rewritten to the new behaviour, not deleted.
- e2e specs that walk these screens (`situation.spec.ts`, `tick.spec.ts`, `screenshots.spec.ts`, `ux.spec.ts`) are updated for the new selectors; the suite is known stale in other areas and is not a merge gate.

## 8. Risks

- Links into `/plan#…` from rules and content are many; the redirect in section 3 covers them, and a grep for `/plan#` and `plan#` across `playbooks/rules`, `api/sos/engine.py` and `web/src` is part of the plan.
- The band is the most visible surface in the app; the change is small in code but every screen shows it. A screenshot at 853×480 and 390×844 before merge.
- Moving the event log changes a Tools tile; nothing else depends on `/tools/log`.
