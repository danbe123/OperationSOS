# Kits: design

Date: 2026-09-06. Status: approved in conversation; the owner asked for the build to proceed without further gates.

## 1. What this is

A sixth destination, **Kit**, that turns "what should we have in the house" into tiered, tickable lists that feed the existing Stock inventory and the readiness score. Fifteen authored kits (medical, water, food, power and light, comms, sanitation and hygiene, warmth and shelter, fallout and CBRN, grab bag, car, baby and child, pets and livestock, documents and cash, tools and repair, growing food), each with three nested tiers: **basic** (three days, the government baseline), **serious** (two weeks, what every playbook on this box plans for) and **full** (no help coming). Ticks are shared by everyone on the box, like scenario checklists. Ticking an item that maps to stock offers to add it to Stock with the quantity already worked out for this household.

Out of scope: per-person kits, shopping-list export, barcode or photo capture, kit items that depend on which scenario is running.

## 2. Content: `playbooks/kits/<slug>.yaml`

One YAML file per kit, validated by `sos validate-playbooks` against `playbooks/kits/schema.json`. The file name is the `id`.

```yaml
id: water
title: Water
icon: water
order: 2
summary: Stored drinking water, containers and the means to make more.
intro: |
  Markdown. Same citation rule as pages: every figure carries a doc:/kiwix: citation.
sources:
  - {title: Prepare, kiwix: prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/, as_at: 2026-09-05}
relevant_when:                      # optional; absent means always relevant
  age_under: 2                      # any household member younger than N
  needs_any: [pet, dog, cat, hens]  # any household member's needs or medications contains one of these
tiers:
  basic:   {title: Three days,     days: 3,  why: The government's own baseline.}
  serious: {title: Two weeks,      days: 14, why: What every playbook on this box plans for.}
  full:    {title: No help coming, days: 90, why: A season with no mains and no shops.}
items:
  - id: stored-water
    tier: basic
    name: Drinking water in sealed containers
    qty: {amount: 3, unit: L, per: person-day}
    stock: {category: water, unit: L}
    why: Bottled, or filled containers, rotated yearly.
    link: module:water
```

Rules:

- `id`, `title`, `icon`, `order`, `summary`, `tiers`, `items` and `sources` are required; `intro` and `relevant_when` optional. `sources` entries follow the playbook schema (`title` plus `doc:` or `kiwix:`; `as_at`).
- `tiers` has exactly the keys `basic`, `serious`, `full`, each with `title`, `days` (integer, basic < serious < full) and `why`.
- An item has `id` (unique within the kit, `^[a-z0-9]+(-[a-z0-9]+)*$`), `tier` (one of the three), `name`, optional `qty`, `stock`, `why`, `link`, `note`.
- `qty.per` is `person`, `person-day`, `household` or absent (a single object with `amount` defaulting to 1). `qty.unit` is free text. The scaled amount is `amount × people` for `person`, `amount × people × tier.days` for `person-day`, `amount` otherwise, where `people` is the household register count or 1.
- `stock.category` is one of the Stock categories (`water`, `food`, `fuel`, `medicine`, `other`); `stock.unit` is the Stock unit. An item with `qty` but no `stock` is a tick-only item.
- `link` uses the existing link scheme (`module:`, `page:`, `card:`, `playbook:`, `doc:`, `kiwix:`, `map:`) and is checked by the validator like every other link. Links inside `intro` are checked too.
- Tiers nest: the serious tier means everything in basic plus the serious items; completion of a tier counts only that tier's own items.
- Kits are content, not rules: no `when` on items, no scenario dependence.

The first version ships the fifteen kits above with the `relevant_when` set on baby-and-child (`age_under: 2`) and pets-and-livestock (`needs_any: [pet, dog, cat, hen, chicken, goat, sheep, horse, rabbit, livestock]`). The other thirteen are always relevant.

## 3. Storage and API

- Ticks live in the existing `checklist_state` table with `playbook = "kit:<slug>"` and `item_id = <item id>`. They therefore ride along with backup and transfer merge unchanged, and the readiness engine can read them the same way it reads scenario ticks.
- `stock` gains a nullable column `kit_item TEXT` holding `<kit>/<item id>`. `db.init_schema` adds it with `ALTER TABLE` when missing (the first column migration in the schema; a small `_ensure_column` helper).
- Content loading: `ContentCache` learns the `kit` kind from the `kits/` directory and parses YAML rather than Markdown front matter; `intro` is rendered through the same Markdown renderer and link resolver as pages, with directives applied.

Endpoints, on the `/api` prefix, in a new `routers/kits.py`:

| Method and path | Body | Returns |
|---|---|---|
| `GET /kits` | | `{people, kits: [{slug, title, icon, order, summary, relevant, tiers: {basic: {done, total}, serious: …, full: …}}]}` in `order` |
| `GET /kits/{slug}` | | the kit: `slug, title, icon, order, summary, intro_html, sources, relevant, people, tiers: [{id, title, days, why, done, total, items: [...]}]` where an item is `{id, name, why, note, link, href, qty: {amount, unit, scaled, text} | null, stock: {category, unit} | null, checked, updated_at, stock_item: {id, quantity, unit, expires, days_left} | null}` |
| `PUT /kits/{slug}/items/{item_id}` | `{checked, stock?: {quantity, expires?, notes?}}` | the kit, as above |
| `DELETE /kits/{slug}/ticks` | | the kit, as above |

- `qty.text` is the sentence the screens show: "168 L for 4 people over 14 days", "4 for 4 people", "1". `href` is the resolved route for `link`.
- `PUT` with `stock` creates a Stock row (name = item name, category and unit from the item, `per_person_day` from `qty` when `per` is `person-day`, `kit_item` set) and ticks the item. `PUT` with `stock` on an item whose `stock_item` already exists returns 409. Unticking never touches Stock. Deleting a Stock row from the Household screen leaves the tick alone.
- The relevance test uses the household register only: `age_under` compares `age`; `needs_any` does a case-insensitive substring match against `needs` and `medications`, the same match the rules engine uses.
- Every change to a tick or to Stock calls `readiness.refresh`, as the household router does today.

## 4. Readiness

The score stays 0 to 100. The weights in the situation-engine spec (section 7) change from 40/30/20/10 to:

| Part | Points | Detail |
|---|---|---|
| Stock days | 30 | water 12 (3 days), food 11 (7 days), medicine 7 (14 days) |
| Household coverage | 30 | unchanged |
| Plan | 15 | home on the map 6, contacts 5, meeting point 4 |
| Practice | 10 | unchanged |
| Kits, basic tier | 15 | proportion of basic-tier items ticked across relevant kits |

The engine's `Model` gains `kits: tuple[dict, ...]` (`{slug, title, relevant, basic_total, basic_done}`), built by `build_model_for` from the content cache and `checklist_state`. Gaps: one line per relevant kit whose basic tier is not complete ("Water kit: 2 of 5 basic items", link `/kit/water`, points = that kit's share of the 15, rounded), so the peacetime Now screen sends people to the kit that needs them. Existing tests that assert the stock-gap point values move to the new numbers.

## 5. Screens

- `destinations.ts`: a sixth entry `{to: '/kit', icon: 'boot', label: 'Kit'}` between Guides and Medical, matching `/kit`. The comment and the shell test say six. The bottom bar on a 360 px phone shows six icons with labels; the rail gains one row.
- `/kit` (`screens/Kits.tsx`): heading, one sentence on what kits are and that ticks are shared, then tiles in `order`. Each tile: icon, title, summary, and a three-segment progress line with "basic 3/5 · serious 0/6 · full 0/4". Kits with `relevant: false` sit under a "Not needed for this household" heading, still openable. A print button prints every kit as one packing list using the existing print styles.
- `/kit/:slug` (`screens/Kit.tsx`): intro, then the three tiers as collapsible sections. Basic is open by default; the others open on tap (and serious opens itself once basic is complete). An item row reuses the tick row from the shared `Checklist` component's `TickedLine`: tick target, name, `qty.text`, `why`, the link; underneath, either the linked Stock line (quantity, unit and the existing expiry/days badge) or, once ticked and when the item has `stock`, an "Add to Stock" button that opens an inline form prefilled with the scaled quantity and optional use-by date. "Reset ticks" at the bottom behind a confirm, as on scenarios. Undo after a tick works as it does for checklists.
- Household screen Stock rows with `kit_item` show a small "from the Water kit" label linking to `/kit/water`.
- Themes, touch targets and components: existing `Tile`, `panel`, `list`, `progress-line`, `badge`, `field`; nothing new in the design system.

## 6. Validation and tests

- `sos validate-playbooks` loads `kits/*.yaml`, validates against `kits/schema.json`, checks id equals file name, unique item ids, tier keys, `days` ordering, every `link` and every link in `intro`, every source, and that `stock.category` is a Stock category. `--all-scenarios` is unaffected. Output lines follow the existing `kits/<slug>.yaml: <problem>` form.
- `api/tests/test_kits.py`: parsing and scaling (per, person-day, household, absent), relevance (age, needs), the four endpoints including the 409, the Stock row creation with `kit_item`, tick reset, and readiness points and gaps for kits.
- `api/tests/test_playbooks_content.py`: a `KITS` list with the fifteen slugs in order; front matter keys; tiers present; every item has `why` or `link`; intro citations.
- `api/tests/test_engine.py`: the new weights.
- Web: `tests/screens/kits.test.tsx` (overview tiles, progress text, not-needed group), `tests/screens/kit.test.tsx` (tiers collapse, tick, add-to-stock form prefill, stock line, reset confirm), the shell test updated to six destinations, Stock row label test.
- e2e: one spec that opens `/kit`, opens Water, ticks an item, adds it to Stock, and sees the line on the Household screen.

## 7. Risks

- Six destinations on a 360 px bar is tight; if labels wrap, the bar drops labels for icons at that width (decided at build time by the existing bar styles, not by this spec).
- `checklist_state.playbook` is a free string, so `kit:` keys need no schema change, but the playbooks router must not accept `kit:` slugs; it already 404s on unknown scenarios.
- The readiness rebalance changes the number people see on the Now screen the day it ships; the gap list explains why.
