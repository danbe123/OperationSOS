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

Scenarios add `modules` (slugs of the modules the body includes), `overlays` (map overlay ids from `manifest/overlays.json` that switch on when the map opens from the playbook), `reviewed` (the owner's sign-off date `YYYY-MM-DD`, or `null` until reviewed) and `sources`. Modules, cards and pages may carry `sources`; pages must carry `category`: `comms`, `reference`, `plan` or `about`, which picks the list the page appears in.

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
