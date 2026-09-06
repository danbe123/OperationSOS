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
