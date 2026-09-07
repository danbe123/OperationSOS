# No setup: design

Date: 2026-09-07. Status: approved in conversation (the owner: "i dont like the stock idea, and the adding user information etc … it's meant to be more general, i dont want loads of setting up for the users"; the cut list below was chosen from three options).

## 1. What this is

The box must be useful to anyone who joins the hotspot without anyone typing anything in first. Everything that only works once a household has been described is removed: the household register, the neighbours list and its street print, Stock, the readiness score and its gaps, and the tasks and readings that are generated per person or per neighbour. What stays is general: the guides, the medical cards, the map, the kits as tick-lists, the situation (services, log, drills), the tasks and forecasts that follow from the services, notes and pins, the tools, the system screen and the assistant.

One number survives, because the kits need it: **how many people**, a setting with a one-tap stepper on the Kit screen, default two. It is the only thing a household is ever asked.

Out of scope: dropping the database tables (they stay, unread, so a box that already holds data loses nothing on upgrade and a later restore is possible); changing the kits content; the map.

## 2. What is removed

- **API**: the household, neighbours and stock routers and their endpoints; the street-list print; the readiness store and refresh; the `readiness_score` field on `/status`; the household, stock and neighbours parts of transfer (export still succeeds; those parts are omitted; an import that carries them ignores them with a note in its summary).
- **Engine**: `readiness()` and the readiness part of the View; the household-needs and neighbour-skills matching; the `stock` predicate; the `who: household` and `who: neighbours` task and reading rules; the `Model` fields for household, neighbours, stock and meeting point. The `kits` rows stay for the Kit screen's own progress but no longer score anything.
- **Rules content**: every rule in `playbooks/rules/*.yaml` that carries `needs:`, `skills:`, `who:` or `stock:` is deleted; the schema drops those fields.
- **Frontend**: the Household hub and its sub-screens (People, Neighbours, Stock, The plan, Notes and pins); the readiness panel on Now and the "How ready you are" heading; the "Household and stock" summary on Now; the "In this household" panel on Medical; "Add to Stock" and the Stock line on kit items; the Stock label on nothing (Stock is gone); the Board's stock countdown; the Tools tiles for Stock and the household plan; the `/plan/*` routes and the `/plan#…` redirects (they now go to `/notes` or `/situation#log` as below).
- **Tests, fixtures and e2e** for all of the above; specs and README lines that describe them are rewritten, not deleted, so the record says what changed and why.

## 3. What replaces it

- **People count**: `settings.people` (integer, default 2, minimum 1, maximum 20). `GET /api/settings/people` and `PUT /api/settings/people {people}`; it is also returned on `GET /kits` and `GET /kits/{slug}` as `people` and used by every kit's scaling (a gated kit still scales by the count when its gate would have matched; without a register, `relevant_when` has nothing to test, so every kit is relevant and the "Not needed for this household" group goes). The Kit overview shows a stepper "For N people" with minus and plus, saving on tap; the kit page shows the same number in its "Quantities are for N people" line with a link back to the overview.
- **Now in peacetime**: the band (nothing to show), the title "Everything is working", then "Start here": the kits' basic-tier progress in one line ("Kits: 12 of 84 basic items ticked", linking to `/kit`), the drill button, and the guide tiles as today. No score, no gaps.
- **Notes**: a screen at `/notes` (title "Notes and pins") reached from Now's "Notes" tile and from the map's pin flow, holding the notes-and-pins list and the "Add a note" button, exactly as the former `/plan/notes` did. The event log stays on `/situation#log`.
- **The household plan page** stays as content (`/p/household-plan`) and appears in the Guides "Reference" group; its meeting-point idea becomes prose, not a tracked flag.
- **Medical** keeps the cards, the NHS tiles and the library.
- **Kits**: items keep ticks; the quantity text uses the people count; "Add to Stock" and the Stock line are gone; the print button prints every kit as before.
- **Transfer**: the parts list becomes conditions, scenario, tasks, checklist, notes, home, events, settings (people).

## 4. Tests

- API: the removed endpoints answer 404; `/status` has no `readiness_score`; `GET/PUT /settings/people` round-trips and rejects 0 and 21; kits scale by the setting; transfer omits the removed parts and tolerates an old export that has them; the engine's View has no `readiness` and no `neighbours` keys; rules load without the removed fields and the schema rejects them.
- Web: Now peacetime shows "Start here" with the kits line and no score; `/notes` lists notes and pins and adds a note; Kit overview stepper saves and re-scales; Medical has no household panel; `/plan` and `/plan/*` are gone (404 page); the shell's Now destination no longer matches `/plan`.
- Existing tests for the removed screens are deleted; tests that asserted the removed panels on Now, Medical, Board and the kit page are rewritten.

## 5. Risks

- A box that has already been set up loses nothing but stops showing it; the upgrade note says so.
- The rules engine's per-person tasks were the most personal thing the box did; losing them is the point, but the tasks that remain must still read well with no name in them.
