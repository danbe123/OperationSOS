# Tools: stock, household, doses, situation clock, timers, sun and moon, calculators, event log

Design for the tool expansion agreed on 2026-09-05. Extends the application spec (`2026-09-03-operation-sos-design.md`); nothing here changes the content, search, map or AI sections.

## 1. Why

The five Home tiles are Medical, Maps, Library, Phone and radio, Plan. Everything behind them is reading except the shared checklist, notes and pins. During an event people need to manage things (stock, people, time) and do sums (doses, runtimes, daylight). This adds those as small offline tools that use structure the app already has.

Non-goals: mesh radio, sensors, photo identification, live data (tides, forecasts), weight-based paediatric dosing, checklist due-dates (checklist items carry no phase metadata yet).

## 2. Navigation

- Home gets a sixth tile after Plan: **Tools** (icon `hammer`, subtitle "Timers, sun, sums, log"). The tiles grid already wraps.
- `/tools` lists: Timers (`/tools/timers`), Sun and moon (`/tools/sun`), Calculators (`/tools/calc`), Event log (`/tools/log`), Children's doses (`/medical/dose`), Stock (`/plan#stock`).
- `/medical` gains a **Children's doses** tile in the NHS A to Z row and a **Household** panel (people with medical needs or medications) when the register has any, linking to `/plan#household`.
- `/plan` sections in order: Household, Stock, Household plan (existing page), Shared notes, Pins, Event log. Each has an `id` anchor.
- `/s/:slug` gains the situation clock in the intro strip.

Design rules from the main spec apply: 48px targets, plain body text, an icon always has a word, warnings use colour plus a symbol.

## 3. Data (sos-api, SQLite)

New tables in `db.py` `SCHEMA` (all `CREATE TABLE IF NOT EXISTS`, so existing boxes migrate on start):

```
household (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER, needs TEXT, medications TEXT,
           contacts TEXT, updated_at TEXT)
stock     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
           quantity REAL NOT NULL, unit TEXT NOT NULL, per_person_day REAL, expires TEXT, notes TEXT, updated_at TEXT)
```

- `stock.category` is one of `water | food | fuel | medicine | other`. `per_person_day` is optional; when set, days left = `quantity / (per_person_day × people)` where `people` is the household count (minimum 1). Water items default to 3 litres per person per day (UK guidance covers drinking plus basic hygiene); other categories default to none.
- `expires` is an ISO date or null.
- The situation clock uses the `settings` table: `situation_slug`, `situation_started_at` (ISO UTC). One active situation per box.
- Events are `notes` rows with `kind = 'event'`; `title` holds the text, `updated_at` the time it was logged. Editing an event changes its text only; the time is kept (the router preserves `updated_at` for events on PUT).

## 4. Endpoints (all under `/api`, JSON, no PIN)

| Method and path | Body | Returns |
|---|---|---|
| `GET /household` | | `[{id, name, age, needs, medications, contacts, updated_at}]` |
| `POST /household` | `{name, age?, needs?, medications?, contacts?}` | the row |
| `PUT /household/{id}` | partial | the row |
| `DELETE /household/{id}` | | `{ok: true}` |
| `GET /stock` | | `{people, items: [{..., days_left}]}` |
| `POST /stock` | `{name, category, quantity, unit, per_person_day?, expires?, notes?}` | the item with `days_left` |
| `PUT /stock/{id}` | partial | the item |
| `DELETE /stock/{id}` | | `{ok: true}` |
| `GET /situation` | | `{slug, title, started_at, elapsed_s, phase}` or `{slug: null}` |
| `POST /situation` | `{slug}` | as GET (404 for an unknown playbook) |
| `DELETE /situation` | | `{slug: null}` |
| `GET /notes?kind=event` | existing | events, newest first |

`phase` from elapsed time: under 12 hours `right-now`, under 72 hours `first-72-hours`, under 30 days `first-month`, else `long-term`. The thresholds live in one place (`sos.situation.PHASES`) and are mirrored in the frontend for display between polls.

`days_left` is `null` when `per_person_day` is null or zero; otherwise a float rounded to one decimal. Validation: `quantity >= 0` and a non-empty name (400 otherwise); `category` outside the set is a schema error (422).

`/status` gains `situation: {slug, started_at} | null` so the status strip and Home can show it without another request.

## 5. Frontend

Pure logic modules under `web/src/tools/`, each with vitest tests:

- `sun.ts`: NOAA solar position algorithm. `sunTimes(lat, lon, date) -> {sunrise, sunset, civilDawn, civilDusk, dayLength}` in local time (the browser's zone); returns `polar: 'day' | 'night'` when no event occurs. Tested against London 21 June and 21 December 2026, Lerwick 21 June, and a southern-hemisphere check.
- `moon.ts`: phase from the synodic month (reference new moon 2000-01-06 18:14 UTC): `moonPhase(date) -> {age, illumination, name}` with the eight names. Tested against a known full moon.
- `calc.ts`: `generatorHours(tankL, litresPerHour)`, `batteryHours(wh, loadW, efficiency = 0.85)`, `solarDailyWh(panelW, month)` with the page's UK yield band (0.5 to 1 kWh per kWp per day in December rising to 4 to 5 in June, linear between, returns a low and high), `rationDays(quantity, people, perPersonDay)`.
- `dose.ts`: age-band tables copied from the two NHS pages in `nhs_medicines` (paracetamol 120mg/5ml, paracetamol 250mg/5ml, paracetamol 250mg melting tablets, ibuprofen 100mg/5ml, ibuprofen 200mg tablets for 12 to 17). `doseFor(medicine, form, ageMonths) -> {amount, mg, maxPerDay, intervalHours, notes[]} | {unavailable: reason}`. Every result carries `source: {title, url, as_at}` pointing at the library page. Ibuprofen under 3 months and paracetamol under 2 months return unavailable with the NHS wording. The 3 to 5 month ibuprofen band carries the "weighing more than 5kg" note; paracetamol 2 to 3 months carries the "over 4kg, born after 37 weeks, 2 doses a day" note.
- `situation.ts`: `phaseFor(elapsedSeconds)` mirroring the API thresholds and `describeElapsed(seconds)`.
- `timers.ts`: metronome and alarm using the Web Audio API (`OscillatorNode` clicks; falls back silently when `AudioContext` is unavailable). Tested for scheduling logic with a fake clock; audio itself is not unit tested.

Screens:

- `Tools.tsx`: tile list.
- `Timers.tsx`: presets Boil water (1 min), CPR (metronome at 110 beats per minute with a visual pulse, count of compressions), Fallout 7:10 rule (enter time of detonation; shows time to the 7 hour, 49 hour and 2 week marks and the dose-rate factor at each, with a link to the radiation module), Medication interval (4 h or 6 h), Custom. Running timers survive navigation (module-level state) and show in the app bar as a small badge while running. Alarm on completion plus an on-screen banner.
- `SunMoon.tsx`: location (last pin, else the map default; place search via `/places`; manual lat/lon), date (default today, arrows for previous/next day), results table and moon phase.
- `Calculators.tsx`: four cards, inputs with sensible defaults, results update live, each card links to the page or module the figures come from.
- `Dose.tsx`: medicine, form, age in years and months; result in large type with the maximum in 24 hours, the interval and the notes, the warning strip (999/111) and the source link. Never shows a dose outside the NHS bands.
- `Plan.tsx` is split: `plan/Household.tsx`, `plan/Stock.tsx`, `plan/EventLog.tsx`, `plan/Notes.tsx`, `plan/Pins.tsx`, with `Plan.tsx` composing them.
- `Scenario.tsx`: a `SituationClock` component in the intro: "This has started" button (confirm when another situation is active), then "Started 5 h ago, first 72 hours" with an End button (confirm). The current phase tab gets a "now" badge and `aria-current`. Home's resume card shows the same line when a situation is active.
- `Medical.tsx`: dose tile and household panel.

API client gains `household*`, `stock*`, `situation*` calls and the event helpers; `types.ts` gains the types.

## 6. Error handling

Every mutation follows the notes pattern: optimistic where cheap, `notify()` with the error message on failure, refetch on focus. Calculators validate numerically and show "Enter a number above zero" rather than NaN. The dose tool refuses ages outside its tables instead of extrapolating. Sun times report polar day or night rather than invalid times.

## 7. Testing

- Backend: `test_household.py`, `test_stock.py` (including `days_left` and the household count), `test_situation.py` (phases, unknown slug, status field), notes events (time preserved on edit) in `test_api.py`.
- Frontend: unit tests for every module in `web/src/tools/`; screen tests for Tools, Timers (fake timers), SunMoon, Calculators, Dose, Plan sections, the Scenario clock and the Medical panel; the Home test gains the sixth tile.
- The unified `make test` target stays the gate. Playwright: `ux.spec.ts` gains a pass over the Tools tile and the situation clock.

## 8. Order of work

1. Backend tables, routers, status field, tests.
2. Frontend logic modules with tests (sun, moon, calc, dose, situation, timers).
3. API client and types.
4. Plan split and new sections.
5. Tools, Timers, SunMoon, Calculators, Dose screens and routes.
6. Situation clock in Scenario and Home; Medical additions; Home tile.
7. Playwright pass, `make test`, docs.
