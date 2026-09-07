# Tasks that are prioritised: design

Date: 2026-09-07. Status: approved in conversation (the owner: "when I add scenarios that are happening the to-do list doesn't seem prioritised and under-thought-out").

## 1. What is wrong

A nuclear-war drill with power and phones off produced twenty tasks: six generic power-cut jobs in "now"
(fridge doors, cooker off, CO alarm) and every scenario checklist item in "today", alphabetically, with
"Everyone in the room; stay in for 48 hours" ninth. Three causes: scenario checklist items all land in
one bucket; the engine sorts a bucket by title; only fifteen task rules exist and none is scenario-aware.

## 2. Checklist items carry urgency and keep their order

A scenario checklist line is `- [ ] text {#id}` or `- [ ] text {#id now}` with an optional bucket token
after the id: `now`, `hour`, `today` (the default), `week`. `parse_checklist` returns `{id, text, bucket}`;
the engine makes the task with that bucket; the item's `why` is "<Scenario title>: right now" / "in the
first hour" / "today" / "this week". Ticks are unaffected (the id is unchanged). The validator requires
every scenario checklist to carry at least one `now` item and rejects an unknown token.

## 3. Order is the author's, not the alphabet

`engine.tasks` sorts by bucket only, with a stable sort, so within a bucket tasks keep the order they
were produced in: rule tasks in `tasks.yaml` file order, then checklist items in checklist order. A rule
may carry `rank: <int>` (default 100) to move above or below others in its bucket; checklist items rank
at 100 in their own order. Scenario rules (section 4) rank 10 so a scenario's first actions lead the
"now" bucket ahead of generic housekeeping.

## 4. Scenario-aware rules

`tasks.yaml` rules may name a scenario: `when: {scenario: nuclear-war}` (with other conditions as now) and
`unless: {scenario: …}`; `task_rule_applies` reads `model.scenario["slug"]`. Generic housekeeping rules
that a scenario's own first actions supersede carry `unless: {scenario: [nuclear-war, chemical, …]}` or are
demoted with `rank: 200` while any scenario is active (`when: {scenario: any}` / `unless: {scenario: any}`
are allowed: `any` means a scenario is running). Every one of the twenty scenarios gets its first actions
as `now` rules or `now` checklist items: at least three, in the order a household should do them.

## 5. Next on the board and Now

`nextTasks` (board) and the situation sheet show the first three outstanding tasks in this order. The
report groups by bucket as now.

## 6. Tests

Parser: bucket tokens, default, unknown token error. Engine: bucket order then stable production order;
`rank`; scenario `when`/`unless` including `any`; a nuclear-war drill's first three tasks are the
scenario's own "now" items, and fridge doors are not in the first five. Validator: a scenario with no
`now` item fails; the real tree passes. Content: every scenario checklist has ≥ 3 `now` items.
