# No setup: removal map (research record, 2026-09-07, line numbers as of commit 44efcfb)

Source of intent: `docs/superpowers/specs/2026-09-07-no-setup-design.md`. DB tables stay
(unread); kits content stays; the map stays.

## 1. API

**`api/sos/routers/household.py`** (224 lines) — delete whole file: household CRUD (`GET/POST
/household` 141-154, `PUT/DELETE /household/{id}` 157-178), Stock CRUD (`GET/POST /stock`
181-198, `PUT/DELETE /stock/{id}` 201-224), `PersonIn/PersonPatch` (21-34), `StockIn/StockPatch`
(37-54), `CATEGORIES`/`Category`/`DEFAULT_PER_PERSON_DAY`/`COUNTED` (14-18). `_item`,
`people_count` (69-70, 98-114) are imported by `routers/situation.py:75` (used in `_stock()`
68-78) and `routers/kits.py:10` (used in `_stock_rows` 41-46, `list_kits` 120) — both call sites
are themselves deleted below, so nothing orphaned, but `people_count` (register size) must be
replaced everywhere by `settings.people`. `is_expired`, `stock_days_by_category`, `_kit_title`,
`days_raw` are only used by the deleted Stock code; delete with it.

**`api/sos/routers/neighbours.py`** (78 lines) — delete whole file: `GET/POST /neighbours`
(41-52), `PUT/DELETE /neighbours/{id}` (55-71), `GET /street-list` (74-78, `StreetListLink`'s
target), `NeighbourIn/NeighbourPatch` (16-31).

**`api/sos/neighbours.py`** (84 lines) — delete whole file: `row`, `listing`, `get`, `add`,
`update`, `remove`, `label`, `street_list`. Called from `routers/neighbours.py:8` and
`routers/situation.py:13,150` (`neighbours=tuple(nb.listing(conn))` in `build_model_for`).
`transfer.py:20` imports `neighbours as nb` but never calls it — dead import either way.

**`api/sos/readiness.py`** (78 lines) — delete whole file: `store`, `stored`, `refresh`, `_due`,
`nightly`; `settings` keys `readiness_score`/`readiness_at`. Callers to strip: `main.py:13`
(import), `:68` (`readiness.nightly` task); `routers/status.py:3,19-23` (`/status`'s
`readiness_score`); `routers/household.py:8,153,168,177,197,214,223` (dies with the file);
`routers/kits.py:7,154,163` (after a tick / stock hand-off); `routers/situation.py:13,289,398,446`
(after import-merge, setting home, ending a drill).

**`api/sos/routers/system.py`** — `SettingsBody` (27-34) and `POST /system/settings` (75-78) are
the existing pattern a `people` setting should join (section 7); no removal here.

**`api/sos/routers/situation.py`**, `build_model_for` (106-157): `_stock()` (68-78) delete;
`household = tuple(...)` (133-135) delete (`Model.household` goes with it); `neighbours=
tuple(nb.listing(conn))` (150) delete; `stock=_stock(conn)` (151) delete; the meeting-point probe
(136-137, `SELECT 1 FROM notes WHERE ... 'meeting point' ...`) and `meeting_point=meeting is not
None` (153) delete — the meeting-point idea becomes prose only (spec section 3). `kit_rows` loop
(140-148): `kits_mod.relevant(kit, household)` (147) becomes `kits_mod.relevant(kit)` — spec:
"every kit is relevant" with no register; `basic_progress`/ticks are unaffected. Everything else
in `build_model_for` (scenario, conditions, checklist, task_state, home, drill, titles,
last_drill_at, tz, detected) stays.

**`api/sos/routers/kits.py`** (164 lines) — the hand-off into Stock is removed, not the kit lists:
`StockAdd`, `ItemBody.stock` (16-24) delete (`ItemBody` keeps only `checked`); `_stock_rows`
(41-46) and its use in `kit_view` (83, 94, 102-104, the `stock_item` field) delete; `set_item`'s
`if body.stock is not None:` branch (128, 134-149) delete, ticking (149-155) stays; `_household`
(31-33) and its uses in `kit_view` (80-81, 109) and `list_kits` (115, 119) — replace with
`settings.people` (an int, not rows); `people_count(conn)` import (10) and use (120) — replace
likewise; `readiness.refresh` (7, 154, 163) delete.

**`api/sos/kits.py`** — `matching_people(kit, household)` (166-175) and `relevant(kit, household)`
(178-185) read `age`/`needs` off register rows for `relevant_when` (`age_under`, `needs_any`).
With no register: `relevant` returns `True` unconditionally; `matching_people` returns
`max(1, people)` from the setting, so a gated kit (baby/child) scales to the whole household
count, not "how many babies". `_matches`, `_need_words`, `_term_matches` (139-163) become dead
code once those two change — kit YAML's own `relevant_when` field stays as content (out of scope).

**`api/sos/engine.py`** — section 2. **`api/sos/rules.py`** — section 3 (`who`/`needs`/`skills`/
`stock` drop from `_FIELDS` 20-21, `Rule` 57-60, `WHO` 22, the schema-driven checks at 64-65).

**`api/sos/transfer.py`** (309 lines): `PARTS` (29) drops `"household"`, `"stock"`,
`"neighbours"` — spec section 3 wants `conditions, scenario, tasks, checklist, notes, home,
events, settings (people)`, which adds `notes` and `settings` not currently in `PARTS` at all;
reconcile when implementing. `_PERSON_FIELDS`/`_STOCK_FIELDS`/`_NEIGHBOUR_FIELDS` (30-32) delete.
`data_for()` (54-74): drop the three rows (68-70). `merge()` (267-280): drop the three
`_merge_people(...)` calls (274-276); `_merge_people` (185-210) becomes dead. `summary_line()`
(302-309): drop the count lines (306-307). `decode()`'s `set(PARTS) <= set(data)` check (141-142)
already tolerates *extra* keys in an old export, so an old export with household/stock/neighbours
still decodes — only the "note in the summary" behaviour (spec) is new.

**`api/sos/db.py`** — tables stay (`household` 22, `stock` 24, `neighbours` 32, `settings` 34).
`get_setting`/`set_setting` (74-89) are the mechanism (section 7).

**`api/sos/main.py`** — drop `household` import (17) and `household.router` (84); drop
`neighbours_router` import (18) and its registration (85); drop `readiness` import (13) and the
`readiness.nightly` task (68). `kits.router` (17, 85) stays.

**`api/sos/cli.py`** — no household/neighbours/stock/readiness registrations; only a kits YAML
glob count (103), unaffected.

## 2. Engine (`api/sos/engine.py`, 637 lines)

- `Model.household` (47), `.neighbours` (48), `.stock` (49), `.meeting_point` (58),
  `.last_drill_at` (59, only fed the practice-points gap — dies with `readiness`), `.people`
  property (68-70, `max(1, len(self.household))`) — all delete.
- `need_words` (138-140), `matches_needs` (143-151), `register` (154-155), `people_for`
  (158-160), `fill`/`_Fields` (163-174, `{name}`/`{address}`/`{at_address}` filling) — delete;
  nothing produces person/neighbour rows to fill them with.
- `stock_matches` (177-188), `_row_days`/`_days`/`stock_days` (191-207) — delete.
- `check_on` (316-334, who to knock on) and `neighbour_skills` (337-357, "Mrs Khan is a nurse")
  — delete.
- `readiness()` (442-508, whole scoring function) and its call in `compute()` (558) — delete;
  `STOCK_TARGETS` (28), `KIT_POINTS` (29), `DRILL_FRESH` (30) go with it.
- `compute()` (536-560): drop the `"neighbours": {...}` key (554-555) and `"readiness": ...`
  (558); `tasks`, `forecast`, `inferred`, `briefing`, `modes`, `bulletins`, `conditions`,
  `scenario`, `meta` stay.
- `tasks()` (360-389): the `who == "neighbours"` guard (370) and `people_for`/`need_terms` branch
  (372-375) delete, leaving only the plain `_task(...)` path (376-377); the `check_on` merge
  (378-380) goes with `check_on`.
- `forecast()` (281-297): same `need_terms`/`people_for` branch (290-293) deletes, leaving only
  the plain-title branch (294-295) — so a `needs:` consequence rule (section 3) has nothing left
  to expand it and must itself be deleted, not just the code path.
- `report()` (585-636): the `## Neighbours` block (618-629) and `Readiness {score} of 100.`
  (632) — delete.
- Untouched: `matches`, `trigger_since`, `effective_states`, `condition_view`, `inferred`,
  `_strongest_per_condition`, `briefing`, `modes`, `next_bulletin`, `flags*`, `summary_line`,
  `phones_state`, `_season`.

## 3. Rules content

`playbooks/rules/schema.json`: drop `needs` (46), `skills` (47), `who` (48), `stock` (49-50) from
`properties` (30-67), and the two `allOf` clauses referencing them (57-65 — reading rules needing
`open` or `skills`, and `skills` implying `who: neighbours`).

Every rule with `needs:`, `who:`, `skills:` or `stock:` (17 total):

| id | file:line | kind | field(s) | what it does |
|---|---|---|---|---|
| `cold-medicines-insulin` | consequences.yaml:44 | consequence | needs | insulin out of the fridge too long |
| `cold-medicines-fridge` | consequences.yaml:55 | consequence | needs | cold-chain medicine out of the fridge too long |
| `oxygen-concentrator` | consequences.yaml:66 | consequence | needs | back-up oxygen cylinders low |
| `cpap` | consequences.yaml:77 | consequence | needs | a night without CPAP coming |
| `hoist` | consequences.yaml:88 | consequence | needs | hoist out of action |
| `stairlift` | consequences.yaml:99 | consequence | needs | stairlift out of action |
| `neighbour-skills-medical` | reading.yaml:103 | reading | who, skills | nurse/doctor/paramedic/midwife/first aider/dentist/vet/pharmacist |
| `neighbour-skills-trades` | reading.yaml:112 | reading | who, skills | electrician/plumber/engineer/mechanic/builder/farmer/gas fitter |
| `neighbour-skills-kit` | reading.yaml:121 | reading | who, skills | generator/chainsaw/4x4/tractor/log burner/well/radio/boat |
| `medicines-cold-box` | tasks.yaml:60 | task | needs | move insulin into a cold box with ice packs |
| `check-dependent` | tasks.yaml:71 | task | needs (`*`) | check on anyone with a recorded need after power/mobile/landline loss |
| `water-stock-low` | tasks.yaml:136 | task | stock | top up water under 3 days |
| `medicine-stock-missing` | tasks.yaml:146 | task | stock | prompt to add the medicine box to Stock |
| `neighbours-power-off` | tasks.yaml:159 | task | needs, who | check on vulnerable neighbours, power off |
| `neighbours-water-off` | tasks.yaml:170 | task | needs, who | take water to vulnerable neighbours |
| `neighbours-heating-off-winter` | tasks.yaml:181 | task | needs, who | check vulnerable neighbours are warm |
| `neighbours-scenario` | tasks.yaml:192 | task | needs (`any`), who | knock on every neighbour when a scenario starts |

`bulletins.yaml`, `implications.yaml`, `modes.yaml` — no rules use these fields, unaffected.

## 4. Frontend

**Deleted screens**: `web/src/screens/Plan.tsx` (133, the Household hub — rows, `stateLines`,
`hasMeetingPoint`, `ANCHORS`), `web/src/screens/plan/Household.tsx` (120),
`web/src/screens/plan/Neighbours.tsx` (180, incl. `StreetListLink` at 105 → `/api/street-list`),
`web/src/screens/plan/Stock.tsx` (342, incl. exported `daysBadge`/`meter`/`sortStock`/
`RATE_BY_CATEGORY`/`CATEGORIES`/`METERED`), `web/src/screens/plan/NeighboursScreen.tsx` (17),
`web/src/screens/plan/StockScreen.tsx` (20), `web/src/screens/plan/People.tsx` (20),
`web/src/situation/Readiness.tsx` (71, whole file).

**Kept but relocated**: `web/src/screens/plan/Notes.tsx` (131), `plan/Pins.tsx` (37, `PinRow`),
`plan/NotesScreen.tsx` (18) — becomes the top-level `/notes` screen (spec section 3); its
`backTo="/plan"` (10) must change. `plan/PlanPage.tsx` (22) — the household-plan content page
moves under `/p/household-plan` into Guides' "Reference" group (already matched there:
`playbooks/pages/household-plan.md`'s `category: plan` front matter, grouped by
`web/src/screens/Guides.tsx:19`'s `categories: ['reference', 'plan', 'about']`); its prose
("your own filled-in notes... live on the `/plan` screen", household-plan.md line 11) needs a
content edit. `plan/EventLog.tsx` (110, `formatStamp`, used by `/situation#log`) stays as is.

`daysBadge` (Stock.tsx:59) is imported by `web/src/screens/Kit.tsx:12`, used at 74-76, 101 for the
"in Stock" badge — dies with that feature, not moved.

**`web/src/screens/Kit.tsx`** (180 lines): `AddToStock` (23-56, the quantity/use-by form,
`api.setKitItem(..., { stock: {...} })`), the `daysBadge` import/use (12, 74-76), the "in Stock"
line (98-104, incl. `<Link to="/plan#stock">`) and its `<AddToStock>` fallback (105) — all delete.
Tick UI (58-97) stays. Line 149's "for {kit.people} people on the register" drops "on the
register" (spec: "For N people").

**`web/src/screens/Kits.tsx`** (110 lines): line 78 `people = q.data?.people ?? 1` and line 90's
"household register" wording become the settings-backed stepper (spec section 3); the "Not needed
for this household" split (`relevant`/`rest`, 76-77, 96-99) collapses to one list once `relevant`
is always true.

**`web/src/screens/Now.tsx`** (193 lines): `HouseholdSummary` (25-71, "Household and stock" panel:
`api.household()` 26, `api.neighbours()` 27, days-left badges 54-66) — delete, and its render at
187. `<Readiness />` import (13) and render (186) — delete, replace with the spec's "Start here"
block (kits progress line, drill button, guide tiles). `stock` query (156) and `stockEmpty` (157)
— delete once `nowTitle` drops that param. `BoxPanel` (78-113), `CarryOn` (117-149) unaffected.

**`web/src/situation/nowTitle.ts`**: `peacetimeTitle` (24-29) reads `view.readiness?.gaps` (25)
and branches on `stockEmpty` (27-28) — collapses to always `'Everything is working'`; `nowTitle`'s
`stockEmpty` param (34, from `Now.tsx:166`) becomes dead.

**`web/src/screens/Medical.tsx`**: `householdQ` (68), the needs/medications filter (69), and the
"In this household" panel (111-112, `<Link to="/plan#household">`) — delete the whole block.

**`web/src/screens/Tasks.tsx`** + **`web/src/situation/TaskRow.tsx`**: `Tasks.tsx:13`
(`api.household()`) feeds `people={household.data ?? []}` (48) into `TaskRow`, which — when given
`people` (17) — renders a "Who is doing this" `<select>` from the register (45-53) instead of
plain `{task.person}` text (54). **Not named in the design spec**, but breaks the moment
`/household` 404s; needs an explicit decision (drop assignment, or a free-text name field).

**`web/src/situation/board.ts`** — no stock/household code (`wantsBoard`, `nextTasks`,
`boardSunset` are condition/task/sun based); no change needed despite being named in the brief.

**`web/src/situation/BoardView.tsx`** (116 lines): `stock` query (26), `STOCK_DAYS` (16), the
`days` calc (43) and `board-stock` list (94-101) — delete; conditions/jobs/sunset/bulletin/log
stay.

**`web/src/screens/tools/Calculators.tsx`**: line 74, `<Link to="/plan#stock">Stock</Link>` in
the water-calculator note — rewrite (target gone).

**`web/src/screens/Tools.tsx`**: `TOOL_TILES` line 11 (`/plan/stock` Stock tile) — delete. No
separate "household plan" tile exists here — the household plan is reached via Guides (see
PlanPage note); check that assumption before the plan is written.

**`web/src/shell/destinations.ts`**: line 11, Now's `match` includes `starts('/situation',
'/tasks', '/board', '/plan')` — drop `'/plan'`, add `'/notes'`.

**`web/src/router.tsx`**: delete lazy imports/routes for `Plan` (39, route 103), `People` (40,
104), `NeighboursScreen` (41, 105), `StockScreen` (44, 106); `plan/plan` (108, `PlanPage`) — path
changes, component stays; `plan/notes` (107, `NotesScreen`) — path becomes top-level `/notes`.

**`api/types.ts`**: `Person` (60), `Neighbour` (62), `StockCategory` (63), `StockItem` (64-73),
`StockResponse` (74) — delete. `Status.readiness_score?` (16) — delete. `ReadinessGap` (138),
`Readiness` (139), `SituationView.readiness` (151), `SituationView.neighbours?` (152-153),
`NeighbourCheck` (158-161), `NeighbourSkill` (163) — delete. `KitItem.stock`/`stock_item`
(185, 188) — delete (`qty`/`checked` stay). `KitsResponse.people` (178), `Kit.people` (189) keep
their shape but now come from `settings.people`, not the register.

**`api/client.ts`**: delete `household` (135), `addPerson` (136), `updatePerson` (137),
`deletePerson` (138), `neighbours` (139), `addNeighbour` (140), `updateNeighbour` (141),
`deleteNeighbour` (142), `stock` (143), `addStock` (144), `updateStock` (145), `deleteStock`
(146). `setKitItem`'s `body.stock` option (149) narrows to `{ checked: boolean }`. No
`streetList` client method exists — `Neighbours.tsx:105`'s print link goes straight to
`/api/street-list` by href; dies with that component.

## 5. Tests and e2e

**API — delete whole files**: `test_household.py` (82: register CRUD, Stock CRUD/days
arithmetic, `test_readiness_ignores_expired_stock`), `test_neighbours.py` (142: CRUD, ordering,
validation, event logging, street list markdown/escaping, check-on task, skills reading, report
section), `test_stock.py` (27: days-left sizing, validation), `test_readiness.py` (94: store on
first read, stock/household/home/drill recompute, nightly timing, never-fail-the-write, timestamp).

**API — rewrite**: `test_transfer.py` — delete `test_a_transferred_stock_row_keeps_its_kit_link`
(128), `test_import_matches_people_and_stock_by_name` (145); trim household/stock/neighbours from
every other `data_for`/`merge`/`PARTS`/summary-line expectation. `test_kits.py` — rewrite
`test_matching_people_counts_only_the_people_a_kit_is_for` (86), `test_kit_detail_scales_to_the_
household` (213), `test_gated_kit_scales_by_its_own_people_not_the_register` (231) for the
settings-count signature; delete `test_tick_and_add_to_stock` (244), `test_adding_to_stock_ticks_
the_item_whatever_the_body_said` (319), `test_a_stock_hand_off_of_nothing_is_refused` (325),
`test_stock_rows_carry_the_kit_title` (334). `test_engine.py` — delete `test_peacetime_gaps_name_
what_is_missing` (65), `test_readiness_counts_the_basic_tier_of_relevant_kits` (76), `test_equal_
kit_gaps_put_the_emptiest_kit_first` (88), `test_readiness_without_kit_content_keeps_the_full_kit_
points` (101), `test_stock_predicates` (338), and the five neighbour tests (390, 401, 414, 421,
437); rewrite `test_golden_peacetime` (50), `test_report_of_a_blackout_lists_the_forecast` (304),
`test_the_report_carries_the_street` (430). `test_rules.py` — delete the six `who`/`needs`/
`skills` schema tests (182, 192, 202, 210, 218, 224). `test_situation_api.py` — delete
`test_the_model_reads_the_stock_without_opening_a_kit_file` (62); rewrite `test_the_report_is_
markdown` (245, asserts `"Readiness" in text`) and `test_status_carries_the_situation_and_no_
services` (255, asserts `readiness_score` is an int).

**Web — delete whole files**: `screens/neighbours.test.tsx`, `screens/people.test.tsx`,
`screens/plan.test.tsx`, `screens/stock.test.tsx`, `screens/medical-needs.test.tsx` (the "In this
household" panel).

**Web — rewrite**: `screens/kit.test.tsx` (8, 39, 71 — stock line, Add to Stock, zero-hand-off
refusal; keep tiers/citation/reset/error tests); `screens/kits.test.tsx` (15, the "Not needed"
split); `screens/now.test.tsx` (8, 47, 57 — household summary / cupboard wording / gaps, rewrite
for "Start here"); `screens/board.test.tsx` (20, drop "the stock" from the assertion list);
`screens/tasks.test.tsx` (38, "assigns a task to somebody in the household" — depends on the
Tasks/TaskRow gap above); `screens/carry.test.tsx` (101-107, `countLines` naming household/
neighbours/stock — rewrite to the new `PARTS`); `situation/nowTitle.test.ts` (8, 14, 20, 25, 35,
all peacetime-title cases); `situation/conditions.test.ts` (59, `contentHref('/plan#stock')`
round-trip — low value, update the example path).

**Web fixtures**: `web/e2e/fixtures/state.ts` (household/stock/neighbours arrays, 13-14, 29,
59-60, 72); `web/e2e/fixtures/engine.ts` (`readinessGaps` 37-46, neighbour check-on/skills
106-118, `readiness`/`neighbours` keys 156, 158); `web/e2e/fixtures/routes.ts` (the `/household`,
`/stock`, `/neighbours`, `/street-list` fake routes ~247-340, export/import counts 314-315, 320,
`readiness_score` passthrough 181); `web/tests/fixtures/api.ts` (`stockResponse` 383,
`neighbours` 420 — `householdPlan` 269 stays, it's content).

**Web e2e**: `situation.spec.ts` (whole file, the "How ready you are" panel — delete);
`screenshots.spec.ts` scenarios `now-peacetime` (38), `now-empty-household` (44), `household`
(75), `neighbours` (76), `stock` (77) — delete or repoint; `board.spec.ts` (39-56, "Home in
peacetime says how long the household would last" + a `/plan#stock` assertion at 56) — rewrite;
`ux.spec.ts` (82, path list includes `/plan`) — swap for `/notes`.

## 6. Docs

`docs/superpowers/specs/2026-09-06-household-simplification-design.md` — whole document
superseded (household hub, Stock meter screen); keep as history, don't delete. Sections:
`## 2. Household hub: /plan` (16), `## 4. Stock: /plan/stock` (43).

`docs/superpowers/specs/2026-09-06-kits-design.md` — `## 4. Readiness` (76-90): the scoring table
and `Model.kits` description need rewrite once readiness is gone and kits scale by
`settings.people`.

`docs/superpowers/specs/2026-09-06-situation-engine-design.md` — `### Household, stock, home`
(36-38), `## 7. Readiness and drills` (94-96, keep drills, drop readiness), `## 8. Community`
(final section — neighbours table, street list, export/import) — all need rewrite.

`docs/superpowers/specs/2026-09-06-interface-redesign.md` — `## 2. Design plan` line 37,
`## 3. Screens` lines 47-51 (Now's readiness/household-and-stock, Medical's household needs),
`## 6. Coverage inventory` lines 73-93 (the `/plan` routes-table entry and sub-screens, `/tasks`
row's "assignment ... with and without a household", `/board` row's "no stock") — all rewrite.

`docs/superpowers/specs/2026-09-03-operation-sos-design.md` — line 420, routes table row
`| /plan | Household plan template, shared notes, pins list |` — update for the split
(`/p/household-plan`, `/notes`).

`docs/superpowers/specs/2026-09-05-tools-design.md` — title itself names "stock, household"
(line 1); whole doc covers the Tools screen losing its Stock tile — rewrite.

`README.md` — line 12 (household-plan reference pages, still true) unchanged; line 13
("quantities scaled to the household and a one-tap hand-off into Stock") — rewrite: scaled to the
people count, no hand-off.

`docs/app-completion.md` — lines 53, 58-59, 79-80 are changelog entries describing when these
features were *added*; leave as history, add a new entry for the cut rather than editing old ones.

`docs/superpowers/plans/2026-09-06-household-simplification.md`,
`docs/superpowers/plans/2026-09-06-kits.md` — executed implementation plans, historical; no action.

## 7. Settings (mechanism for the new `people` count)

`api/sos/db.py`: `settings` is `(key TEXT PRIMARY KEY, value TEXT)` (line 34, already generic);
`get_setting(conn, key, default=None)` (74-79) / `set_setting(conn, key, value)` (81-89) are the
only primitives, both string-typed — `people` round-trips as `str(int)` like every other numeric
setting (`thermal_ai_off_c`, `idle_minutes`).

`api/sos/system.py`: `DEFAULTS` dict (36-39) holds every default string — add `"people": "2"`.
`status()` (429-452) reads each through `get_setting(conn, key, DEFAULTS[key])` and casts
(`int(...)`, e.g. line 444) — add a `people` line so `/status` carries the count for every screen.

`api/sos/routers/system.py`: `SettingsBody` (27-34) / `POST /system/settings` (75-78,
`system.apply_settings(conn, body.model_dump(exclude_none=True))`) is today's one generic
settings-write endpoint. The design spec instead wants a dedicated pair, `GET /api/settings/
people` and `PUT /api/settings/people {people}`, with its own 1-20 range validation (spec section
3) rather than folding into `SettingsBody`; `apply_settings`'s per-field `ValueError` pattern
(`default_theme`'s validation, not read in this pass) is the model to copy either way.

`api/sos/routers/kits.py:120` (`{"people": people_count(conn), ...}`) and `:110` (`kit_view`'s
`"people": people`) are the two places `GET /kits`/`GET /kits/{slug}` report a people count today
— both switch to `settings.people` once the register is gone (section 1).

## Surprises worth flagging back to the plan

- `web/src/screens/Tasks.tsx` + `web/src/situation/TaskRow.tsx`'s per-task "Who is doing this"
  assignment reads the household register and isn't named anywhere in the no-setup spec, but it
  breaks the moment `/household` 404s — needs an explicit decision, not a mechanical deletion.
- The six `needs:` consequence rules in `consequences.yaml` (insulin, cold-chain medicine,
  oxygen, CPAP, hoist, stairlift) are real safety content about medical dependents, not just
  plumbing — deleting the schema fields silently deletes these warnings unless they're rewritten
  as unconditional (always-shown) content first.
