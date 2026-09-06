# Interface redesign: one box, one situation, one manual

Approved brief 2026-09-06: a complete redesign of the frontend for intuitiveness, followed by five rounds of critique and improvement. Constraints from the application spec stand: three themes (vault default, field, blackout), kiosk at 853x480 and phones at 360 to 430 wide, 48 px targets, 18 px body on the kiosk and 16 px on phones, an icon always has a word, colour plus a symbol for any state, every quick card and every scenario's Right now within two taps of Home, search on every screen, no network fonts (the bundled Inter, Source Serif 4 and VT323 only), no new dependencies.

## 1. What is wrong today

Twenty-one screens grew by accretion. Home is a long scroll of unrelated bands (situation, briefing, a hero with search, six tool tiles, twenty scenario tiles, a status strip). There are three places to manage things to do (playbook checklists, the tasks screen, the plan page), three places that list guidance (scenario grid, Tools, Field craft, Phone and radio), and the only navigation is the app bar's Back and Home. Nothing tells a first-time user where they are or what the box is for. The situation engine is the box's point and it arrives as a strip among many.

## 2. Design plan

**Subject**: a household's emergency box on a wall, used by frightened people, often in poor light, often one-handed on a phone. Its job is to answer "what do I do now" and then let people read deeper. The interface should feel like a well-kept instrument, not a website.

**Colour** (per theme, tokens on `:root[data-theme]`; the values below are the vault set, field and blackout carry the same roles):
- `--ground` #0B120C (the panel), `--panel` #121B14 (raised surfaces), `--ink` #DCEFDD (text), `--ink-muted` #8FAF93, `--signal` #6CF08C (the one accent: live state, primary action), `--warn` #F2C14E, `--danger` #FF6B57.
- Field: paper #F3EFE4, panel #FFFFFF, ink #1B1B1B, muted #5C5C55, signal #1F6F3F, warn #B7791F, danger #B3261E.
- Blackout: #000000, #0A0000, ink #C9463B, muted #7A2E27, signal #E0574A, warn #C9463B, danger #FF5A4A (single hue by design; state is always carried by a symbol).

**Type**: Inter for everything on phones and for body on the kiosk; VT323 only for the two places that are the box's voice (the app name in the rail and the board's big clocks) in vault, Source Serif 4 for headings in field. One scale: 16, 18, 22, 28, 40, 64 (the board). Sentence case throughout; no tracked-out uppercase labels; no eyebrows except the single situation band label.

**Layout concept**: a persistent navigation rail on the kiosk (left, 96 px, five destinations) and a bottom bar on phones (five destinations), with the situation band always visible at the top of the content area when anything is off or a scenario is active. Content is left-aligned on a single column with a 72-character measure; the kiosk uses the width for a two-pane layout only where the content is genuinely two things (playbook guidance beside its checklist, map beside its panel).

```
kiosk 853x480                                   phone 390
┌──────┬──────────────────────────────────────┐ ┌──────────────────────┐
│ SOS  │ ● Power off 4 h  ● Phones off 2 h  ▸ │ │ ● Power off 4 h    ▸ │  situation band
│      ├──────────────────────────────────────┤ ├──────────────────────┤
│ Now  │ Do now                               │ │ Do now               │
│ Guide│  □ Fill the bath while water runs    │ │  □ Fill the bath …   │
│ Med  │  □ Shut the fridge and freezer       │ │  □ Shut the fridge   │
│ Map  │ Coming up                            │ │ Coming up            │
│ Find │  Fridge food unsafe   in 3 h         │ │  Fridge food  in 3 h │
│      │ Read                                 │ │ Read                 │
│ ▪▪▪  │  What still works in an outage       │ ├──────────────────────┤
└──────┴──────────────────────────────────────┘ │ Now Guide Med Map Find│
                                                └──────────────────────┘
```

Six destinations: **Now** (the situation, the briefing, the tasks; in peacetime the readiness and a plain "start here"), **Guides** (the manual: scenarios first, then modules, field craft, phone and radio, pages, all searchable and filterable by situation), **Kit** (tiered lists of what to have, ticked by everyone, feeding Stock), **Medical** (cards, doses, NHS, medical library), **Map**, **Find** (search across everything with the library behind it). Household, stock, plan, notes, tools, timers, system and the AI assistant live one tap inside the destination they serve (Household and stock under Now; timers, sun, calculators under Guides as tools; system and AI in the rail's footer).

**Principles**:
1. Now is the front door. The first screen answers "what do I do" from the engine, or says "nothing is wrong, here is how to get ready" in peacetime.
2. One list of things to do. Playbook checklists, engine tasks and drills all appear in the same task list with the same tick, the same assignment and the same "why".
3. The band is the memorable element. Everything else is quiet: flat panels, one border weight, one radius (6 px), no shadows, no gradients, no decorative motion. Motion only answers a tap (a tick, an accordion, a sheet).
4. You always know where you are: the destination is lit in the rail, the screen title is the first line, Back goes where you came from, and Home is the Now destination.
5. Reading is comfortable: measure under 72 characters, 1.5 line height, headings that are headings, tables that scroll, print that works.
6. Words do one job: verbs on buttons ("Start the clock", "Mark done", "Set as home"), plain state words (working, patchy, off), no jargon, no system names.

## 3. Screens

- **Now**: band, "Do now" tasks (tick, assign, why), "Coming up" forecast, "The box thinks" proposals, "Read" links, then Household and stock summary with a link. Peacetime: readiness with its gaps as the to-do list, the drill button, the household and stock summary.
- **Guides**: a search field, then Scenarios (twenty, icon plus name plus one line), Modules, Field craft, Phone and radio, Reference, Tools. A scenario opens with tabs as today but the checklist becomes the shared task list filtered to that scenario.
- **Medical**: 999 line first (through the directives), quick cards, children's doses, household medical needs, NHS A to Z, library.
- **Map**: as today with the panels reorganised into one toolbar (Layers, Find, Pins, Home, Nearby, Measure, Share, Print).
- **Find**: search with source chips, then the library browse (categories, availability), then the AI assistant when it is on.
- **Situation sheet** and **Tasks**: reached from the band; tasks also from Now. **Board**: unchanged in purpose, restyled with the scale.
- **System**: reached from the rail footer, grouped into Box, Network, Screen, AI, Updates, Safety (PIN).

## 4. Implementation notes

- Replace `AppBar` with a `Shell` (rail or bar plus band plus content) rendered by the layout route; screens stop rendering their own app bars and expose a title and optional actions through a small context.
- One stylesheet system: `tokens.css` (themes), `shell.css`, `type.css`, `components.css`, screen files only for what is unique. Delete dead rules.
- Keep every route path that exists (links from content and tests depend on them); add `/now` as an alias of `/` and `/guides`, `/find`.
- Tests: update screen tests for the shell; Playwright specs for the rail on the kiosk, the bar on phones, the two-tap rule (Home to a quick card, Home to a scenario's Right now), and the band.
- Design rules from the application spec are the acceptance floor.

## 5. The critique loop

Five rounds. Each round: a critic agent reviews screenshots of Now (peacetime and power off), Guides, a scenario, a quick card, Medical, Map, Find, the sheet, Tasks and the board, at 853x480 and 390 wide, in all three themes, against a rubric (first-time intuitiveness, hierarchy and scanning, consistency of components and words, touch targets and contrast, copy, the two-tap rule, what a frightened person at 03:00 would misread), and writes a ranked list of at most ten concrete changes with the screen, the problem and the fix. An implementer agent applies them with tests. The round is recorded in `docs/superpowers/critique/round-N.md` with before and after screenshots. Round five ends with the full test target, the browser suite and a rebuilt dev stack.

## 6. Coverage inventory

The redesign is not done until every entry below has been restyled inside the shell, checked at 853x480 and 390 wide, in vault, field and blackout, and appears in the critique screenshots. Nothing is out of scope.

### Routes (all keep their paths)

| Route | Screen | States to cover |
|---|---|---|
| `/` (`/now`) | Now | peacetime (readiness, gaps, drill button), scenario active, conditions off, proposals pending, drill, loading, engine unreachable, empty household and stock |
| `/situation` | Situation sheet | all ten conditions in each state, stale prompt, conflict (409), note editing, clock controls, drill start and end, sensors present and absent, print report, the event log beneath the rows (`#log` deep link) with empty and populated states and its entry form |
| `/tasks` | Tasks | four buckets, empty bucket, done filter, assignment with and without a household, checklist tasks, drill ticks |
| `/board` | Board | scenario active, conditions off, peacetime, no bulletin, no stock, tap to leave |
| `/s/:slug` | Scenario | six tabs, current phase marked, modules as accordions, checklist as the task list, sources, reviewed and unreviewed, print (all tabs open), loading, missing |
| `/m/:slug` | Module | standalone, with checklist items, print |
| `/p/:slug` | Page | reference, comms, fieldcraft and plan categories, calls-hidden notice, read aloud present and absent, print |
| `/medical` | Medical | 999 line through the directives, quick cards, household needs present and absent, NHS installed, NHS on a missing drive, NHS absent |
| `/medical/card/:slug` | Quick card | extra-large type, steps, warnings, stop or escalate with phones on and off, print |
| `/medical/dose` | Children's doses | both medicines, every form, an age under the table, 18 and over, source link to either NHS book |
| `/map` | Map | base switch, terrain, layers panel, find place, locate me (kiosk only), pins, home (set, not set, flood zone), nearby (with results, with missing kinds, no home), measure, share, print, tooltips on hover and tap, calls hidden |
| `/search` | Find | empty, suggestions, results with source chips, partial results notice, no results, library browse |
| `/library` | Library | categories, item cards with drive badges, unavailable items, extended tier on a missing drive |
| `/read/:id/*` | Reader | article, theme injected, text size, external link notice, missing article |
| `/doc/:id` | Document | PDF with thumbnails and search, EPUB, `#page=` deep link, missing file |
| `/ai` | Assistant | off, starting, ready, busy by this screen, busy by another, thermal off, error, streaming answer with citations, refusal |
| `/plan` | Household hub | one row per section (People, Neighbours, Stock, The plan, Notes and pins, What happened) each stating its own state or empty state, old-anchor redirects (`#household`, `#stock`, `#notes`, `#pins`, `#log`) to the sub-screen; `/plan/people`, `/plan/neighbours`, `/plan/stock`, `/plan/plan`, `/plan/notes` each with their list, empty state, add-behind-a-button form, edit and remove, and Back to the hub |
| `/fieldcraft` | Field craft | the ten pages |
| `/radio` | Phone and radio | comms pages, calls hidden |
| `/tools` | Tools | tile list |
| `/tools/timers` | Timers | idle, running countdown, finished, CPR running, fallout marks |
| `/tools/sun` | Sun and moon | pin, place search, polar day and night, moon phase |
| `/tools/calc` | Calculators | defaults, invalid input |
| `/tools/log` | Event log | empty, entries, edit |
| `/system` | System | status, storage, hotspot, ethernet, power mode, backlight (present and 501 fallback), AI toggle, thermal threshold, update progress, theme default, PIN set and unset, PIN dialog |
| `*` | Not found | |
| route error | Unable to open this page | |

### Overlays, panels and chrome

The shell (rail on the kiosk, bar on phones, band, screen title and actions), the notices toast, the on-screen keyboard (kiosk), the idle overlay and the board switch, the Connect a phone panel with its QR codes, the admin PIN dialog, the map panels (Layers, Find place, Locate me, Pins, Home, Nearby, Share), the map tooltip popup, the pin modal, the reader's text-size control, the document viewer chrome, the chip strip on every screen, the read-aloud player, forecast reminder toasts, the DRILL banner, the dim mode.

### Static pages outside the app

`welcome.html` (captive portal landing) and `starting.html` (kiosk boot page) in `web/public` get the same tokens and type.

### Cross-cutting states

Loading, error and empty for every list; the three themes; dim mode; calls hidden; `map_first`; drill; kiosk versus phone; landscape phone; print stylesheet for every printable screen; keyboard focus visible everywhere; reduced motion; RTL not required.
