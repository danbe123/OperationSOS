# Round 0: the design plan

The plan the rebuild was made from, written before any code was changed, then checked against the
brief (`docs/superpowers/specs/2026-09-06-interface-redesign.md`) and the design rules in section 11
of `docs/superpowers/specs/2026-09-03-operation-sos-design.md`.

## 1. What the thing is

A household's emergency box on a wall. It is read by frightened people, often in poor light, often
one-handed on a phone, sometimes across a dark kitchen. Its job is to answer **what do I do now**,
and then let people read deeper. It should feel like a well-kept instrument: quiet, legible, and
always in the same place. Nothing on it is decorative.

Three consequences that drive every decision below:

1. **The situation is the subject.** The engine's answer is the first thing on the screen, not a
   strip among many. When nothing is wrong the box says so and shows how ready the household is.
2. **The furniture never moves.** Five destinations, in the same order, in the same place, on every
   screen. You always know where you are and how to get back.
3. **One of everything.** One task list, one search, one set of tokens, one border weight, one
   radius. Variety is a cost paid by a reader at 03:00.

## 2. Tokens

One system, in `web/src/styles/tokens.css`, on `:root[data-theme]`. Every theme carries the same
role names; nothing outside this file states a colour.

| Role | What it is | vault | field | blackout |
|---|---|---|---|---|
| `--ground` | the page | `#0b120c` | `#f3efe4` | `#000000` |
| `--panel` | raised surfaces (cards, the band, the rail) | `#121b14` | `#ffffff` | `#0a0000` |
| `--sunken` | inputs, table headers, the deepest surface | `#18251a` | `#ebe5d6` | `#150505` |
| `--ink` | body text | `#dcefdd` | `#1b1b1b` | `#ff9d93` |
| `--ink-muted` | secondary text | `#96b69a` | `#474740` | `#ff7a6e` |
| `--link` | a link in running text | `#6cf08c` | `#1a3f8a` | `#ffc4bc` |
| `--signal` | the one accent: live state, primary action | `#6cf08c` | `#15532e` | `#ffc4bc` |
| `--on-signal` | text on the accent | `#0b120c` | `#ffffff` | `#000000` |
| `--ok` | working | `#6cf08c` | `#15532e` | `#ffc4bc` |
| `--warn` | patchy, due soon | `#f2c14e` | `#6b4400` | `#ffa79c` |
| `--danger` | off, stop, delete | `#ff8a76` | `#94170f` | `#ff8074` |
| `--line` | the one border | `#2c4a30` | `#c3b9a2` | `#5a1c17` |
| `--line-strong` | a border that must be seen (state chips) | `#47764d` | `#8d846f` | `#8a2b23` |
| `--focus` | the keyboard focus ring | `#ffb000` | `#1a3f8a` | `#ffc4bc` |

Structure tokens: `--radius: 6px`, `--touch: 48px`, `--rail: 96px`, `--bar: 64px`, `--measure: 72ch`,
`--kb-height` (set by the on-screen keyboard).

**What changed from the brief, and why.** The brief's colour list is a starting point and three of
its values do not reach the 7:1 floor the same brief sets, so they were tuned along their own hue
rather than replaced:

- vault `--danger` `#ff6b57` gives 6.3:1 on the panel; lifted to `#ff8a76` (7.7:1). `--ink-muted`
  `#8faf93` gives 7.3:1, which is inside the rounding of the measurement, so it was lifted to
  `#96b69a` (7.9:1) to leave headroom.
- field `--signal` `#1f6f3f` gives 6.2:1 on white and `--danger` `#b3261e` 6.5:1; both were darkened
  along the same hue (`#15532e`, `#94170f`). Field `--warn` at `#b7791f` is 3.6:1 — an amber cannot
  be 7:1 on paper, so field's warn is the dark ochre `#6b4400`, which is what a printed field manual
  uses anyway, and the symbol carries the meaning regardless.
- blackout's set (`#c9463b` ink on black) is 4.4:1. Blackout stays a single red hue on black, but the
  three steps are separated by luminance instead of by hue — `#ff8074` off, `#ffa79c` patchy,
  `#ffc4bc` working — all above 8:1, with the symbol still doing the real work. Dimness in blackout
  is delivered by the `dim` mode's brightness filter, not by unreadable text.

Everything else in the brief's palette is used as written.

## 3. Type

Bundled faces only: Inter (body and everything on phones), Source Serif 4 (field headings), VT323
(the box's voice: the app name in the rail, and the board's clocks, in vault only).

One scale, in px so the kiosk and the phone differ only where the spec says they must:

| Token | Phone | Kiosk | Used for |
|---|---|---|---|
| `--t-meta` | 16 | 16 | timestamps, "worth 12 points", table meta |
| `--t-body` | 16 | 18 | everything you read |
| `--t-lead` | 22 | 22 | section headings (h2), the band's line |
| `--t-title` | 28 | 28 | the screen title (h1) |
| `--t-display` | 40 | 40 | the board's headline, a quick card's steps |
| `--t-board` | 64 | 64 | the board's clock |

Line height 1.5 for body, 1.2 for headings. Measure capped at 72 characters. Sentence case
everywhere; no tracked-out uppercase; the only eyebrow left in the app is the band's own label.
Body text carries no glow, no shadow and no display face in any theme — the scanline and glow of
vault apply to the rail, the band and headings only.

## 4. Layout: the shell

```
kiosk 853x480                                    phone 390
┌──────┬───────────────────────────────────────┐ ┌───────────────────────┐
│ SOS  │ ● Power off 4 h  ▲ Mobile patchy   ▸  │ │ ● Power off 4 h     ▸ │  band
│      ├───────────────────────────────────────┤ ├───────────────────────┤
│ Now  │ ← Back   Now              [search   ] │ │ ← Back   Now        ⌕ │  screen head
│ Guide│                                       │ │                       │
│ Med  │ Do now                                │ │ Do now                │
│ Map  │  □ Fill the bath while water runs     │ │  □ Fill the bath …    │
│ Find │ Coming up …                           │ │ Coming up …           │
│ ─────│                                       │ ├───────────────────────┤
│ Sys  │                                       │ │ Now Guide Med Map Find│  bar
└──────┴───────────────────────────────────────┘ └───────────────────────┘
```

- **Rail** (≥ 700 px, 96 px wide): the app name in VT323, then Now, Guides, Medical, Map, Find, then
  a footer with System, AI and the theme button. The current destination is lit: filled panel, a
  signal-coloured left edge, and `aria-current="page"`. Every item is an icon **and** a word.
- **Bar** (< 700 px, 64 px tall, safe-area padded): the same five destinations, same order.
- **Band**: sticky at the top of the content column whenever a scenario is running, a drill is on, or
  any condition is not working. It carries the drill flag, the scenario and its clock, one chip per
  condition that is not working, the count of outstanding jobs, and a link to the sheet. In peacetime
  it is not rendered at all — Now shows readiness instead, and no other screen needs the space.
- **Screen head**: Back, the screen title as an `h1`, the screen's own actions, and (≥ 700 px) the
  compact search field. Screens no longer render an app bar; they render a `<Screen>` with a title.
- **Content**: one left-aligned column, 72-character measure, 24 px gutters on the kiosk and 16 on
  phones. Two panes only where the content is genuinely two things: a playbook's guidance beside its
  task list, and the map beside its panel.

## 5. The five destinations

| Destination | What is behind it |
|---|---|
| **Now** (`/`, `/now`) | The band, "Do now", "Coming up", "The box thinks", "Read", then the household and stock summary. In peacetime: readiness with its gaps as the to-do list, the drill button, and the household summary. One tap inside: the situation sheet, tasks, the board, the plan, the household register, stock, neighbours. |
| **Guides** (`/guides`) | The manual. Search, then the twenty scenarios, then modules, field craft, phone and radio, reference pages and tools. A scenario opens with its tabs; its checklist is the shared task list filtered to that scenario. |
| **Medical** (`/medical`) | 999 through the directives, quick cards, children's doses, the household's medical needs, NHS A to Z, the medical library. |
| **Map** (`/map`) | As today, with the panels reorganised into one toolbar: Layers, Find, Pins, Home, Nearby, Measure, Share, Print. |
| **Find** (`/search`, `/find`) | Search across everything with source chips, then the library browse, then the assistant when it is on. |

Every existing route keeps its path. `/now`, `/guides` and `/find` are added.

## 6. Components

Flat panels, one border weight (1 px `--line`), one radius (6 px), no shadows, no gradients, no
decorative motion. Motion only answers a tap: a tick, an accordion, a sheet. `prefers-reduced-motion`
removes even those.

- **Panel** — the only container. A heading, a body, optional actions.
- **Task row** — one tick, one title, one "why", one "who". Playbook checklists, engine tasks and
  drill jobs all render as this row: one list of things to do.
- **State chip** — icon, word, symbol, colour, duration. Used by the band, the sheet, the board.
- **Tile** — icon plus word plus one line. Used by Guides, Medical and Tools only.
- **Button** — 48 px minimum, a verb, an icon beside the verb. Primary is `--signal`; danger is an
  outline, never a filled red.
- **Badge** — a symbol and a word, never colour alone.
- **Notice** — the toast, the calls notice and the drill bar share one look.

## 7. Words

Verbs on buttons: "Start the clock", "Mark done", "Set as home". Plain state words: working, patchy,
off. No system names in front of a household ("the engine", "the View", "playbook" as a noun the
reader must learn). British English, sentence case, no jargon.

## 8. Files

- `src/styles/tokens.css` — the three themes and the structure tokens, plus the print palette.
- `src/styles/type.css` — the faces, the scale, headings, the measure, `.muted`, print type.
- `src/styles/shell.css` — the rail, the bar, the band, the screen head, the content column, the
  overlays (keyboard, idle, notices, modal).
- `src/styles/components.css` — buttons, inputs, panels, tiles, chips, badges, tasks, lists, tables.
- Screen files only for what is unique: `screens/now.css`, `screens/guides.css`, `screens/map.css`,
  `screens/board.css`, `screens/tools/tools.css`.

`app.css`, `screens/home.css` and `situation/situation.css` are deleted and their live rules moved
into the four files above; dead rules go.

## 9. Checked against the brief

Read back against section 2's principles and section 6's inventory. Two things in this plan read like
a default and were changed before building:

- The first draft gave Now a hero with a search field and a strapline, inherited from the old Home.
  A hero is a marketing pattern; a box on a wall has no hero. Now opens on the band and the first
  task, and the search field lives in the screen head where it is the same on every screen.
- The first draft kept the six tool tiles on Now. They are a second navigation competing with the
  rail, so they moved to Guides, which is where the manual lives, and Now carries only what the
  situation asks for plus the household and stock summary.

## 10. The screenshots

`web/scripts/screenshots.mjs` captures every entry below at **853x480** (the kiosk, in kiosk mode)
and **390** wide (a phone), in **vault**, **field** and **blackout**, from the Playwright fixture
server. It rebuilds first, so a later round cannot photograph an older interface.

```
cd web && node scripts/screenshots.mjs            # into docs/superpowers/critique/round-0
cd web && node scripts/screenshots.mjs round-3    # a later round
cd web && node scripts/screenshots.mjs round-3 map   # only the shots whose name contains "map"
```

Each file is `round-0/<name>-<width>-<theme>.png`. The inventory entry each name covers:

| Inventory entry | Screenshot name | State reached |
|---|---|---|
| `/` Now, peacetime | `now-peacetime` | readiness, gaps, the drill button |
| `/` Now, conditions off | `now-power-off` | power off an hour, tasks, forecast, proposals |
| `/` Now, phones down | `now-phones-down` | `calls: hidden`, the no-phones way in |
| `/` Now, drill | `now-drill` | drill running on a scenario |
| `/` Now, engine unreachable | `now-engine-down` | the box says so and keeps the rest of itself |
| `/` Now, empty household and stock | `now-empty-household` | nothing registered yet |
| `/situation` sheet | `situation-sheet` | two conditions off, states, since, note, sensors |
| `/situation` carry | `situation-carry` | the export codes with Previous and Next |
| `/situation` drill | `situation-drill` | the drill form with a scenario chosen |
| `/tasks` | `tasks` | the four buckets with assignment |
| `/tasks` empty | `tasks-empty` | nothing to do |
| `/board` scenario active | `board` | conditions, next jobs, sunset, bulletin, stock, log |
| `/board` peacetime | `board-peacetime` | everything working |
| `/guides` | `guides` | twenty situations, then pages and tools |
| `/guides` filtered | `guides-filtered` | one filter field across every kind |
| `/s/:slug` Right now | `scenario-right-now` | tabs, guidance beside the task list |
| `/s/:slug` a later phase | `scenario-later` | first 72 hours |
| `/m/:slug` | `module` | standalone module with read-aloud |
| `/p/:slug` | `page` | a reference page with its table |
| `/medical` | `medical` | 999 line, quick cards, NHS A to Z, library |
| `/medical` phones down | `medical-phones-down` | 999 will not connect |
| `/medical/card/:slug` | `quick-card` | extra-large steps and the warning |
| `/medical/dose` | `childrens-doses` | a dose for a four-year-old |
| `/map` | `map` | the one toolbar over the map |
| `/map` layers | `map-layers` | bases, terrain, overlays with coverage |
| `/map` nearby | `map-nearby` | facilities with the nearest and its runners-up |
| `/map` home | `map-home` | home set, flood zone, grid reference |
| `/map` share | `map-share` | the link and its QR code |
| `/search` Find, empty | `find-empty` | what it searches |
| `/search` Find, results | `find-results` | source chips, results, the library behind |
| `/library` | `library` | categories, item cards, drive badges |
| `/read/:id/*` | `reader` | an article with the theme injected |
| `/doc/:id` missing | `document-missing` | a document the box does not have |
| `/ai` off | `assistant-off` | the card explaining how to turn it on |
| `/plan` household | `household` | the register with medical needs |
| `/plan` neighbours | `neighbours` | the street list and who to check on |
| `/plan` stock | `stock` | days left with its badges |
| `/fieldcraft` | `field-craft` | the field craft pages |
| `/radio` | `phone-and-radio` | the comms pages and the numbers |
| `/tools` | `tools` | the tool list |
| `/tools/timers` | `timers` | a countdown running, the CPR beat, fallout |
| `/tools/sun` | `sun-and-moon` | sun times and the moon phase |
| `/tools/calc` | `calculators` | generator, battery, solar, rations |
| `/tools/log` | `event-log` | the log and its entry field |
| `/system` | `system` | status, hotspot, power, AI, settings, PIN, updates |
| `*` not found | `not-found` | the way back |
| Connect a phone panel | `connect-a-phone` | both QR codes and the addresses |
| The on-screen keyboard | `keyboard` | the kiosk keyboard under the search field |
| The notices toast | `notice` | "not in the library" from a reader link |

## 11. What the first look at the screenshots changed

The plan was built, then photographed, then fixed. Everything below came from looking at round 0's
own screenshots before declaring it done:

- **The chosen condition state was drawn as the primary action**, so "off" appeared in the accent
  green. Each state now wears its own colour and keeps its symbol.
- **The board carried the rail and the band**, which said in small type what the board says in large.
  `/board` is now the whole screen; a tap anywhere still comes back.
- **The scenario's two panes split at 900 px**, so the kiosk — 853 wide, 757 once the rail is off —
  got one column. The split is now 800 px, and the guidance sits beside its task list on the kiosk.
- **The rail did not fit 480 px** and scrolled the theme button out of reach. The rows lost four
  pixels of padding each and the icons two, and the whole rail now fits.
- **The compact search field said "Search Wikipedia, NHS, ma…"**. It says "Search the box".
- **Find showed a list of suggestions over the results it had just been asked for**, because the term
  arrived from the URL. Suggestions now answer typing only.
- **Guides offered a "Field craft (0)" chip** and called the situations "playbooks", a word the
  household never has to learn. Empty chips are gone and the word with them.
- **The checklist counted itself twice**, in a badge and in its own summary line.
- **The plan's sections were not landmarks** — a `<section>` with no name is not a region — so a
  screen reader had no way to jump between the household, the street list, the stock and the log.
- **MapLibre's own controls arrived as white boxes** on a phosphor-green map. The zoom, compass and
  scale now follow the theme, and their icons invert in the two dark ones.
- **The map toolbar had eight tools and 757 pixels**, so Share fell off the end. "Locate me" moved
  inside Find place, which is where it belonged: one panel that either reads the device's position
  or says why it cannot, with the place, postcode and grid-reference entry either way. The toolbar
  is now exactly the seven the brief names, plus Print in the screen head.
- **The task list called its first bucket "Now"**, the same word as the destination. It says "Right
  now", which is what the guides call the same moment.
- **On a phone the theme button sat above the screen title**, on a line of its own, because it had no
  place in the head's order. It shares the top line with Back.
- **The band wrapped to two rows on a phone.** Its label is what did not fit beside the chips, and
  the chips say what the label says.
- **A guide put its sources between the guidance and the checklist on a phone**, so the jobs came
  after the paperwork. The two panes are now grid areas: one column puts the jobs first, two put the
  sources under the guidance they belong to.
- **The kiosk keyboard did not appear for a field that was already focused** — Find focuses its
  search field on arrival — because there was no `focusin` left to hear. It now looks at what is
  focused when it starts.
- **The situation's QR codes were 220 px** for chunks of up to 800 characters, which is a dense code
  to read off a screen with a phone. They are 260.
