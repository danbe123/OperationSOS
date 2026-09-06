# Round 2: critique

Reviewed against `docs/superpowers/specs/2026-09-06-interface-redesign.md` (sections 5 and 6), the
round-0 plan, the round-1 critique and its Applied section, the 294 screenshots in
`docs/superpowers/critique/round-1/`, and the running app at `http://127.0.0.1:8080` driven with
Playwright at 853x480, 844x390 (landscape phone) and 390x844.

## Verdict

Round 1's ten mostly landed and the box reads better for it: the quick card is now legible across a
room, the situation sheet paints the state it means in all three themes, the number pad has its 1, 4
and 7 back, and one noun — things to do — runs through the job list. What nobody has looked at is the
box in the state it was built for: the engine turns `dim` on for "power off and dark" (per
`2026-09-06-situation-engine-design.md`), and `:root[data-dim="on"] body { filter: brightness(0.55) }`
then does two things at once — it makes `body` a containing block, so the kiosk keyboard, the toasts,
the modals and the idle board all position against a 256 px shell instead of the screen, and it drags
measured body contrast from 14.6:1 down to 4.9:1 in vault, 5.7:1 in field and 3.5:1 in blackout,
with secondary text at 3.0:1. Beneath that sit two vendor surfaces nobody has touched (the raw pdf.js
toolbar, the unstyled radio buttons), a `.btn-small` at 40 px that quietly breaks the 48 px floor on
the whole map toolbar, Back, the band and every "Read more", and a front door that says four
contradictory things about the same water.

## The ten

### 1. Dim mode — the 03:00 blackout state — breaks every overlay and the contrast floor

**Screens** all of them, whenever `modes.dim` is true. **Files** none: dim is a cross-cutting state
in section 6 of the brief and it is not in any of the 294 screenshots. Reproduce at
`http://127.0.0.1:8080/search?kiosk=1` with `document.documentElement.dataset.dim === 'on'`.

`tokens.css:105` puts `filter: brightness(0.55)` on `body`. A filtered element becomes the containing
block for every `position: fixed` descendant, so `.kb-panel`, `.notices`, `.modal-backdrop`,
`.idle-overlay` and `.idle-board` (`shell.css:150–181`) stop measuring from the viewport and start
measuring from `.app`, which is `calc(100dvh - var(--kb-height))` = 256 px. Measured live: with dim
on the kiosk keyboard computes `top: 32px` and covers the search field it was opened for, with 224 px
of dead black below it and the app unusable; with dim off the same panel computes `top: 256px` and is
correct. The same filter also destroys the 7:1 floor the brief sets — measured ink-on-panel: vault
14.62 → 4.92, field 17.22 → 5.70, blackout 10.36 → 3.54; muted text 7.93 → 3.06, 9.36 → 4.46,
8.16 → 2.96. The engine raises this mode precisely when the power is off at night.

**Fix** Stop dimming with a filter. Add a dim variant of each theme's tokens (`:root[data-dim="on"]`
overriding `--ground`, `--panel`, `--sunken`, `--ink`, `--ink-muted`, `--line` to a darker set that
still measures 7:1 against its own ground) and, on the kiosk, drop the hardware backlight through the
existing System control. Then add `dim` to `screenshots.mjs` so at least Now, the quick card, the
keyboard and a toast are photographed in it.

### 2. The document viewer is raw pdf.js, and a missing document says nothing

**Screen** `/doc/:id`. **Files** `document-missing-853-vault.png`, `document-missing-853-blackout.png`,
`document-missing-853-field.png`, `document-missing-390-vault.png` and the rest of the six.

Below the app's own screen head sits an untouched pdf.js toolbar: a light-grey bar, twelve icons with
no words, a page box reading "0 of 0", an "Automatic Zoom" select, and a blank grey page filling the
screen. It is the same light grey in blackout, where it is the only white slab in a red-on-black
interface at 03:00. Every rule the redesign set is broken in one strip — no theme, no tokens, icons
without words, targets far under 48 px, a system word ("Automatic Zoom") — and the state the
screenshot is named for, a document the box does not have, is communicated only by the numeral 0.

**Fix** Give the viewer the app's chrome and hide pdf.js's own: Back (already there), "Page 4 of 210"
with ‹ and › at 48 px, "Find in this document", "Text size", "Print", and thumbnails behind one
labelled toggle — styled from `components.css`, in all three themes. When the file is absent, render
no viewer at all: a panel reading "The box does not have this document." with what to do next
(a link to the library entry and to Find).

### 3. The kiosk keyboard costs half the screen and takes the rail with it; the rail also fails on a landscape phone

**Screens** every kiosk text field. **Files** `find-empty-853-vault.png`,
`find-results-853-vault.png`, `guides-filtered-853-vault.png`, `keyboard-853-vault.png` and their
field and blackout pairs.

`.shell { height: calc(100dvh - var(--kb-height)) }` shrinks the whole shell, rail included, to 256 px
whenever the keyboard is up. The rail needs 469 px for its nine rows, so it is cut after Map: Find is
half-drawn and **AI, System and the theme button are unreachable while anyone is typing**, with no
scroll cue. On Find the fix round 1 made — scroll the results up — pushed the field itself off the
top, so the screenshots show "5 results." and two results with no way to see or edit what was typed;
on Guides the same keyboard leaves the count line and zero results. The same rail failure happens
without the keyboard on a landscape phone: measured at 844x390 the rail is 469 px in a 390 px
viewport, so System and the theme button are off-screen there too.

**Fix** Make the keyboard a panel over the content column only (`left: var(--rail)` on the kiosk) and
leave the rail at full height; keep the active field and the first row of results pinned above
`--kb-height` together, not one or the other. Give the rail a `min-height: 0; overflow-y: auto` body
with the five destinations fixed and the footer (System, AI, theme) always visible — or move the
footer to a single overflow row — so no viewport under 470 px tall can hide a destination.

### 4. `.btn-small` is 40 px, and it is most of the app's controls

**Screens** the map toolbar, every screen head, the band, every job, the plan. **Files**
`map-853-vault.png`, `map-390-vault.png`, `now-power-off-853-vault.png`, `tasks-853-vault.png`,
`household-853-vault.png`, `situation-sheet-390-vault.png`.

`components.css:21` sets `.btn-small { min-height: 40px }`, and `.searchbar-compact` repeats it at
line 205. Measured live, on both widths: all seven map tools (Layers 97x40 … Share 90x40), Back on
every screen (86x40), the band's "Situation" and "N to do", "All of them", "Read more" on every job,
Edit and Remove on every person and every stock line, the theme button (148x40), "Try again", "Open
the plan", "System", every panel Close. The brief's floor is 48 px and this is the majority of the
secondary controls in the box. Worse, on a new box the two first-run calls to action are inline text
links: "Add who lives here" measures 145x20 and "Add water, food and fuel" 189x20 on the kiosk
(`now-peacetime-853-vault.png`).

**Fix** Raise `.btn-small` and `.searchbar-compact` to `min-height: var(--touch)`, keeping
`--t-meta` type and the tighter padding so nothing grows visually except the hit area; the map
toolbar still fits 757 px at 48 px tall. Make the two first-run links `.btn` buttons on their own
row.

### 5. The front door says four contradictory things about the same water

**Screen** `/` in peacetime. **Files** `now-peacetime-853-vault.png`, `now-peacetime-390-vault.png`,
`now-empty-household-853-vault.png` and the field and blackout pairs.

One screen, four statements: "No water is recorded yet." (the lead), "› Water: 1.5 days for 3 people"
(a gap row, two lines below it), "Nobody registered yet. Stock is counted for one person until you add
people." and "No stock recorded." The lead comes from `stockDays()` and the gap from
`view.readiness.gaps` (`Readiness.tsx`), two sources answering the same question differently, and the
person count disagrees with itself as well (3 people vs one person vs nobody). `now-empty-household`
is pixel-identical to `now-peacetime`, so the inventory's "empty household and stock" state is not
actually being shown. The gap rows also reuse `.task-tick`, so a link that navigates wears the shape
of a job you can tick, with a chevron where the box goes.

**Fix** Take every number on the peacetime panel from one source (the engine's readiness) and say it
once: "Nobody is registered yet, so the box counts stock for one person." then the gaps. Give the gap
rows their own class — no `.task-tick` — so nothing that is not tickable looks tickable. Make the
empty-household fixture actually empty so the state gets photographed.

### 6. The same tick behaves three different ways

**Screens** `/`, `/tasks`, `/s/:slug`. **Files** `tasks-853-vault.png`, `now-power-off-390-vault.png`,
`scenario-right-now-390-vault.png`, `scenario-later-390-blackout.png`.

Ticking on `/tasks` (verified live: `PUT /api/tasks/fridge-doors-shut` 200) makes the row **vanish**
— no toast, no strikethrough, no undo, only the running count changing from "4 to do, 0 done." to
"4 to do, 2 done.". On Now the same tick leaves the row in place with a strikethrough. On a guide it
leaves it in place with a strikethrough and "· ticked 3 days ago". One list, three behaviours, on the
single most-used control in the box, and the one that disappears is the one on the screen titled
"Things to do". A wrong tap is unrecoverable without finding and clearing the "Show done" chip.

**Fix** One behaviour everywhere: the row stays where it is, struck through, tick filled, with the
"who and when" line, and a "Show done" chip that filters the list on the next load rather than on the
tap. Add an inline **Undo** in the row for ten seconds after a tick. Do not strike through the meta
line, only the title (`scenario-right-now-390-vault.png` strikes "ticked 3 days ago" too).

### 7. The drill cannot be started, and its debrief argues with itself

**Screen** `/situation#drill` and the debrief. **Files** `situation-drill-853-vault.png`,
`now-drill-853-vault.png`, `now-drill-390-vault.png`.

Live, on arrival, **"Start drill" is `disabled`** with nothing on the screen saying why (you must
first pick from a select that reads "Choose a situation…"), and `.btn:disabled { opacity: 0.55 }` on
a filled `--signal` button is a low-contrast green slab in vault and near-invisible in blackout. On
ending, the debrief prints "Drill ended: Nuclear war. 2 h in on the clock, 2 of 18 jobs ticked."
directly above its own log line "Drill ended: **0 tasks done** in 120 minutes (drill)" — two counts
of the same thing disagreeing, and two formats for the same duration — with the household's real
ticks mixed into the drill log, tagged "(kiosk)" and "(drill)". Before that, `now-drill-390-vault.png`
spends 280 px — a third of the phone — on a banner, a band and a theme row before the first job, and
says the word Drill three times in it.

**Fix** Never ship a disabled primary with no reason: leave Start enabled and, on a tap with nothing
chosen, focus the select and show "Choose a situation first"; or default the select to the most
likely situation. Compute the debrief's counts from one place and phrase the duration once ("2 h in,
2 of 18 jobs ticked"). Drop the "(kiosk)"/"(drill)" suffixes for "on the box" / "in the drill", and
collapse the drill banner into the band's existing Drill chip plus an "End drill" button so the phone
gets one row of drill chrome, not four.

### 8. Now never says 999 will not connect, and the box still has two 999 components

**Screens** `/`, `/m/:slug`, `/p/:slug`, `/s/:slug` against `/medical`, `/medical/card/*`,
`/medical/dose`, `/tools/timers`, `/radio`. **Files** `now-phones-down-853-vault.png`,
`now-phones-down-390-vault.png`, `medical-phones-down-853-vault.png`.

With both networks down the front door is titled "Mobile and landline off" and then says nothing at
all about 999 — `Now.tsx` renders neither `Emergency999` nor `CallsNotice` — while `/tools/timers`, a
screen for boiling water, carries the 999 panel unconditionally. And round 1's "one component" is two:
`Emergency999` (a `.panel`, "999 will not connect while both networks are down") on five screens and
`CallsNotice` (a `.notice` line, "Phone numbers on this page will not connect while the phones are
down") on Module, Page and Scenario — one fact, two looks, two wordings, and two names for the same
condition ("both networks" / "the phones").

**Fix** Render `Emergency999` at the top of Now whenever calls are hidden — it is the most important
new fact on the screen — and delete `CallsNotice`, replacing its three uses with `Emergency999` so
there is genuinely one component and one sentence. Take the 999 panel off `/tools/timers` unless
calls are hidden, where the warning is the point.

### 9. Guides amputates the one useful line, and its copy does not follow the filter

**Screen** `/guides`. **Files** `guides-853-vault.png`, `guides-390-vault.png`,
`guides-filtered-853-vault.png`, `guides-filtered-390-field.png`.

`guides.css:8` clamps the tile line to two lines, so the real first sentences round 1 introduced are
cut mid-word on exactly the tiles that had something to say: "A radiation release from a UK or…",
"A nationwide or regional blackou…", "A respiratory pandemic that…", "Ransomware or sabotage takes
o…". The part that tells a reader whether this guide is theirs is the part removed. And after
filtering to two results the section still carries "Situations — Twenty situations: what to do right
now and over the months after." (`guides-filtered-390-field.png`), so the screen states a count it is
not showing. On the kiosk the filter block takes the top 190 px of 480, leaving one row of tiles.

**Fix** Write or trim each guide's line to fit two lines at 390 (about 60 characters) in the content,
and drop the clamp so nothing is ever cut mid-word; where no short line exists, show none. Replace
the section blurb with a live count — "Twenty situations" unfiltered, "2 situations match "water""
when filtered — and collapse the filter block to one row (field plus chips on the same line) on the
kiosk.

### 10. On a phone the map panel covers the map you are being asked to aim

**Screen** `/map`. **Files** `map-home-390-vault.png`, `map-nearby-390-vault.png`,
`map-layers-390-blackout.png`, `map-390-vault.png`, `map-home-853-vault.png`, `map-share-853-vault.png`.

The Home panel says "Centre the map on where you live, then set it" while occupying every pixel of the
map except a 45 px sliver, so the instruction cannot be followed without closing the panel that
carries it; Nearby and Layers do the same. On the kiosk the panel's primary action is worse off —
`map-home-853-vault.png` shows only the top sliver of the green "Set as home" button at the bottom
edge, with no scroll cue — and `map-share-853-vault.png` clips both the share URL (a 40 px box showing
one and a half lines) and the caption under the QR code. The toolbar is still the deferred round-1
watch item: Print takes a non-scrolling row of its own above a seven-tool scroller that clips "Ho"
mid-word with no fade or chevron.

**Fix** On phones make the panels a bottom sheet at 55 % height with the map live above it, and give
Home a "Use the centre of the map" line that updates as the map moves. On the kiosk make the panel
body scroll with its actions pinned to the panel's bottom edge, and let the share URL be a two-line
`textarea` with a "Copy the link" button. Move Print into the toolbar as the eighth tool (it fits at
48 px on 757 px) and delete its separate row; add a right-edge fade and a chevron to the phone
scroller.

## Watch list

1. **The board's big clock is 40 px in two of three themes.** Measured live: vault renders
   `.board-now` at 64 px VT323, field and blackout at 40 px Inter (`board-853-field.png`,
   `board-853-blackout.png`). `--t-board` is 64 in the plan and the board is the across-the-room
   element. Keep the size in every theme; only the face is meant to change.

2. **Unstyled radios repeat the fault the checkbox fix cured.** `input[type="radio"]` only gets
   `accent-color`, so in vault and blackout the *unselected* base map is a solid grey disc and the
   selected one a thin ring — the filled control is the one that is off (`map-layers-853-vault.png`,
   `map-layers-390-blackout.png`). Draw radios the way checkboxes are now drawn. While there, the
   overlay swatches are colour-only squares with no symbol.

3. **The warning triangle now means five things, and "Remove" is the loudest word on the plan.** ⚠
   marks "999 will not connect", "The box cannot read the situation", the drill chip, the **Timers**
   tile and the peacetime **"Practise a drill"** primary (`tools-853-vault.png`,
   `now-peacetime-853-vault.png`, `now-engine-down-853-vault.png`) — a hazard symbol on two things
   that are not hazards. Meanwhile `--danger` outlines a Remove button beside every person, neighbour
   and stock line (`household-853-vault.png`, `neighbours-390-vault.png`), so red on the plan means
   housekeeping. Reserve ⚠ for danger and put Remove behind Edit.

4. **"Playbook" survived, and so did a dot-run.** `Timers.tsx:97` renders "…<Link>Radiation
   module</Link> · <Link>Nuclear war playbook</Link>" — the word the brief says a household never has
   to learn, joined by a middle dot, after round 1 claimed both were gone. Also still system-facing:
   "Development profile" and "Version 0.1.0" and "CPU 51°C" on `/system` (`system-390-blackout.png`),
   "Core" as a drive name, and "Scan to open SOS" (`connect-a-phone-853-vault.png`, whose heading is
   clipped off the top at 480 px).

5. **Three things the fixtures never photograph.** `/fieldcraft` renders ten pages live but the
   screenshot shows a title and one sentence (`field-craft-853-vault.png`); the `notice` entry is
   pixel-identical to `reader` in all six shots, so the toast has never been reviewed; and the
   inventory's quick card "with phones on and off" has no phones-off screenshot at all — worth
   checking, because the live CPR card's step 1 reads "Shout for help, a phone on speaker beside you
   — call 999" directly under a panel that would say 999 will not connect. Also: on the phone the
   `<nav>` precedes `<main>` in the DOM, so Tab visits the five bottom-bar destinations before the
   first job and there is no skip link.

## Applied

Every screenshot below is `docs/superpowers/critique/round-1/<name>` before and
`docs/superpowers/critique/round-2/<name>` after, at the same width and in the same theme. The whole
inventory was re-shot with `node scripts/screenshots.mjs round-2`, and it now carries five entries
that round 1 could not photograph at all: the dim mode, a field craft page, the quick card with the
phones off, a toast that is actually on the screen, and a peacetime front door with a household in it.

### 1. Dim mode — the 03:00 blackout state — breaks every overlay and the contrast floor

Root cause, removed: `:root[data-dim="on"] body { filter: brightness(0.55) }`. A filtered element is
the containing block for every `position: fixed` descendant, so the kiosk keyboard, the toasts, the
modals and the idle board measured from a 256 px shell instead of the screen; and the same filter
took ink from 14.6:1 to 3.5:1.

Dim is now a palette. `tokens.css` carries a third block per theme on `:root[data-dim="on"]`,
`:root[data-theme="field"][data-dim="on"]` and `:root[data-theme="blackout"][data-dim="on"]`,
overriding `--ground`, `--panel`, `--sunken`, `--ink`, `--ink-muted`, `--link`, `--signal`,
`--on-signal`, `--ok`, `--warn`, `--danger`, `--line`, `--line-strong` and `--focus`. The ground and
the panel go darker than the theme they dim, the ink comes down with them but never below 7:1
against either, and the accent is dimmed with everything else — vault's `#6cf08c` becomes `#57c274`,
blackout's `#ffc4bc` becomes `#e8a29a`, field's paper drops from `#f3efe4` to `#d5cfc0` with its
accents darkened along their own hues to keep the floor. Nothing is filtered, so every overlay
measures from the viewport again.

The unit suite now measures six palettes rather than three (`tests/theme/contrast.test.ts`, 96 cases),
asserts that each dim ground and panel is darker than the theme it dims, and asserts that no
`data-dim` rule carries a `filter` at all. `e2e/dim.spec.ts` measures the live tokens in all three
themes, checks `getComputedStyle(document.body).filter === 'none'`, and opens the kiosk keyboard in
dim to prove it sits on the bottom edge of the 480 px screen with the search field above it.

The kiosk's own backlight is separate hardware and was left where it is: the idle timer and the
System control already drop it (`kiosk/IdleOverlay.tsx`).

New in the inventory: `now-power-off-dim`, `board-dim`, `quick-card-dim`, `keyboard-dim` and
`notice-dim`, at both widths in all three themes.

### 2. The document viewer is raw pdf.js, and a missing document says nothing

The viewer's own chrome is hidden — `pdfViewerCss` sets `--toolbar-height: 0px` and takes
`#toolbarContainer`, `#sidebarContainer`, `#sidebarResizer`, `#findbar`, `#secondaryToolbar` and
`#editorUndoBar` off the screen in every theme — and `screens/Doc.tsx` draws the chrome instead:
Previous, a page field, "of n", Next, "Find in this document" with its match count and a Next match,
and the page size, all `btn-small` at 48 px with a word beside every icon. It drives PDF.js through
its own event bus (`pagesloaded`, `pagechanging`, `scalechanging`, `updatefindmatchescount`,
`documenterror`), and every call is guarded so a viewer that has not finished starting simply does
nothing. Back is the screen head's, which every screen already has.

The colours are no longer a second palette living in the viewer: `viewerTokens()` reads `--ground`,
`--panel`, `--ink` and `--line` off the app's own root at inject time, so the viewer follows the
theme *and* the dim palette. Blackout still inverts the page, because a white page at 03:00 in a
red-on-black theme is a torch in the face.

The missing state is a state, not the numeral 0: `Doc` probes the file with a HEAD request and, on a
404 or 410 (or a `documenterror` from the viewer), renders no viewer at all — a `panel-warn` reading
"The box does not have this document.", who is listed and on which drive, that the file arrives when
the box is built or updated, and two buttons: "Open the library entry" and "Search the box for this".

Before `round-1/document-missing-853-{vault,field,blackout}.png` and the 390 set · after the same
names under `round-2/`.

### 3. The kiosk keyboard costs half the screen and takes the rail with it

`.app` is `height: 100dvh` again. Above 700 px wide and 440 px tall the keyboard's height belongs to
`.app-main` alone (`padding-bottom: var(--kb-height)`), so the rail keeps all 480 px, and
`.kb-panel` starts at `left: var(--rail)` so it covers the content column and nothing else. The rail
itself gives way in the right order: `.mainnav-list` is `flex: 0 1 auto; min-height: 0; overflow-y:
auto` and `.rail-foot` is `flex: 0 0 auto`, so System, AI and the theme button are on the screen at
any height and the five destinations scroll before they do.

The landscape phone is the same fault without a keyboard: 469 px of rail in a 390 px viewport. The
rail's query now carries a height — `(min-width: 700px) and (min-height: 440px)`, in `shell.css` and
in `useWide` — so 844x390 draws the bottom bar, which shows all five destinations at any width, and
the theme button moves to the screen head with it. 853x480 is unchanged.

On Find, the fix round 1 made scrolled the count line to the top and pushed the field off it; the
content column is scrolled to the top instead, so the field, the count and the first results are
above `--kb-height` together.

`e2e/keyboard-rail.spec.ts` measures the rail before and after the keyboard opens, asserts every
destination and the theme button is still visible, asserts the panel starts where the rail ends, and
checks the landscape phone gets a bar with all five destinations on the screen.

Before `round-1/find-empty-853-vault.png`, `round-1/find-results-853-vault.png`,
`round-1/guides-filtered-853-vault.png`, `round-1/keyboard-853-vault.png` and their field and
blackout pairs · after the same under `round-2/`.

### 4. `.btn-small` is 40 px, and it is most of the app's controls

`components.css` raises `.btn-small` and `.searchbar-compact` to `min-height: var(--touch)`, keeping
`--t-meta` type and the tighter padding, so the map toolbar, Back on every screen, the band's
buttons, every "Read more", every Edit and Remove, the theme button, "Try again", "Open the plan",
"System" and every panel Close clear the floor without growing visually. The map toolbar still fits.
The two first-run calls to action are `.btn` buttons on a row of their own rather than 145x20 and
189x20 inline links. While there, a disabled primary gives up its fill rather than its legibility —
`.btn-primary:disabled` is the panel ground with muted ink, not a 55 %-opacity accent slab.

Before `round-1/map-853-vault.png`, `round-1/map-390-vault.png`, `round-1/now-power-off-853-vault.png`,
`round-1/tasks-853-vault.png`, `round-1/household-853-vault.png`, `round-1/now-peacetime-853-vault.png`
· after the same under `round-2/`.

### 5. The front door says four contradictory things about the same water

Every number on the peacetime panel now comes from the engine's readiness and is said once.
`Readiness.tsx` no longer counts stock itself: its lead is "One thing would help most." (or "Nothing
is outstanding.") and the gaps follow. Who the box is counting for is said in exactly one place, the
household panel: "Nobody is registered yet, so the box counts stock for one person." The gap rows
have their own class — `.gap-row`, a 48 px full-width row with the chevron on the right — and no
longer wear `.task-tick`, so nothing that is not tickable looks tickable.

The fixture was making the contradiction possible: `readiness.gaps` was the hard-coded string "Water:
1.5 days for 3 people" while the stock was empty. It is derived from the same register and the same
stock the household panel counts (`e2e/fixtures/engine.ts:readinessGaps`), so the two cannot
disagree. And `now-peacetime` now has two people and four and a half days of water in it, which makes
`now-empty-household` a different picture rather than a pixel-identical one.

Before `round-1/now-peacetime-853-vault.png`, `round-1/now-peacetime-390-vault.png`,
`round-1/now-empty-household-853-vault.png` and the field and blackout pairs · after the same under
`round-2/`.

### 6. The same tick behaves three different ways

One behaviour, in one place. `situation/Tick.tsx` carries the ten-second undo window
(`useTickUndo`), the Undo button and the "who and when" line, and both `TaskRow` (Now and Things to
do) and `Checklist` (a guide) use them. A ticked job stays exactly where it is, struck through, tick
filled, with `person, ticked just now` on its own line and an inline **Undo** beside it for ten
seconds. Only the title is struck through: `.task-time` carries `text-decoration: none`, because the
meta line is the answer, not part of the job.

On `/tasks` the row no longer vanishes. "Show done" filters the jobs that were already done when the
screen was opened — the set is seeded on the render the list first arrives in, not in an effect, so
nothing is painted and then taken away — and turning the chip off re-seeds it. Anything ticked on
this screen stays where it is until the next load.

`e2e/tick.spec.ts` ticks and undoes the same job on `/tasks`, on `/` and on `/s/grid-collapse`, and
checks the computed `text-decoration-line` of the title and the meta line.

Before `round-1/tasks-853-vault.png`, `round-1/now-power-off-390-vault.png`,
`round-1/scenario-right-now-390-vault.png`, `round-1/scenario-later-390-blackout.png` · after the
same under `round-2/`.

### 7. The drill cannot be started, and its debrief argues with itself

"Start drill" is never a disabled primary with nothing saying why: it stays live, and a tap with
nothing chosen focuses the situation select and says "Choose a situation first." beside the button
(and "Choose at least one thing that is off in the drill." when that is what is missing).

The debrief counts once and phrases the clock once: "Drill ended: National grid collapse. 2 h in,
1 of 4 jobs ticked." The engine's own "Drill ended: N tasks done in M minutes (drill)" line is
dropped from the log under it (`situation/drill.ts`), because that is the second, disagreeing count
of the same fact. The log speaks in places rather than suffixes — `api/words.ts:eventTitle` turns
"(kiosk)" into "on the box", "(phone)" into "on a phone" and "(drill)" into "in the drill" — and the
event log screen uses the same translation.

The drill's chrome is one row, not four. `DrillBanner`'s bar is gone; the band already carries the
⚑ Drill chip and the scenario, and the way out of the drill is an "End drill" button beside them
(`EndDrillButton`). The debrief travels from the band to the panel under it the way a notice does.

Before `round-1/situation-drill-853-vault.png`, `round-1/now-drill-853-vault.png`,
`round-1/now-drill-390-vault.png` · after the same under `round-2/`.

### 8. Now never says 999 will not connect, and the box still has two 999 components

`CallsNotice` is deleted. `Emergency999` gained one prop, `onlyWhenHidden`, which is the "cannot
call" state on its own, and the three screens that used the notice — Module, Page and Scenario —
render that instead, so there is genuinely one component, one look and one sentence for the fact.
Now renders it at the top whenever calls are hidden, which is the most important new thing on the
front door and was previously not said there at all. `/tools/timers` renders it only when calls are
hidden; a screen for boiling water does not carry a 999 panel while the phones work. `/medical`,
`/medical/card/*`, `/medical/dose` and `/radio` keep both states.

Before `round-1/now-phones-down-853-vault.png`, `round-1/now-phones-down-390-vault.png`,
`round-1/medical-phones-down-853-vault.png`, `round-1/timers-853-vault.png` · after the same under
`round-2/`, plus the new `quick-card-phones-off`.

### 9. Guides amputates the one useful line, and its copy does not follow the filter

The clamp is gone from `guides.css`, and every guide's line is written to fit two lines at 390 px —
about 60 characters — in the content itself, so nothing is cut mid-word and a guide with no short
line shows none. "A radiation release from a UK or…" is "A radiation release from a UK or nearby
site."; "Ransomware or sabotage takes o…" is "Sabotage takes out the NHS, banks or the grid."

Each section counts what it is showing, never what it would show with the filter off: "20 situations.
What to do right now, and over the months after." unfiltered, "1 situation matches “flood”." when
filtered. On the kiosk the filter block is one row — the field and its chips share a line — instead
of 190 px of the 480.

Before `round-1/guides-853-vault.png`, `round-1/guides-390-vault.png`,
`round-1/guides-filtered-853-vault.png`, `round-1/guides-filtered-390-field.png` · after the same
under `round-2/`.

### 10. On a phone the map panel covers the map you are being asked to aim

Every map panel is now a `MapPanel`: a pinned head with its title and Close, a body that scrolls, and
pinned actions along the bottom edge. On the kiosk "Set as home" and "Search from this centre" are in
that pinned row, so the primary action is never the top sliver of a button at the bottom of a 480 px
screen. On a phone the panel is a bottom sheet at 55 % height, so the map an instruction asks you to
aim stays live above the instruction.

Home says what it will save and follows the map: "Set as home will use the centre of the map,
**SU 39 14**. Move the map and this line follows it." The share panel's link is a two-line box with a
"Copy the link" button beside it. Print is the eighth tool in the toolbar rather than a non-scrolling
row of its own above it, and the strip has a fade at its right edge and a chevron that scrolls it, so
"Home" is never cut in half with nothing to say there is more. The fade and the chevron appear only
when the strip really does scroll, measured rather than guessed at a breakpoint, and the chevron sits
over the fading end rather than in the flow — in the flow it took exactly the width that made it
necessary. With the tools' padding tightened the kiosk's seven fit 757 px at 48 px tall with no
chevron at all; a 390 px phone shows three and the chevron.

Before `round-1/map-home-390-vault.png`, `round-1/map-nearby-390-vault.png`,
`round-1/map-layers-390-blackout.png`, `round-1/map-390-vault.png`, `round-1/map-home-853-vault.png`,
`round-1/map-share-853-vault.png` · after the same under `round-2/`.

## The watch list

Taken:

1. **The board's big clock is 40 px in two of three themes.** `.board-now` is `var(--t-board)` — 64 px
   — in every theme; only the face changes, and VT323 stays vault's alone. Before
   `round-1/board-853-field.png`, `round-1/board-853-blackout.png` · after the same under `round-2/`.
2. **Unstyled radios repeat the fault the checkbox fix cured.** `input[type="radio"]` is drawn the way
   the checkbox now is: `appearance: none`, a 26 px `--line-strong` ring on `--sunken` when unchosen,
   and the accent ring with a filled accent dot when chosen — so the filled control is the one that is
   on, in all three themes. Before `round-1/map-layers-853-vault.png`,
   `round-1/map-layers-390-blackout.png` · after the same under `round-2/`.
4. **"Playbook" survived, and so did a dot-run.** `Timers.tsx` no longer says "Nuclear war playbook"
   or joins two links with a middle dot: "Read about radiation" and "Open the nuclear war guide" are
   buttons that say where they go, and so are "Adult CPR card" and "Child CPR card". No user-facing
   string in the app contains the word now. Before `round-1/timers-853-vault.png` · after
   `round-2/timers-853-vault.png`.
5. **Three things the fixtures never photograph.** The ten field craft pages exist in the fixture, so
   `/fieldcraft` is a list of ten rather than a title and one sentence, and `field-craft-page` shows
   one of them in full. The `notice` shot clicked a link that was not there (`hasText: /http/`); it
   clicks "the live article" and waits for the toast, so `notice` is no longer pixel-identical to
   `reader`. `quick-card-phones-off` is new: the CPR card's own step 2 says to call 999, and this is
   the state where it will not connect. Before `round-1/field-craft-853-vault.png`,
   `round-1/notice-853-vault.png` · after the same under `round-2/`, plus the two new names.

Left, with reasons:

- **The overlay swatches are colour-only squares with no symbol** (watch list 2). The swatch is a
  legend key that appears in the layers panel, the printed map and the map's own legend; giving it a
  symbol means giving every overlay a symbol and carrying it through all three, which is a change to
  the map's data, not to a control.
- **The warning triangle means five things, and "Remove" is the loudest word on the plan** (watch list
  3). Half of it is done — "Practise a drill" no longer wears the hazard triangle — but reserving ⚠
  for danger across the drill chip, the Timers tile and the engine-down line, and putting Remove
  behind Edit, is a pass over the symbol and button vocabulary the whole app shares. It is the
  round-3 item the round-1 note about chip shapes already pointed at.
- **"Development profile", "Version 0.1.0", "CPU 51°C", "Core" as a drive name and "Scan to open SOS"**
  (watch list 4). These are System and the Connect panel, which round 2's ten did not reach; the
  clipped heading on `connect-a-phone` at 480 px belongs with them.
- **`<nav>` before `<main>` on a phone, and no skip link** (watch list 5). The order is the shell's
  grid, and a skip link is a new piece of chrome on every screen; it wants its own pass with the rest
  of the keyboard-order work rather than being bolted to one of the ten.

### What the round's own screenshots changed

Round 2 was built, photographed, and then fixed again before it was called done:

- **The map toolbar's own scroll cue was self-fulfilling.** `map-853-vault.png` showed Share clipped
  and a chevron beside it on the kiosk, because the chevron in the flow took the width that made the
  strip overflow. It is out of the flow now, over the fade, and shown only when a measurement says
  the strip scrolls: the kiosk's seven tools fit, and the phone gets the cue it needs.
- **The keyboard's keys did not fit the narrower panel.** With the rail keeping its own 96 px, eleven
  64 px keys overflowed 757 px: `keyboard-dim-853-vault.png` showed "ift" where "shift" should be and
  the delete key cut off at the right edge. The keys share the row now, the wide ones taking twice a
  letter's share, and `e2e/keyboard-rail.spec.ts` walks every key to check it is inside the panel,
  48 px tall, and not clipping its own label.
- **The Guides filter still wrapped its chips to a second row** on the kiosk, which put the count line
  and every tile under the keyboard (`guides-filtered-853-vault.png`). Under 620 px tall the chips are
  one scrolling row.
- **A new box was told to add who lives here twice** — once as the first-run button and once as the
  engine's own gap (`now-empty-household-390-vault.png`). The gap gives way to the button, and the
  count above it follows what is shown.

One thing the new shots record rather than fix: `quick-card-phones-off` shows the CPR card's own step
2, "Call 999 and put it on speaker.", under the panel that says 999 will not connect. The warning is
at least on the screen and above the step now, which it was not before; making the card's own words
follow the condition is content, not chrome, and belongs to a later round.
