# Situation engine: implementation plan

Spec: `docs/superpowers/specs/2026-09-06-situation-engine-design.md`. Repository: `/home/dan/OperationSOS`. Backend FastAPI in `api/` (venv `api/.venv`, tests `cd api && .venv/bin/pytest -q`), frontend React + Vite in `web/` (`pnpm test -- --run`, `pnpm exec tsc --noEmit`, `pnpm lint`, Playwright `LD_LIBRARY_PATH=$HOME/.local/chromium-deps/usr/lib/x86_64-linux-gnu pnpm exec playwright test`). `make test` runs everything. The dev stack (Caddy 8080, API 8000, kiwix 8090, llama 8081) is running: never stop or restart it; never run `make dev`.

Already in place (do not rewrite, extend if needed): `api/sos/directives.py` (block and inline directives, branch enumeration), `api/sos/conditions.py` (ten conditions, `load`, `set_state`, `confirm`, staleness, `ConflictError`), `playbooks/rules/schema.json`, tables `conditions`, `task_state`, `sensor_readings`, `neighbours` in `api/sos/db.py`. The old `api/sos/services.py`, `api/sos/routers/services.py`, `api/tests/test_services.py`, `web/src/services.ts`, `web/src/components/ServiceToggles.tsx` and the `services` field on `/status` are superseded and must be removed by the tasks that own those paths.

Conventions: TDD (test first), British English, no new npm dependencies, PyYAML and jsonschema are available. Commit only the paths you own with explicit `git add <paths>`; if `.git/index.lock` exists, wait and retry. Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Contract: the View (`GET /api/situation/view`)

```json
{
  "meta": {"now": "2026-09-06T14:00:00+00:00", "dark": false, "sunrise": "2026-09-06T05:22:00+00:00", "sunset": "2026-09-06T18:41:00+00:00",
           "home": {"lat": 50.93, "lon": -1.43, "label": "Home", "flood_zone": "3"} , "drill": false},
  "scenario": {"slug": "grid-collapse", "title": "National grid collapse", "started_at": "...", "elapsed_s": 7200, "phase": "right-now"},
  "conditions": {"power": {"id": "power", "title": "Mains power", "state": "off", "since": "...", "for_s": 7200, "source": "manual",
                            "confidence": 1.0, "note": "", "set_by": "phone", "updated_at": "...", "confirmed_at": "...", "stale": false}, "...": {}},
  "inferred": [{"condition": "mobile", "state": "degraded", "confidence": 0.7, "due_at": "...", "why": "...", "rule": "power-off-mobile-degraded", "source": "page:what-still-works"}],
  "forecast": [{"id": "freezer", "title": "Freezer food unsafe", "due_at": "...", "severity": "warn", "why": "...", "link": "module:food", "passed": false}],
  "tasks": [{"id": "fill-bath", "title": "...", "bucket": "now", "why": "...", "link": "module:water", "person": null, "done": false, "done_at": null, "source": "rule:fill-bath"}],
  "briefing": [{"title": "Right now", "kind": "playbook-section", "ref": "grid-collapse#right-now"}, {"title": "Power", "kind": "module", "ref": "power"}, {"title": "What still works in an outage", "kind": "page", "ref": "what-still-works"}],
  "modes": {"theme": null, "dim": false, "calls": "shown", "map_first": false, "board": false},
  "readiness": {"score": 62, "gaps": [{"title": "Water: 1.5 days for 3 people", "link": "/plan#stock", "points": 12}]},
  "bulletins": {"next": {"station": "BBC Radio 4", "frequency": "198 kHz LW", "at": "2026-09-06T18:00:00+00:00"}}
}
```

- `scenario` is `null` when none is active. `conditions` always has all ten ids. `tasks` are ordered now, hour, today, week, then by title; done tasks stay in the list with `done: true` until retired. `briefing` refs: `playbook-section` is `<slug>#<section-id>`, `module` and `page` are slugs, `card` a card slug, `doc` a document id.
- Links in rules use the content link scheme (`playbook:`, `module:`, `page:`, `card:`, `doc:`, `map:`); the frontend resolves them with the existing `resolveLink` rules (`/s/`, `/m/`, `/p/`, `/medical/card/`, `/doc/`, `/map`).

Other endpoints:

| Method and path | Body | Returns |
|---|---|---|
| `GET /api/conditions` | | `{id: condition}` for all ten, with `stale` |
| `PUT /api/conditions/{id}` | `{state, since?, note?, expected_updated_at?}` | the condition; 409 with the current row on a conflict; 404 unknown id; 422 bad state |
| `POST /api/conditions/{id}/confirm` | | the condition |
| `POST /api/conditions/{id}/accept` | `{rule}` | takes the inferred state for that rule as source `inferred` |
| `GET /api/tasks` | | the View's tasks |
| `PUT /api/tasks/{id}` | `{done?, person?}` | the task |
| `GET /api/home` and `PUT /api/home` | `{lat, lon, label?, flood_zone?}` | the home |
| `POST /api/drill` | `{scenario, conditions: {power: "off", ...}, hours_ago?}` | the View; `DELETE /api/drill` ends it and restores the saved conditions |
| `GET /api/situation/report` | | `text/markdown` |
| `GET /api/status` | | gains `conditions` (id to state), `modes`, `drill`, `readiness_score` |

Events: every change writes a `notes` row with `kind = 'event'` and a title such as "Mains power off since 14:20 (phone)"; the actor is `kiosk` for 127.0.0.1, `phone` otherwise, `box` for detection, `drill` during a drill.

## Rules files (`playbooks/rules/*.yaml`)

`implications.yaml`, `consequences.yaml`, `tasks.yaml`, `modes.yaml`, `reading.yaml`, `bulletins.yaml`; each a YAML document `{rules: [...]}` (bulletins: `{rules: [], bulletins: [...]}`) validated against `schema.json`. Every rule needs `source` (a content link) and `why`. Duration strings `30m`, `4h`, `2d`. `when` keys and semantics per the schema. `needs` matches household `needs` or `medications` text (case-insensitive substring) and yields one item per person with `{name}` substituted; `stock` predicates read `days_left` (`days_lt`) or absence (`missing: true`) by category.

Minimum content, with UK timings and citations from the playbooks and pages: power off implies mobile degraded 4h and off 8h, shops off 0h, internet off 0h (home), heating off 0h (gas boilers need power), water degraded 24h (pumped supplies), sewage degraded 24h; gas off implies heating off; consequences: fridge 4h warn, freezer 48h danger, phone batteries 12h warn, hot water 24h info, cold-chain medicines 24h danger (`needs: insulin` or `fridge`), oxygen concentrator 6h danger (`needs: oxygen`), CPAP 8h warn (`needs: cpap`), stairlift and hoist 0h warn (`needs: hoist|stairlift`), tank water 3d warn, cash 0h info when shops off; tasks: fill bath while water works, fridge and freezer doors shut, cooker off at the knobs, CO alarm check when gas or generators, charge everything while power lasts (power degraded), medicines cold box (needs insulin, after 2h), check on anyone medically dependent (needs any, at 0h), fill containers when water degraded, boil water when water degraded or off after restoration, bucket flush when sewage degraded, meeting point and runner plan when phones off, cash out when shops degraded, one warm room when heating off, plus the active scenario's checklist items as `checklist:<slug>/<item>` tasks (done state shared with `checklist_state`); modes: blackout and dim when power off and dark, calls hidden when mobile and landline off, map first for storms-flooding, board when a scenario is active; reading: per condition and per scenario phase.

## Wave 1 (parallel; disjoint paths)

### Task A: backend engine and API (owns `api/**`, `playbooks/rules/**`)

1. `api/sos/rules.py`: load all YAML files in the rules directory (`settings.playbooks / "rules"`), validate against the schema, cache by mtimes, expose `Rules` with lists by kind and `bulletins`; `parse_duration`. Tests: schema violations raise with the file and rule id; a parametrised test asserts every rule's `source` link resolves to an existing playbook, module, page, card or manifest document (use `ContentCache`).
2. `api/sos/sun.py`: `sun_times(lat, lon, date) -> (sunrise, sunset)` UTC (NOAA equations; port of `web/src/tools/sun.ts`), `is_dark(lat, lon, now)`. Tests against London 21 June and 21 December 2026.
3. `api/sos/engine.py`: `Model` dataclass (conditions, scenario, household, stock items with `days_left`, home, now, drill, checklist items for the active scenario, `checklist_state`, `task_state`), `compute(model, rules) -> dict` exactly the View contract, pure and deterministic. Effective state: manual beats detected beats inferred, but a detected reading newer than the manual `updated_at` proposes, never overrides. Inferred proposals come from implications whose `after` has elapsed and whose target condition is still `working` (or `degraded` when the implication says `off`). Forecast from consequences with `due_at = since + after`, `passed` when due_at <= now. Tasks from task rules whose `when` matches and whose `until` does not, plus checklist items; `done` from `task_state` (or `checklist_state` for checklist tasks). Modes merged in file order. Readiness per spec section 7. Bulletins: next time today or tomorrow in the box's local zone. Golden tests: a fixed model at a fixed clock for (a) nothing off, (b) power off 5 hours with a household member on insulin and oxygen, (c) storms-flooding scenario with mobile and landline off at night, asserting forecast order, task buckets, inferred proposals, modes and readiness.
4. `api/sos/routers/situation.py`: extend with the endpoints in the contract (keep the existing `/situation` start and end). Build the Model from the database and the content cache (`request.app.state.content`) and the settings; write events; conflicts return 409 with the current row. `/status` (`api/sos/routers/status.py`) gains `conditions`, `modes`, `drill`, `readiness_score`; remove `services`. Register nothing new in `main.py` beyond what exists (`situation_router` is already registered); delete `services.py`, `routers/services.py`, `tests/test_services.py`.
5. Content: `api/sos/content.py` applies `directives.resolve(md_text, flags)` before Markdown rendering in `render_document` and `render_module` (`rendered(kind, slug, flags=None)`; cache key includes `directives.signature`). The playbooks, modules, cards and pages routers pass the current flags (`engine.flags(view)`: conditions `working` or `degraded` count as true, `phones` = mobile or landline true, `dark`, `scenario:<slug>` true for the active scenario). `validate_tree` renders every document for every `branch_flag_sets` combination and checks links in each; a `DirectiveError` is a validation error. Tests for both.
6. `api/sos/situation.py` keeps the clock; add `drill` handling (`settings` keys `drill` JSON with the saved conditions) used by the router.
7. `api/tests/simulate.py`: a random walk of 400 steps over conditions, scenarios and clock advances with a seeded RNG; assert no exception, determinism (compute twice), every forecast has `due_at`, no task present whose `until` matches, `modes.calls == "hidden"` whenever mobile and landline are both off. Run as a normal test.

Report the final View for the three golden models and the test counts.

### Task B: frontend phase 1 (owns `web/**`)

Work against the contract above; the backend may land later, so mock the API in tests and add fixture routes in `web/e2e/fixtures/routes.ts` and state in `state.ts` for every endpoint in the contract (a small in-memory engine is fine: conditions, tasks done state, a fixed forecast when power is off).

1. Types and client: `Condition`, `SituationView`, `Task`, `Forecast`, `Inferred`, `Modes`, `Home`; `api.situationView()`, `api.conditions()`, `api.setCondition(id, body)`, `api.confirmCondition(id)`, `api.acceptInferred(id, rule)`, `api.tasks()`, `api.setTask(id, body)`, `api.home()`, `api.setHome(body)`, `api.startDrill(body)`, `api.endDrill()`. `Status` gains `conditions`, `modes`, `drill`, `readiness_score`; remove `services`.
2. A `SituationProvider` (`web/src/situation/SituationProvider.tsx`) that polls `/situation/view` every 30 s and on focus, exposes the View and an `apply(view)` for optimistic updates, and is mounted in `App.tsx` inside the status provider.
3. Home: replace `ServiceToggles` and `OutagePanel` with a **situation strip** (scenario and clock if active, the five home conditions as chips: green working, amber degraded, red off, each showing "for 5 h" when not working; tapping a chip opens the sheet at that condition; DRILL badge) and a **briefing** section: inferred proposals with Accept and Not now, forecast items due in the next 24 h with countdowns, the now and hour tasks with tick boxes and names, then the reading links. Peacetime (nothing off, no scenario): the strip shows the readiness score and top gap. The existing Home layout below stays.
4. `/situation` sheet: all ten conditions with state buttons (working, degraded, off), a since picker (now, 1 h ago, this morning, yesterday, custom), a note, who set it and when, stale prompts ("still off?") with Confirm, the clock controls, the drill controls (choose scenario and conditions, hours ago, start; DRILL banner and End drill), and a Print report button that opens `/api/situation/report` in a new tab.
5. `/tasks`: buckets with tick boxes, why and link on each, assign to a household member (from `api.household()`), a "done" filter, and the count in the app bar.
6. Chrome: a compact chip strip in the `AppBar` (or under it) on every screen when anything is off or a scenario is active: red and amber chips plus the clock, tapping opens `/situation`. Remove `OutageNotice`, `services.ts`, number tagging in `Html.tsx` and their tests; instead, when `modes.calls === 'hidden'` render a one-line notice on content screens saying phone numbers on this page will not connect with a link to `/p/no-phones` (the content itself now carries the alternatives through directives).
7. Modes (phase 1 part): `ThemeProvider` honours `modes.theme` and `modes.dim` from the View while set (a `data-dim` attribute halves brightness via CSS); the Home tile order puts Maps first when `map_first`.
8. Tests: unit tests for chip colours and countdown text, screen tests for the strip, briefing, sheet, tasks and chrome chip, Playwright: from Home set power off since 1 h ago, see the freezer forecast and the fill-the-bath task, tick it, open the sheet, end with everything working.

Report screenshots at 853x480 of Home with power off and of the sheet, and the test counts.

### Task C: content pass (owns `playbooks/scenarios/**`, `playbooks/modules/**`, `playbooks/cards/**`, `playbooks/pages/**`)

Rewrite every instruction that depends on a service so it renders correctly in every situation, using the directives (see `api/sos/directives.py` docstring):

- Every "call 999/112/111/105/101" and the numbers in every quick card's Stop or escalate section become `[[call 999]]` (renders "call 999" normally, and "999 will not connect while the phones are down: get help without phones" otherwise). Read `playbooks/pages/no-phones.md` first so the alternatives match.
- Advice that assumes water, power, gas or internet gains a branch: `{{#if water}}Fill the bath now{{else}}Water is off: draw from the tank and the [water module](module:water){{/if}}`; "check the website", "charge your phone", "boil the kettle", "turn the heating up" and similar each get their branch. Keep prose natural inside each branch and never leave a branch empty.
- Only these flags exist: `power water mobile landline internet gas heating roads shops sewage phones dark scenario:<slug>`.
- Run `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios` after each file; it must stay at OK (directives pass through as text until Task A lands, links inside both branches are still checked). Do not edit anything under `api/` or `web/`.
- Keep the content tests green: `cd api && .venv/bin/pytest -q tests/test_playbooks_content.py tests/test_content.py`.

Report a table of files changed with the number of directives added, and any instruction you could not express.

## Wave 2 (after wave 1 is merged and `make test` is green)

### Task D: backend phase 2 and 3 (owns `api/**`, `manifest/**`, `install/**`, `playbooks/rules/**`)
Home and nearest facilities (`GET /api/nearby?lat&lon` from the GeoJSON overlays and the places index: emergency department, pharmacy, GP, fuel, water works, fire station, rest centre; distance and Naismith time), readiness recomputed on stock and household changes, `sos.sensors` with the drivers and a background task in `main.py` (60 s), inferred prompts from readings, bulletins recording with `rtl_fm` when present, `POST /api/speak` with Piper (manifest items `piper` and `piper-voice-en_GB`, install notes), tests with fake subprocesses and fixture `rtl_power` output.

### Task E: frontend phase 2 and 3 (owns `web/**`)
Board (`/board`) and kiosk idle switch to it when a scenario is active or anything is off; modes for calls and map-first; map "Set as home" capturing the flood zone, nearest facilities panel, bearing and time to a facility; readiness on Home with gaps; drill flow polish; read aloud button; sensors on the sheet with detected badges; forecast reminders (kiosk toast when an item falls due).

### Task F: phase 4 (backend then frontend)
Neighbours API and screen, who-to-check-on tasks and reading rules, printable street list, report export and import (JSON and QR sequence), hardware notes in `docs/hardware-checklist.md`, the simulator wired into `make test`.

## Integration (Fable)
After each wave: `make test`, Playwright fixture suite, rebuild `web/dist`, restart the dev stack through `dev/run-dev.sh` (never kill uvicorn alone), re-enable the AI, screenshot, update `docs/app-completion.md`, commit.
