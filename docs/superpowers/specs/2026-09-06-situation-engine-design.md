# The situation engine

Approved 2026-09-06 as the replacement for the "what is working" toggles. Extends the application spec and the tools spec; supersedes the services toggles (2026-09-05).

## 1. What it is

One shared model of the household's situation that every part of the box reads: the scenario and its clock, the state of each service, the household, the stock, the home location, what the box can sense, and time. A deterministic engine turns that model into a forecast, a task list, a briefing and a set of interface modes. Nothing in the app asks "what should I show?" without asking the engine.

Non-goals: mesh networking (a later plugin), speech recognition, anything needing the internet at runtime, medical decision-making beyond what the playbooks already say.

## 2. The model

### Conditions

| id | title | states |
|---|---|---|
| power | Mains power | working, degraded, off |
| water | Water supply | working, degraded, off |
| mobile | Mobile network | working, degraded, off |
| landline | Landline and 999 | working, degraded, off |
| internet | Internet | working, degraded, off |
| gas | Gas | working, degraded, off |
| heating | Heating | working, degraded, off |
| roads | Roads and transport | working, degraded, off |
| shops | Shops and cash | working, degraded, off |
| sewage | Sewage and drains | working, degraded, off |

Each condition row: `state`, `since` (ISO), `source` (`manual`, `detected`, `inferred`), `confidence` (0 to 1, 1 for manual), `note`, `set_by` (kiosk, phone, box), `updated_at`, `confirmed_at`. Home shows power, water, mobile, landline and internet; the situation sheet shows all ten.

A condition that has been off for 24 hours without `confirmed_at` moving is stale and the app asks whether it is still off. A change records an event in the log ("Mains power off since 14:20, set from a phone").

### Scenario and clock

Unchanged from the tools spec (`situation_slug`, `situation_started_at`), now part of the same model and sheet. A `drill` flag marks a simulated situation; every screen shows DRILL while it is set and the audit log tags entries as drill.

### Household, stock, home

Household and stock as built. Home is a setting (`home_lat`, `home_lon`, `home_label`, `home_flood_zone`), set from the map ("Set as home"), which also captures the flood zone under the point from the flood overlay when it is loaded.

### Sensors

A `sensor_readings` table (`sensor`, `value`, `unit`, `at`). Drivers in `sos.sensors`, each optional and configured by settings:
- `internet`: DNS and HTTP probe of a fixed host; result feeds `internet` as detected.
- `mains`: `/sys/class/power_supply/*/online` (UPS HATs) or a GPIO pin; feeds `power` as detected for the house.
- `hotspot_clients`, `cpu_temp`: from the existing system code.
- `file`: a number read from a path (any USB or I2C sensor script that writes one), typed by name: `temp_in`, `temp_out`, `humidity`, `pressure_hpa`, `co_ppm`, `radiation_usvh`, `leak`.
- `rtl_power`: if `rtl_power` is installed and a dongle is present, band energy for FM (87.5 to 108 MHz), DAB (174 to 240 MHz) and the 800 and 900 MHz mobile bands; presence feeds `mobile` (detected, degraded when the bands go quiet) and a `broadcast` reading.
- `rtl_fm`: records a named frequency for a bulletin window into `state/recordings/` when scheduled.

Detection never overrides a manual state set later than the reading; it proposes, with a prompt on the kiosk ("The box has lost the internet. Is the power off in the street too?").

## 3. Rules

`playbooks/rules/*.yaml`, validated by `playbooks/rules/schema.json`, each rule with a citation to a playbook, module, page or document. Kinds:

- **implication**: `when: {power: off}` → `expect: {mobile: degraded, after: 4h}` and `{mobile: off, after: 8h}`, `{shops: off, after: 0h}`, `{water: degraded, after: 24h, where: "pumped supplies"}`, `{sewage: degraded, after: 24h}`, `{heating: off, after: 0h, unless: "solid fuel"}`. Produces inferred conditions with confidence and a prompt to confirm.
- **consequence**: a countdown from a condition's `since`: fridge 4h, freezer 48h (24h if half full), phone batteries 12h, water in a combi or tank 3 days, hot water 1 day, medicines needing cold 24h, ventilators and concentrators from the household register's `needs`. Produces forecast items with `due_at` and severity.
- **task**: a task template with `when` conditions, optional household or stock predicates (`needs: insulin`, `stock: water < 3 days`), a priority bucket (now, hour, today, week), a title, a why, a link, and `until` (a condition change that retires it). Playbook checklist items are imported as task templates keyed to their scenario, with `when` defaulting to the scenario being active.
- **mode**: interface changes: `when: {power: off, dark: true}` → `theme: blackout, dim: true`; `when: {landline: off, mobile: off}` → `calls: hidden`; `when: {scenario: storms-flooding}` → `map_first: true`.
- **reading**: what to open: `when` → pages, modules, playbook sections.

The engine loads rules once (mtime cached) and evaluates them in order; rules are pure data and every rule has a test.

## 4. The engine (`sos.engine`)

`compute(model, now) -> View`, deterministic, no side effects. View fields:

- `conditions`: effective states (manual over detected over inferred), each with `since`, `for_s`, `source`, `stale`.
- `inferred`: proposed changes awaiting confirmation.
- `forecast`: items sorted by `due_at`, each `{id, title, due_at, severity, why, link}`; overdue items stay with `severity: passed`.
- `tasks`: `{id, title, bucket, why, link, person, done, done_at, source}`; done state from the `task_state` table; retired tasks are dropped.
- `briefing`: ordered sections `{title, kind, ref, html?}` compiled from reading rules, the scenario's current phase section, and the modules the conditions call for; includes sun times for home and the next radio bulletin.
- `modes`: `{theme, dim, calls, map_first, board}`.
- `readiness`: score 0 to 100 with gap list, computed in peacetime from stock days, household needs coverage, plan completeness and the last drill.
- `meta`: `{now, dark, sunrise, sunset, home, drill}`.

Endpoints: `GET /situation/view` (the View), `PUT /conditions/{id}` `{state, since, note}`, `POST /conditions/{id}/confirm`, `POST /conditions/{id}/accept` (take an inferred state), `PUT /tasks/{id}` `{done?, person?}`, `PUT /home`, `POST /drill` `{scenario, conditions}` and `DELETE /drill`, `GET /situation/report` (markdown), `GET /sensors`. `/status` carries `conditions` (effective) and `modes` so the chrome needs nothing else.

## 5. Content directives

Markdown may contain `{{#if <cond>}} … {{else}} … {{/if}}` and `{{#unless <cond>}} … {{/unless}}` where `<cond>` is `power`, `water`, `mobile`, `landline`, `internet`, `gas`, `heating`, `roads`, `shops`, `sewage`, `phones` (mobile or landline working), `dark`, or `scenario:<slug>`. The renderer evaluates them against the View before Markdown rendering; rendered output is cached per (document mtime, condition signature). The validator renders every branch and checks links in each. Inline shortcuts: `[[call 999]]` renders "call 999" with phones working and "999 will not connect: [get help without phones](page:no-phones)" without. Every quick card's Stop or escalate section and every playbook Right now section that names a number uses the directives. The number tagging is removed.

## 6. Interface

- **Home**: the situation strip (scenario, clock, five conditions as green, amber or red chips), then the briefing: forecast items due soon, the now and hour tasks, inferred prompts, then the tools and the scenario grid. In peacetime the strip shows the readiness score and its top gap.
- **Situation sheet** (`/situation`, and from the chrome chip on every screen): conditions with a since-when picker and note, inferred proposals with accept and dismiss, the clock, the drill switch, sensors, the printable report.
- **Tasks** (`/tasks`): buckets, assignment to household members, tick from any phone, why and link on each.
- **Board** (`/board`): the kiosk's screen while a situation is active or when idle with something off: conditions and clocks, the next three tasks and who has them, sunset, the next bulletin, the stock countdown, the last events. Large type, refreshes every 30 s, a tap returns to Home.
- **Modes**: applied in the theme provider and the chrome: blackout and dim when the mode says so; call buttons and phone numbers hidden or swapped when `calls: hidden`; the map first on Home when `map_first`.
- **Map**: "Set as home"; nearest facilities panel (emergency department, pharmacy, fuel, water works, fire station, rest centre from the health, fuel and water overlays and a `places` search) with distance and walking time; "Route home" and "Route to" draw straight-line bearings with Naismith times (no routing engine).
- **Read aloud**: a speaker button on the briefing and on any page; `POST /speak` runs Piper with a bundled British voice and returns WAV; the kiosk plays it. Piper and its voice are manifest items (`ai` category, `piper` and `piper-voice-en_GB`).
- **Radio**: the comms pages carry a bulletin schedule (`playbooks/rules/bulletins.yaml`); the board shows the next one; with the dongle present the box records it.

## 7. Readiness and drills

`POST /drill` starts a drill: a scenario plus a set of conditions with `since` in the past, flagged `drill`. The engine runs as normal; the board says DRILL; tasks tick as normal into `task_state` with `drill: true`; `DELETE /drill` ends it and writes a summary event (tasks done, time taken). The readiness score is recomputed nightly and on every stock or household change: 40 points stock (water, food, medicine days against 3, 7 and 14), 30 points household coverage (each need with a task template and a stock item), 20 points plan (home set, meeting point in the plan page, contacts), 10 points practice (a drill in the last 6 months).

## 8. Community

`neighbours` table (name, address, needs, skills, contacts, notes). Reading rules and task rules can target neighbours (`needs: oxygen` → "Check on Mrs Khan at number 12"). A printable street list. Situation report export and import as JSON, shown as a QR sequence on one phone and scanned by another (the box's camera-free path is a text paste).

## 9. Audit and reports

Every condition, task, home, drill and neighbour change is an event with actor (kiosk, phone, box, drill) and time. `GET /situation/report` renders the current view and the event log since the situation started as Markdown for print or hand-over. Conflicts: every write carries the row's `updated_at` it was based on; a stale write is refused with the current row.

## 10. Testing

- Rule files validated against the schema; every rule has a unit test in `test_rules.py` built from the file (parametrised).
- Golden views: fixed model plus fixed clock → expected forecast, tasks and modes.
- A simulator (`tests/simulate.py`) walks random condition changes over synthetic days and asserts invariants: no exceptions, determinism (same input, same view), no task whose `until` has fired, no forecast without a due time, no instruction naming a dead number in rendered content.
- Content: every document rendered for the eight condition signatures the validator enumerates.
- Frontend: screen tests for the strip, sheet, tasks, board and modes; Playwright: a drill from Home through the board.

## 11. Phases

1. Model, rules, engine, view endpoint, conditions and tasks API, directives with validation, content pass on numbers, Home strip and briefing, situation sheet, chrome chip, tasks screen. Removes the services toggles.
2. Forecast and reminders on the kiosk, board, modes, home location and nearest facilities, readiness score, drills.
3. Sensors (probe, mains, file, rtl_power, rtl_fm), inferred prompts, bulletins and recording, read aloud with Piper.
4. Neighbours, street list, who to check on, report export and import, the simulator in CI, hardware notes in the checklist.
