# Authoring guide

Playbooks, modules, quick cards and reference pages are Markdown files with YAML front matter. `sos validate-playbooks` checks them (`make test` runs it), `sos index` puts them into search, and the API renders them on request, so a saved file shows up on the next page load.

## Where files live

| Kind | Path | Route |
|---|---|---|
| scenario | `playbooks/scenarios/<slug>.md` | `/s/<slug>` |
| module | `playbooks/modules/<slug>.md` | `/m/<slug>`, and inline wherever a scenario includes it |
| card | `playbooks/cards/<slug>.md` | `/medical/card/<slug>` |
| page | `playbooks/pages/<slug>.md` | `/p/<slug>` |

The file name is the slug: lower-case letters, digits and hyphens. It must equal the `id` in the front matter.

## Front matter

`playbooks/schema.json` is the schema, one `$defs` entry per kind. Every document has these five fields:

| Field | Meaning |
|---|---|
| `id` | the slug, equal to the file name |
| `title` | the heading, also shown in search results |
| `icon` | an icon name from the frontend's vocabulary; unknown names render as a book |
| `order` | sort position within its kind (scenarios use the numbers from spec section 2) |
| `summary` | one sentence for tiles and lists |

Scenarios add `modules` (slugs of the modules the body includes), `overlays` (map overlay ids from `manifest/overlays.json` that switch on when the map opens from the playbook), `reviewed` (the owner's sign-off date `YYYY-MM-DD`, or `null` until reviewed) and `sources`. Modules, cards and pages may carry `sources`; pages must carry `category`: `comms`, `reference`, `plan`, `about` or `fieldcraft`, which picks the list the page appears in (`fieldcraft` pages are the UK field-craft set on the Field craft screen).

```yaml
---
id: nuclear-war
title: Nuclear war
icon: radiation
order: 1
summary: A nuclear strike on the UK. Fallout, shelter, water, radiation sickness.
modules: [radiation, water, shelter-heat, medical, sanitation, comms, evacuation]
overlays: [nuclear-sites, health, water]
reviewed: 2026-09-10
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    url: https://assets.publishing.service.gov.uk/media/67b5f85732b2aab18314bbe4/National_Risk_Register_2025.pdf
    as_at: 2025-01-16
  - title: Nuclear War Survival Skills
    doc: nwss
---
```

A `sources` entry has a `title` and, when the source is in the library, `doc: <manifest id>` (a PDF or EPUB item) or `kiwix: <zim item id>/<article path>`; the validator checks that the id exists. `url` records where the source came from and is never rendered as a link; a `url`-only source is a warning, not an error. `as_at` is `YYYY-MM-DD`, or `YYYY-MM` when only the month is known, and is shown next to the citation.

## Scenario body

A scenario body contains exactly these seven headings, in this order, each non-empty:

```markdown
## Right now
## First 72 hours
## First month
## Long term
## UK specifics
## Checklist
## Go deeper
```

Modules are declared in `modules:` and inserted where a line `{{module:<slug>}}` appears (any section except Checklist). The validator errors when a declared module is never included or an include names an undeclared or missing module. Sections are rendered as tabs; keep "Right now" short enough to read on a phone without scrolling much.

## Checklist ids

`## Checklist` contains only task-list lines, `- [ ] text` or `- [ ] text {#id}`. Ticks are shared by everyone on the box (`PUT /api/playbooks/<slug>/checklist/<id>`) and stored by playbook and item id. The id is the explicit `{#id}` when given, otherwise the slug of the text (lower-case, hyphens, at most 60 characters). **Rewording a checklist item without an explicit id changes its id and resets its state**, so give every item an explicit id and keep it when the wording changes. Ids must be unique within a playbook. Task lists inside an included module get the id `<module-slug>/<item-id>` and are stored under the including playbook, so the same module ticked in two playbooks has two states.

## Link scheme

Markdown links use these schemes; `sos validate-playbooks` checks every target exists and the frontend resolves them to routes.

| Link | Opens |
|---|---|
| `kiwix:<id>/<path>` | the reader at that article, e.g. `kiwix:wikipedia_en_all_maxi/Potassium_iodide` |
| `doc:<id>` | the PDF or EPUB viewer for a manifest item |
| `doc:<id>#page=<n>` | the same document at page n |
| `map:?overlay=<id>&overlay=<id>` | the map with those overlays switched on |
| `playbook:<slug>` | a scenario playbook |
| `module:<slug>` | a module on its own |
| `card:<slug>` | a medical quick card |
| `page:<slug>` | a reference page |

The box is offline: do not link to the internet from a body. Put the origin of a fact in `sources[].url` instead and cite the library copy inline: every dose, distance, time or law carries a citation such as `([NRR 2025, p. 45](doc:nrr-2025#page=45))` so the reader can check it.

## Modules, cards and pages

- **Modules** are written once and included by playbooks. Headings are free (`##`), task lists are allowed and become part of the including playbook's checklist.
- **Cards** are one screen each: the title and the first three steps fit without scrolling on the kiosk (853x480) and on a 360 px phone; later steps scroll. Numbered steps, `**Warning:**` lines for warnings, when to stop or escalate, and the source.
- **Pages** carry `category`; tables render as tables (the PMR446 channel list, UK numbers, band plans).

## Kits

A kit is a tiered, tickable list of things to have. One YAML file each, `playbooks/kits/<slug>.yaml`, shown at `/kit/<slug>` and listed at `/kit`. The shape is fixed by `playbooks/kits/schema.json` and loaded by `api/sos/kits.py`; `sos validate-playbooks` checks every kit against the schema and every link, source and tier the same way it checks a playbook.

- **Tiers.** Every kit has the same three, nested rather than exclusive: `basic` (`days: 3`, "Three days"), `serious` (`days: 14`, "Two weeks") and `full` (`days: 90`, "No help coming"). The day counts never vary between kits; the one-sentence `why` on each tier does, and says what that tier buys you in this particular kit. The serious tier assumes you already hold the basic one, and the full tier assumes both.
- **Items.** Each item carries an `id` (`^[a-z0-9]+(-[a-z0-9]+)*$`, stable for ever, because it is what a tick is stored against), a `tier`, a `name`, and either a `why` or a `link` — usually a `why`, which is one sentence saying why the thing is on the list at all.
- **Quantities.** `qty` is `{amount, unit, per}`. `per: person-day` is scaled by the number of people on the register and by the tier's day count, so 3 L of water per person-day shows as "36 L for 4 people over 3 days" on the basic tier and "168 L for 4 people over 14 days" on the serious one. `per: person` is scaled by people only, `per: household` (or no `per`) is not scaled at all. A kit with a `relevant_when` scales by the people who match its gate rather than by everyone on the register, so six nappies a day for a one-year-old stays six a day in a house of three adults and a baby.
- **Stock.** An item with `stock: {category, unit}` can be handed off to the household Stock table with one tap: the tick screen offers a quantity, and the row is written with `kit_item` set to `<slug>/<item-id>` so it is never added twice. `category` is one of `water`, `food`, `fuel`, `medicine`, `other`, and matches the categories the readiness engine counts days of. When the item's `qty.per` is `person-day`, its `amount` becomes the stock row's per-person-day rate, so the unit in `stock` should be the unit in `qty`. Anything that is water, food, fuel or medicine carries a `stock` block; anything with a `stock` block carries a `qty`.
- **Relevance.** `relevant_when` hides a kit that does not apply to this household: `{age_under: 2}` on the baby and child kit, `{needs_any: [...]}` on pets and livestock, matched against the `needs` and `medications` fields of the register. A kit with no `relevant_when` is for everyone, and only relevant kits count towards the readiness score.
- **Citations.** The same rule as everywhere else on this box: every figure in an `intro` or a `why` carries a citation to the library, `([Prepare](kiwix:prepare_uk/...))` or `([NRR 2025, p. 90](doc:nrr-2025#page=90))`, and `sources` lists at least two entries with a `doc:` or `kiwix:` and an `as_at`. `summary` is 20 to 160 characters; `intro` is 60 to 250 words with at least two citations.
- **Ticks.** They live in the `checklist_state` table alongside scenario checklists, under `playbook = "kit:<slug>"` and `item_id = <item id>`, which is why item ids must never be reworded away.

## Map places

Tapping a place on the map opens a card, and the "What to expect here" paragraph on it comes from one YAML file, `playbooks/map/places.yaml`, loaded by `api/sos/map_places.py` and served as rendered HTML by `GET /api/map/places`. The shape is fixed by `playbooks/map/schema.json`, and `sos validate-playbooks` checks the schema, that all sixteen kinds are present, and every link in the guidance, the same way it checks a playbook.

- **The sixteen kinds**, and they are a closed set because the overlays produce them: `hospital`, `pharmacy`, `gp`, `clinic`, `fuel`, `water-works`, `reservoir`, `spring`, `rail-station`, `airport`, `military`, `nuclear`, `chemical`, `flood-zone`, `footpath`, `access-land`. A missing kind is an error, so a new overlay kind needs a paragraph before it ships.
- **`expect`** is one Markdown paragraph of 40 to 120 words, plain UK English, second person, present tense, no bullet lists and no headings. It is read by a frightened person on a phone standing in the street, so it says what the place is for, what it will and will not do for them in an emergency, and what to do instead. It ends with one guide link, `([Vehicles and fuel](module:vehicles-fuel))`.
- **`link`** is the guide the card's button opens, `page:<slug>`, `module:<slug>` or `card:<slug>`, and it is the same guide the paragraph ends with. The endpoint resolves it to a URL and looks its title up, so nothing is repeated here.
- **The four lists.** Besides `expect`, every kind carries four lists of short bullets, all four required, shown under fixed headings in this order:

  | Key | Heading | What it says | Count |
  |---|---|---|---|
  | `have` | Usually here | the resources a place of this kind normally holds and whether they survive an outage: water, food, fuel, power, heat, shelter, tools, medical, comms, people with skills | 3 to 7 |
  | `useful` | Worth going when | the situations in which this place helps, by scenario (blackout, flood, cold, no water, evacuation, injury, war) | 2 to 5 |
  | `avoid` | Stay away when | when it is dangerous, pointless or a target: crowds, looting, contamination, closure | 2 to 5 |
  | `approach` | How to go about it | what to bring, when in the day, who to ask, how to behave, what to offer, the law | 2 to 6 |

  Each bullet is **6 to 30 words and 20 to 220 characters**, plain UK English, present tense, imperative where it is an instruction. Inline Markdown is allowed, and a bullet that carries a figure carries the guide link that already holds that figure (`([Vehicles and fuel](module:vehicles-fuel))`); a bullet that carries no figure needs no link. `sos validate-playbooks` checks the counts and lengths against the schema, every link in every bullet, and the word range, reporting `map/places.yaml: <kind>: <key>[<n>]: …`. `GET /api/map/places` returns them as `sections: [{id, title, html}]` in that order, each `html` one rendered `<ul>`.
- **Figures.** Every number, distance or law in a paragraph is one the linked guide already carries, taken from that guide, rather than a new fact introduced here: the 30 litre petrol limit from [Vehicles and fuel](module:vehicles-fuel), the 15 cm and 30 cm of floodwater from [Evacuation](module:evacuation), the one-minute rolling boil from [Water disinfection](page:water-disinfection).
- **The test tree** carries its own `api/tests/fixtures/playbooks/map/places.yaml`: the same prose with the guide links rewritten to slugs the fixture tree holds. Change the real file and change that copy too.

## Validation

`sos validate-playbooks` (run by `make test`) checks: front matter against the schema; the seven scenario headings present, in order and non-empty; that every `kiwix:`, `doc:`, `module:`, `card:`, `page:` and `playbook:` target exists in the manifest or the playbook set; that `map:` overlays and `overlays:` entries exist in `manifest/overlays.json`; that module declarations and includes agree; that checklist ids are unique; and that every `sources[].doc` or `kiwix:` resolves (warning for `url`-only). `--deep` (on the box after `sos sync`) also requests every `kiwix:` path from kiwix-serve and checks every `doc:` file on disk. `--all-scenarios` fails unless all twenty scenario slugs from spec section 2 exist. Output is one line per problem, then `FAILED <n> errors` (exit 1) or `OK <n> documents`.

## Style

British English. Emergency numbers are 999, 111 (NHS), 105 (power cut) and 0345 988 1188 (Floodline). Drug names are the UK names (paracetamol, adrenaline). Every icon has a word next to it in the app, so `icon` is decoration, not meaning. The product is "Operation SOS", "SOS" for short.

## Conventions (sub-plan 03)

- Icons are words from the fixed vocabulary in docs/superpowers/plans/2026-09-03-03-content.md ("Icon vocabulary"); unknown names render as a book.
- Modules use exactly these headings: `## Key facts`, `## What to do`, `## UK specifics`, `## Go deeper`, and never contain `- [ ]` lines.
- Cards use exactly these headings: `## When to use`, `## Steps`, `## Warnings`, `## Stop or escalate`, `## Source`. Steps 1 to 3 are at most 70 characters; "When to use" is at most 110 characters (the one-screen rule). Warnings start with `**Warning:**`.
- Scenario checklist items always carry an explicit `{#id}` so that rewording never resets anyone's ticks.
- Every dose, distance, time or law is followed by a citation in brackets: `([NRR 2025, p. 45](doc:nrr-2025#page=45))`, `([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/))`.
- Zimit article paths are the crawled URL without scheme (`www.gov.uk/buying-carrying-knives`); Wikipedia paths are the underscored title; Stack Exchange paths are `questions/<id>/<slug>`.
- British English; 999, 111, 105, 0345 988 1188; UK drug names; never "NOMAD".
