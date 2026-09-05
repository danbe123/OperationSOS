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
