# Round 3: critique

Reviewed against `docs/superpowers/specs/2026-09-06-interface-redesign.md` (sections 5 and 6), the
round-0 plan, the round-1 and round-2 critiques with their Applied sections, the 336 screenshots in
`docs/superpowers/critique/round-2/` (56 entries at 853x480 and 390, in vault, field and blackout,
dim variants included), and the running box at `http://127.0.0.1:8080` driven with Playwright:
keyboard order and accessibility snapshots, a condition change and the advice that follows it, a
drill from the form to the debrief, export and import, set home and nearby, read aloud, the reader
and a document, the assistant, the map panels on a phone, `page.emulateMedia({media:'print'})` with
PDF exports, and `pnpm build`.

## Verdict

Round 2's ten mostly landed and the box is measurably better for it — dim is a palette rather than a
filter, the rail survives the keyboard, the tick behaves the same way in three places, and the map
panels no longer cover the map. What round 3 finds is that the redesign has been checked as a set of
still pictures and not as a thing anyone uses: the quick card a person opens mid-CPR tells them to
call 999 directly under a banner saying 999 will not connect and then cuts the compression rate off
the bottom of the screen; every printable screen prints black paper in exactly the state a household
prints from; the drill's debrief pushes the rail and two thirds of the content off a 480 px kiosk;
and Find answers "bleeding" with the side effects of warfarin. Underneath that sit the two things
this round was asked to weigh — a keyboard user takes seventeen tab stops to reach the first job with
no skip link and no search on any phone screen, and the front door of a Pi 5 kiosk parses one
2.24 MB JavaScript chunk containing MapLibre and PDF.js before it paints.

## The ten

### 1. The quick card tells you to ring 999 under a banner saying 999 will not connect, and hides the compression rate

**Screen** `/medical/card/:slug`. **Files** `quick-card-phones-off-390-blackout.png`,
`quick-card-phones-off-390-{vault,field}.png`, `quick-card-phones-off-853-*.png`,
`quick-card-853-vault.png`, `quick-card-390-*.png`, `quick-card-dim-*.png` — twenty-four files.

Round 2 recorded this rather than fixing it ("making the card's own words follow the condition is
content, not chrome, and belongs to a later round"). It is the worst thing in the box and it is a
flow, not content. On `quick-card-phones-off-390-blackout.png` the panel reads **"999 will not
connect while both networks are down"** and 120 px below it step 2 reads **"Call 999 and put it on
speaker."** at 40 px. Both are on the screen at once. Two opposite instructions, mid-CPR, at 03:00.

The same card then loses its own answer. At 390 the card ends at "**3 Push hard and**" — the rate,
100 to 120 a minute, is never on the screen. At 853 (`quick-card-853-vault.png`) steps 1, 2 and 3
fit, and step 4 is sliced mid-glyph by the 480 px edge; with the phones off, step 3 is the one being
sliced. There is no "1 of 6", no fade, no chevron, nothing that says the card continues, so a person
kneeling over a body reads a card that appears to end. The card's own name, "CPR (adult)", is set at
`--t-meta` — smaller than its steps, smaller than the `h1` on every other screen, and adult versus
child is the distinction that matters.

**Fix** Three changes, in this order. (a) When calls are hidden, the card's steps must follow the
condition: replace the "call 999" step with "Send someone to a landline, a neighbour or a payphone —
999 will not connect from here" and keep the banner. Give `Card.tsx` the calls-hidden flag it already
has on the same screen and let the card content carry a `calls-on` / `calls-off` variant per step.
(b) Make the card fit: the title at `--t-title` as a real `h1`, the 999 banner reduced to a single
`--t-lead` line (it is duplicated from `/medical` and costs 55–90 px of a 480 px screen), and the
steps paginated — "Step 3 of 6" with 48 px Previous and Next, one step per screen at `--t-display`,
which is what a card read at arm's length wants anyway. Failing pagination, a right-edge fade and a
"3 more steps ▾" button. (c) Add a `e2e` assertion that on both widths, in all three themes, no step
of any quick card has its bounding box crossing the viewport's bottom edge.

### 2. Every printable screen prints black paper, in exactly the state a household prints from

**Screen** `/medical/card/:slug`, `/s/:slug`, `/p/:slug`, `/m/:slug`, `/situation`. **Files** none —
print is a cross-cutting state in section 6 and is in none of the 336 screenshots. Reproduce with
`page.emulateMedia({media:'print'})` on any of them.

`tokens.css:167` carries the print palette on `:root, :root[data-theme]` (specificity 0,2,0). The dim
palettes at `tokens.css:113–148` are written as `:root[data-theme="vault"][data-dim="on"]`,
`:root[data-theme="field"][data-dim="on"]` and `:root[data-theme="blackout"][data-dim="on"]`
(0,3,0), so **the dim palette outranks the print palette and print loses whenever `data-dim` is on**
— which is precisely the night-time power cut in which someone prints a CPR card or a situation
report. Measured in print media on `/medical/card/cpr-adult`:

| theme | dim off | dim on |
|---|---|---|
| vault | paper `#f3efe4`, ink `#1b1b1b` | ground `rgb(5,8,5)`, ink `rgb(182,210,184)` |
| field | paper `#f3efe4`, ink `#1b1b1b` | ground `rgb(213,207,192)` |
| blackout | paper `#f3efe4`, ink `#1b1b1b` | **ground `rgb(0,0,0)`, ink `rgb(224,141,132)`** |

A PDF export of the CPR card in that state is three solid black A4 pages. Two more faults in the same
pass: printed `body` computes to **14.67 px** (≈11 pt) because nothing sets a print body size, under
the 16 px floor the brief sets for the screen and well under what a printed emergency card wants; and
a printed scenario is 29 A4 pages with 236 live links and the `.tabs` strip still `display: flex`,
so the inventory's "print (all tabs open)" prints one tab plus a row of dead tab buttons.

**Fix** Give the print block a selector at least as specific as the dim blocks —
`@media print { :root, :root[data-theme], :root[data-dim], :root[data-theme][data-dim] { … } }` — or
move the whole print palette into a `@media print` block placed after and written with
`[data-theme][data-dim]`. Add `body { font-size: 12pt; line-height: 1.4 }` and `h1 { font-size: 20pt }`
to the print rules. Hide `.tabs` in print and render every phase's content when `matchMedia('print')`
matches. Add a `e2e/print.spec.ts` that asserts, for each printable route and each of the six
palettes, that the computed print `background-color` of `body` is the paper colour.

### 3. The situation sheet still cannot show which state is set, contradicts itself about when, and says "Set from at ."

**Screen** `/situation`. **Files** `situation-sheet-853-field.png`, `situation-sheet-390-field.png`,
`situation-sheet-853-blackout.png`, `situation-sheet-390-blackout.png`, and the vault pair.

Round 1's item 2 claimed "the set state is the loudest of the three". Measured live on all six
palettes, it is not. `screens/situation.css:12–16` gives `.state-set` a `--sunken` ground, weight 700
and its own colour, but the computed background of the pressed button equals `--panel` in every
theme (the `.btn` rule wins), so **the only difference between the chosen state and the two others is
text and border colour**. The ✓, ▲ and ✕ glyphs are option icons that sit on all three buttons at
once, so no symbol marks the selection: this is colour-only state on the one screen whose whole job
is state. In field it is inverted — `situation-sheet-853-field.png` shows the chosen "✕ Off" as a
light-red outline beside "✓ Working" and "▲ Patchy" in near-black `#1b1b1b`, so the chosen state is
the *quietest* of the three and the tick is the loudest thing in the group while the power is off.
Two contrast pairs also miss the 7:1 floor on the ground they actually sit on: vault `--danger` on
`--sunken` is 6.94:1 (the selected "Off"), field `--warn` on `--sunken` 6.82:1 (the selected
"Patchy").

Two more, both live: the "Since" select reads **"Just now" [selected]** on a condition whose heading
two lines above says **"off for 1 h"** — the control contradicts the fact; and for every condition
that has never been set, the meta line renders **"Set from at ."** — nine of the ten rows on a fresh
box.

**Fix** Mark the chosen state with a symbol and a fill, not a colour: put the state glyph only on the
chosen button (a bare word on the other two), give `.state-set` the `--sunken` fill it was meant to
have by raising its specificity above `.btn`, and add a 3 px inset bottom edge in the state's colour.
Verify by eye and by a computed-style assertion in all six palettes that `--sunken` is actually
applied. Re-tune vault `--danger` and field `--warn` against `--sunken`, not only against `--panel`.
Set the "Since" select from the stored `since` rather than defaulting to "Just now". Render the meta
line only when both `set_by` and a time exist, and say "Nobody has set this yet." when they do not.

### 4. Ending a drill takes 326 px out of a 480 px kiosk and pushes the rail off the screen

**Screen** `/`, `/situation`, everywhere after a drill ends. **Files** none — round 2's own
`now-drill-*` shots are of a running drill, never of the debrief. Reproduce by starting and ending a
drill at 853x480.

Measured live: the debrief is `.app-drill`, `position: static`, 853x**326**, a direct child of `.app`
rendered **before** the `<nav>`. It is not an overlay. It squashes the rail, the band and the whole
content column into the remaining 154 px, so the five destinations are pushed out of the rail
(measured: only the wordmark, AI and System remain) and the front door is a 60 px sliver. The person
who has just finished practising cannot get back to Now without dismissing a panel whose "Close"
button is the only control in reach.

Three faults travel with it. The debrief counts the household's real work as practice — "2 h in, 2 of
18 jobs ticked", where both ticks were made an hour before the drill started, on the real list; a
drill of "National grid collapse" showed the same four jobs, two already struck through, as the real
power cut. Round 2's `eventTitle` translation produces "Drill started: National grid collapse **in
the drill**", and lists real condition changes ("Water supply working on the box") under a heading
that reads "What happened in the drill". And the whole thing is `role="status"` with a list and a
button inside it: an aria-live region containing controls, which focus is never moved to.

**Fix** Make the debrief the modal it behaves like: `position: fixed`, the existing `.modal-backdrop`
and `.modal` components, `role="dialog"` with `aria-modal`, focus moved to its heading on open and
returned to "End drill" on close, and a heading ("How the drill went") rather than a bold sentence.
Count only ticks whose timestamp falls inside the drill window and say so ("2 h of practice, 3 of 18
jobs ticked during it"); if none were ticked, say "Nothing was ticked during the drill." Filter the
log to drill events and drop the "in the drill" suffix once the list is titled as the drill's own.
While there: a drill left running has no expiry — the live box carried a "Drill started: Nuclear war"
from 03:13 that nobody ended — so end a drill automatically after its own window and say so.

### 5. Find answers "bleeding" with the side effects of warfarin, and repeats itself

**Screen** `/search`. **Files** `find-results-853-vault.png`, `find-results-390-vault.png`,
`find-empty-853-*.png`, and the field and blackout sets. Reproduce with the live API.

The one search a frightened household actually types is answered worst. Live, top hits:

- `bleeding` → "Side effects of warfarin – NHS", "Bleeding", "Bleeding", "Side effects of apixaban –
  NHS", "Vaginal bleeding", then the box's own **"Severe bleeding"** guide sixth.
- `power cut` → "Solar panels in a power cut" **three times** in the top four, then "Power cuts –
  Prepare", then "Selling, buying and carrying knives and weapons – GOV.UK" and "Dental drill".
- `water` → "Water Village, North West", "Water Industry Act 1991", "How and when to take memantine".
- `cpr` → the correct card, but "CPR, adult" appears twice in the top four.

So: the box's own guides and quick cards — the things it was built to deliver — rank below a
Kiwix mirror of the NHS medicines A-to-Z, and the same result is printed two and three times on one
screen. The source chips lie about the set too: the nine chips on `water` sum to 61 while the line
under them says "40 results." Result titles are the source name and the title concatenated with no
separator and no theming — "NHS Medicines A to Z (**Kiwix build**, December 2025) How and when to
take memantine - NHS", "Approved Document G … **ONLINE VERSION ONLINE VERSION**".

**Fix** Rank by tier before relevance: quick cards, then guides, then the box's own pages and modules,
then UK official, then the library. De-duplicate by target URL before rendering. Make the chip counts
count the same set as the results line, or drop the counts. Render a result as source badge +
title on two lines rather than one concatenated string, strip the trailing "- NHS" and the doubled
"ONLINE VERSION", and take "Kiwix build" out of the source name (`api/words.ts` already owns this
translation). Add a spec asserting that `cpr`, `bleeding`, `burns`, `choking` and `power cut` each
put a card or a guide first.

### 6. The front door opens on jobs that are already done

**Screen** `/`. **Files** `now-power-off-853-vault.png`, `now-power-off-390-*.png`,
`now-power-off-dim-853-*.png`, `now-drill-853-*.png`.

Measured live on the kiosk: `.content` is 423 px tall and 2964 px long, and **the first job the
household still has to do sits 598 px down** — off the screen. "Right now" leads with two struck-
through, ticked jobs ("Fill the bath", "Keep the fridge and freezer doors shut", both "ticked 1 h
ago"), each with its full "why" paragraph and a "Read more" button, so the front door answers "what
do I do now" with two things that are finished and a scroll. Round 2's item 6 was right to keep a
ticked row in place on `/tasks` for the ten-second undo; carrying that behaviour onto Now is what
broke it. There is no scrollbar, fade or chevron anywhere in the 853 shots to say the content
continues.

**Fix** On Now only, a job that was already done when the screen loaded drops below the undone ones
(a row ticked *on this screen* stays put for its ten seconds, then moves on the next render, so undo
still works). Collapse the ones already done into a single row — "2 done — show them" — above "All of
them". Show the "why" paragraph only for the first undone job and put the rest behind the row (the
"why" is 3 lines × 4 jobs = most of the screen). Add a persistent scroll cue to `.content` on the
kiosk: a 24 px `--ground` fade at the bottom edge whenever `scrollTop + clientHeight < scrollHeight`.

### 7. A keyboard user takes seventeen stops to reach the first job, and no phone screen has search

**Screen** the shell, every screen. **Files** none — this is an accessibility flow. Reproduced with
Tab and `ariaSnapshot()` at 853x480 and 390x844.

Round 2 deferred this ("it wants its own pass"); this round weighs accessibility, so here it is.

- **No skip link, and the nav comes first.** On the kiosk, Tab 1 is the decorative wordmark link
  ("Operation SOS", measured 83x34, under the 48 px floor and going to the same place as Tab 2), then
  eight rail links, then the theme button, then three band links, then the search field and its
  button — **the first job's checkbox is Tab 17**, on every screen, every time. On a phone the bottom
  bar is drawn last and read first: five destinations before any content, first job at Tab 12.
- **No search on a phone.** `shell/Screen.tsx:47` renders the search field only when `wide` is true.
  The brief's constraint list says "search on every screen"; on a 390 px phone no screen carries one
  except Find and Guides' own filter.
- **Landmarks that name things the screen does not.** `<main>` is unnamed. A region called
  **"Briefing"** wraps four other regions and appears nowhere on the screen. A region called
  **"Read this"** contains an `h2` reading "Read". `<section aria-label>` and the visible heading
  disagree on both.
- **The theme control is shaped like a destination.** In the rail it is an icon and a word in the same
  row style as Now/Guides/Medical/Map/Find, and its visible word is the current theme
  ("Vault"/"Field"/"Blackout") — a noun, not a verb, reading as a sixth place to go. On a phone the
  same control says "Theme: Blackout". One control, two labels, neither a verb.
- **A wordless icon set on the map.** MapLibre's zoom, zoom-out and compass are icon-only on `/map`
  in every theme, and the compass's accessible name is an instruction ("Drag to rotate map, click to
  reset north").

**Fix** Add one skip link as the first focusable element in the shell — "Skip to what to do" —
visible on focus, targeting `#main`. Make `<main id="main" tabindex="-1" aria-label="{screen title}">`.
Drop the wordmark from the tab order (`tabindex="-1"`, it duplicates "Now") or make it 48 px and give
it the destination's name. Move the band after the screen head in the DOM on the kiosk so the search
field and the first job come before the three band links. Render the compact search on phones too, in
the screen head under the title, or state in the brief that Find is the search on a phone. Make every
`aria-label` on a `<section>` the text of its own `h2`, and delete the "Briefing" wrapper region.
Give the theme button a verb ("Change the theme — Blackout now") and a shape that is not a rail
destination. Replace MapLibre's controls with the app's own icon-and-word buttons, as the map toolbar
already does.

### 8. "Carry it to another box" describes a flow it does not offer, and fails in JSON

**Screen** `/situation`. **Files** `situation-carry-853-vault.png`, `situation-carry-390-*.png`,
`situation-drill-853-*.png` (the same textarea), and the field and blackout sets.

The panel says the box "turns the situation into a set of codes to **photograph** in order, and reads
the same set back in on the other side", and the code strip says "**Scan** them in order; the other
box asks for the next one". There is nothing on the receiving side that scans or photographs
anything: the only import is a textarea labelled **"Paste the JSON, or the text of each code in
order"** whose placeholder is `{"i":0,"n":2,"d":"…"}`. To carry a situation between two boxes with no
network, a household must transcribe three QR codes into JSON by hand.

When it goes wrong it goes wrong in developer English. Typing anything invalid and pressing "Bring it
in" produces **`a scanned chunk is not a QR chunk: expected {"i", "n", "d"}`** — and renders it above
the code strip, roughly 500 px from the button that caused it, so on a 480 px kiosk the person who
pressed the button never sees the error. "Copy as text instead" has no antecedent (the button above
it is "Make the codes again"), and "Bring it in" wears a "+" icon.

**Fix** Either build the scan — a "Scan a code" button that opens the device camera on a phone and
feeds each chunk to the same parser, with "Code 2 of 3 read" as it goes — or change the words so they
describe the paste: "Type or paste each code's text in order. The box tells you when it has them
all." Put the error inline, immediately under "Bring it in", in household words: "That is not one of
this box's codes. Type the line printed under the code, starting with `{`." Replace the JSON
placeholder with the first few characters of a real code. Rename "Copy as text instead" to "Copy the
codes as text".

### 9. On a phone the map panel's pinned action row covers the answer it was opened for

**Screen** `/map`. **Files** `map-nearby-390-*.png`, `map-home-390-*.png`, `map-nearby-853-*.png`,
`map-home-853-*.png`, `map-share-*.png`.

Round 2 turned the panels into a 55 % bottom sheet with a pinned head and pinned actions, which fixed
the map being covered and created a new fault: measured live at 390x844, the Nearby sheet is 282 px
tall with a **146 px** scrolling body holding **1861 px** of content, and the pinned "Search from this
centre" row sits over the top of the first result. `map-nearby-390-vault.png` shows the heading, the
caveat paragraph, "Emergency department", and then the nearest hospital's name and distance behind
the action bar. On the kiosk the same panel gives 162 px of body to 2036 px. The nearest hospital —
the single fact the panel exists to deliver — is never the first thing visible on either width.

Home has the matching fault: the panel shows "Home **SU 4015 1465**" and, four lines down, "Set as
home will use the centre of the map, **NY 0295 1266**" — two grid references, no label saying which is
your home and which is the map, and on 390 the second one is clipped after "NY". The share panel
gives two notations for one place (footer "Centre: NY 0295 1266", link `lat=54.5&lon=-3.5`) and clips
the QR code's bottom edge in all six files, which makes it unscannable. And `shell.css:176` hard-codes
`background: #fff` on the QR quiet zone, so blackout gets a large pure-white block.

**Fix** Lead each panel with its answer above everything else: Nearby renders the single nearest
result of the chosen kind at `--t-lead` in the pinned head, with the list below it and the caveat
paragraph at the bottom, not the top. Raise the phone sheet to 70 % when its content exceeds the
body, or make the sheet drag-expandable. Label the two grid references ("Your home: SU 4015 1465" /
"The map is on: NY 0295 1266") and let the map centre line wrap. Give the share panel one notation —
the grid reference — with the link as a link. Give the QR a `--panel`-coloured quiet zone with a
white-on-request "Make it brighter to scan" button, and size it to the panel so it is never clipped.

### 10. One 2.24 MB chunk on the front door, and the kiosk's small print never reaches 18 px

**Screen** every screen, on the Pi 5. **Files** `now-power-off-853-field.png`, `tasks-853-*.png`,
`board-853-*.png`, `library-853-*.png`, `calculators-853-*.png`. Measured from `pnpm build` and from
Chromium at 6x CPU throttle.

`pnpm build` emits **one** JavaScript chunk:

```
dist/assets/index-qzbqGAXZ.css    112.90 kB │ gzip:  19.52 kB
dist/assets/index-DBkUBADL.js   2,241.68 kB │ gzip: 661.43 kB
(!) Some chunks are larger than 500 kB after minification.
```

There is not a single `import()` or `React.lazy` in `src/`. `maplibre-gl`, `pdfjs-dist` and
`simple-keyboard` are all in that chunk, so a kiosk booting to Now parses MapLibre and the PDF viewer
before it paints, for two routes out of twenty-five. Measured at 6x throttle: first contentful paint
1028 ms, the `h1` at 1405 ms. In the box's favour, no long task over 50 ms was recorded in 65 s of
idle on Now or 40 s on `/map`, so the 30 s `SituationProvider` poll is not currently janking — but
it does `setView(v)` unconditionally on every poll, replacing the context object and re-rendering
every consumer whether or not the JSON changed, which is a hitch waiting for a slower box.

Typography on the kiosk misses its own floor. `tokens.css:37` is `:root.kiosk { --t-body: 18px }` and
leaves `--t-meta` at 16 px, so on the 853 kiosk every `.btn-small` ("Back", "Read more", "Close",
all seven map tools), every `.chip`, every `.badge`, every `.task-why` explanation, every `.tile-sub`
and the whole rail footer render at 16 px — most of the small print on the device the 18 px rule was
written for.

**Fix** Split the bundle: `React.lazy` the `/map`, `/doc/:id` and `/read/:id` routes and load
`simple-keyboard` on the first `focusin` of a text field, with `manualChunks` for `maplibre-gl` and
`pdfjs-dist`; target under 250 kB gzipped for the first paint. In `SituationProvider.refresh`, keep
the previous object when the fetched view is deeply equal. Raise `:root.kiosk { --t-meta: 18px }` (or
17 px if the map toolbar will not take 18) and re-shoot the kiosk set. VT323 (18 kB) loads on every
vault screen for a wordmark and one clock — give it `unicode-range` or load it only on `/board`.

## Watch list

1. **A real document still shows the raw pdf.js toolbar.** Round 2's item 2 was verified only against
   `document-missing`, which never loads a PDF. Live at `/doc/ad-g?kiosk=1` the page throws an
   uncaught `InvalidPDFException`, the HEAD probe succeeds so `DocumentMissing` never renders, and the
   untouched vendor bar — light grey, twelve wordless icons, "0 of 0", "Automatic Zoom", a bright blue
   progress line — sits under the app's own three-row chrome. Two toolbars for one document, one of
   them the exact strip round 2 said it had removed. Also: the app's chrome takes 130 px of 480 in
   three rows, "of an unknown number" is not a household phrase, "Next" is enabled with nowhere to go,
   and the rail lights **Find** while a document is open.

2. **The keypads.** The kiosk numeric pad's fourth row (`. 0 -`) starts at y=457 and is sliced by the
   480 px edge (`childrens-doses-853-{vault,field,blackout}.png`): `KEYBOARD_HEIGHT = 224` against four
   59 px rows, so a parent cannot type **0** — no 10 months, no 20 kg, no decimal point — on the
   children's-doses screen, and a fixed panel cannot be scrolled to reach it. On a phone the letter
   keys are 34 px wide against the 48 px floor and the right column reads "dele", "ente", "shi"
   (`keyboard-390-*.png`, `keyboard-dim-390-*.png`).

3. **Blackout's torches, and the toast over the phone's nav.** `shell.css:176` hard-codes
   `background: #fff` on every QR quiet zone, so `connect-a-phone-*-blackout.png`,
   `situation-carry-*-blackout.png` and `map-share-*-blackout.png` each paint a large pure-white block
   on the theme that exists to protect dark adaptation; the filled `--signal` primary does the same at
   smaller scale in `library-*-blackout.png`. Separately, `.notices { bottom: calc(16px + var(--kb-height)) }`
   (`shell.css:164`) never allows for `--bar: 64px`, so the toast covers Guides, Medical and Map on a
   390 px phone (`notice-390-*.png`, `notice-dim-390-*.png`) and has no dismiss control.

4. **The symbol and shape vocabulary, deferred twice now.** ⚠ marks danger, the drill chip, the Timers
   tile, the engine-down line, the assistant's "AI can be wrong", the form hint "Choose a situation
   first", and an OpenStreetMap tagging note — seven jobs for the one alarm symbol. Alongside it:
   `999px` on `.chip`, `.badge`, `.cond-chip-compact` and the progress rules against a stated single
   6 px radius; four border weights (1 px panels, 2 px state buttons and checkboxes, 3 px accent
   edges, 6–8 px progress); and `--glow: 0 0 4px rgba(108,240,140,.3)` applied as a `text-shadow` in
   vault, in a system whose rule is "no shadows". Round 2 left this as "the round-3 item the round-1
   note already pointed at"; it is now the round-4 one.

5. **The box's own machinery on the front door.** Live on `/`, under "The box": "WiFi **SOS**",
   "http://10.42.0.1", "http://sos.box" (two bare URLs, no separator, no reason given for there being
   two), "External drive: 107.8 GB free" and **"CPU 45°C"** — the same class of string round 2's watch
   list flagged on `/system` and left there, now on the household's first screen. In the same column:
   "The box thinks" proposes "**Landline and 999 is** probably off" and "**Shops and cash is**
   probably off" (compound subjects with a singular verb), each with an "Accept" / "Not now" pair —
   eight buttons of data entry on the front door — and "Coming up" renders "**due** Fridge food unsafe
   in 2 h", which is not a sentence in any register.

## Applied

Every screenshot below is `docs/superpowers/critique/round-2/<name>` before and
`docs/superpowers/critique/round-3/<name>` after, at the same width and in the same theme. The whole
inventory was re-shot with `node scripts/screenshots.mjs round-3` — 354 files, against round 2's
336 — and it now carries the state round 3 found in none of them: **print**, as `print-quick-card-*`,
`print-scenario-*` and `print-situation-sheet-*` at both widths in all three themes, taken with
`emulateMedia({media:'print'})` and dim on, which is the exact state a household prints from in a
night-time power cut.

### 1. The quick card

The card is now a screen of its own shape (`screens/Card.tsx`): the title as a real `h1` at
`--t-title` (a `.card` override beats the kiosk's own "short screens shrink the title" rule), one
999 line, a count line, and the steps in a scrolling frame that fills what is left.

- **The 999 line is one line.** `Emergency999` takes a `compact` prop for this screen only: the same
  words at the body size with 4 px of padding instead of a panel, which gives the steps back 50–90 px
  of a 480 px screen. Everywhere else the panel is unchanged.
- **The card says how long it is and where it goes.** "4 steps" is counted from the card's own HTML
  (`countSteps`), and while there is more below the frame it carries a 48 px "More below ▾" button
  beside the count and a fade along the bottom edge (`.card-scroll-more`). Round 2's card ended
  mid-glyph with nothing to say it continued.
- **The steps fit.** A step over 45 characters is a sentence, not an instruction, and drops from
  `--t-display` to `--t-lead` (`card-step-long`); then the screen measures the third step and gives
  up a whole size at a time — display, lead, body, and no lower — until steps 1 to 3 are on the first
  screen. Measured at 390: the compression rate now ends 769 px down an 844 px screen with the phones
  on **and** with them off, where before it was never on the screen at all.
- **The calls-off card no longer contradicts the banner.** The box already resolves `[[call 999]]`
  against the situation before it renders a card, so the live card was never the fault: the *fixture*
  served one card in both modes, which is what the round-2 screenshots photographed. The fixture now
  serves the resolved pair (`tests/fixtures/api.ts` `cardsNoPhones`, chosen in `e2e/fixtures/routes.ts`
  by the same `modes.calls` the app reads), so "Call 999 and put it on speaker" is replaced by "Send
  someone to a landline, a neighbour or a payphone: 999 will not connect from here" — and the
  screenshots now show what the box actually does.
- **Content.** Five cards had a *later* step that told a reader to ring with no alternative:
  `asthma-attack` (4), `choking` (7), `cpr-child` (6), `low-blood-sugar` (7), `recovery-position` (7).
  Each is now `{{#if phones}}[[call 999]]{{else}}send someone to a landline, a neighbour or a
  payphone: 999 will not connect from here{{/if}}`. `sos validate-playbooks --all-scenarios` passes
  (83 documents) and `api/tests/test_playbooks_content.py` + `test_content.py` pass (228).
  **What could not be done, and why:** the same branch cannot go in steps 1 to 3 of any card —
  `test_card_structure_and_screen_rule` caps those three steps at 70 characters *of Markdown source*,
  and a two-branch step is 180 to 240. See "For the coordinator" below.

Before `round-2/quick-card-{853,390}-{vault,field,blackout}.png`,
`round-2/quick-card-phones-off-*.png`, `round-2/quick-card-dim-*.png` · after the same names under
`round-3/`, plus the new `round-3/print-quick-card-*`.
Specs: `e2e/card.spec.ts` — "the card says how many steps there are, and the rate is on the screen at
390" and "with the phones down the card does not tell you to ring, and says it once".

### 2. Print

`tokens.css` now carries the print palette in a `@media print` block written as
`:root, :root[data-theme], :root[data-dim], :root[data-theme][data-dim],
:root[data-theme][data-dim="on"]` and placed after the dim palettes, so print wins from every theme
whether dim is on or not. Measured in print media on all six palettes: ground `#f3efe4`, panel
`#ffffff`, ink `#1b1b1b`. The blackout-with-dim CPR card that printed three solid black A4 pages
prints paper.

`type.css` prints the body at **12 pt** (16.00 px measured, against 14.67 px before), `h1` 20 pt,
`h2` 15 pt, `h3` 13 pt. `.tabs` is `display: none` in print, and `Scenario` now treats
`matchMedia('print')` as printing in its own right — a PDF export or a browser's own print command
fires no `beforeprint` anybody can hear — so every phase renders and every module accordion is open
on paper, instead of one tab plus a row of dead tab buttons.

Before: none — print was in none of round 2's 336 files · after `round-3/print-quick-card-*`,
`round-3/print-scenario-*`, `round-3/print-situation-sheet-*` (853 and 390, three themes, dim on).
Spec: `e2e/print.spec.ts` — six palettes × five printable routes assert the paper ground, the ink,
and a body of at least 16 px; plus "a printed scenario is the whole guide, with no tab strip and
every module open".

### 3. The situation sheet

- `.state-btn.state-set` (two classes) now outranks `.btn`, so the chosen state really is filled with
  `--sunken` — measured in all six palettes, where before it computed to `--panel` in every one — and
  carries a 3 px inset bottom edge in its own colour (`box-shadow: inset 0 -3px 0`, no offset, no
  blur: still no shadows in the system).
- The state glyph is on the **chosen** button only; the other two carry the bare word. One glyph per
  group, asserted.
- The "Since" picker opens on the time the box has stored (`sinceChoiceFor` maps a stored instant
  back onto the option that would have written it, within five minutes, and to "custom" when nothing
  fits), so a row headed "off for 1 h" no longer reads "Just now".
- The meta line renders only when both `set_by` and a time exist, and says "Nobody has set this yet."
  when they do not — nine of ten rows on a fresh box used to read "Set from at .".
- **Contrast.** The chosen button now sits on `--sunken`, so the tokens were re-tuned against it:
  vault `--danger` `#ff8a76` → `#ff9d8b` (6.94:1 → 7.92:1) and field `--warn` `#6b4400` → `#603c00`
  (6.82:1 → 7.80:1); field `--danger` `#94170f` was exactly 7.00:1 on `--sunken` and went to
  `#8a1209` (7.70:1) for headroom. `tests/theme/contrast.test.ts` now measures every readable token
  against `--sunken` as well as `--ground` and `--panel`: 138 cases, all passing.

Before `round-2/situation-sheet-{853,390}-{vault,field,blackout}.png` · after the same names.
Specs: `e2e/situation.spec.ts` — "the chosen state is filled and marked, not merely coloured, in all
six palettes", "the since picker opens on the time the box has stored"; `tests/situation/since.test.ts`,
`tests/situation/stateFill.test.ts`, `tests/screens/situation-sheet.test.tsx`.

### 4. The drill debrief

It is the modal it behaved like: `role="dialog"`, `aria-modal`, the app's own `.modal-backdrop` and
`.modal`, a heading ("How the drill went") that takes focus when it opens, and focus returned to the
screen on close — the "End drill" button it came from goes with the drill, so there is nothing else
to return it to. It no longer squashes the rail: measured at 853x480 the five destinations stay in
the rail and the content column keeps its height.

It also counts the drill and not the household's morning. `drillStartedAt` reads the wall-clock moment
somebody pressed the button out of the log's own "Drill started" line — `scenario.started_at` may be
backdated two days so the guidance shows the right phase — and only ticks and events inside that
window count. The log is filtered to events the engine tagged `(drill)` (plus the drill's own start),
and the tag is stripped for display, so "Drill started: National grid collapse **in the drill**" and
a real "Water supply working on the box" under "What happened in the drill" are both gone. With
nothing ticked it says "Nothing was ticked during the drill."

Before: none — round 2 photographed running drills, never the debrief · after: covered by
`e2e/board.spec.ts` and `e2e/situation.spec.ts` rather than a new inventory entry (a modal over a
screen the inventory already carries). Specs: `tests/screens/drill.test.tsx` (the window, the tag,
the dialog), `e2e/board.spec.ts`, `e2e/situation.spec.ts`.
**Left:** a drill still has no expiry. See "For the coordinator".

### 5. Find

The screen no longer renders the engine's one ranked list in the order it arrives. `api/results.ts`
is the new seam:

- **De-duplicated by target URL** before anything is rendered — "Solar panels in a power cut" three
  times in the top four was the same page found in three books.
- **Grouped by source, the box's own first.** Guides, quick cards, modules and pages are one group,
  "From this box", above every library source; then places, the box's documents, NHS and medical, then
  the rest. Each group is a named region with its own heading, so a household's own guidance is the
  first thing under the count whatever the engine scored it.
- **The chips count the rows underneath them.** They are computed from the de-duplicated result set,
  so the nine chips that summed to 61 over a line reading "40 results" now sum to the number on the
  line. A chip toggles its whole group's sources.
- **A result is a source badge on one line and a title on the next** (`ResultList`), with the
  library's cataloguing stripped: "(Kiwix build, December 2025)" off the badge, a trailing "– NHS"
  and a doubled "ONLINE VERSION" off the title.

Before `round-2/find-results-{853,390}-{vault,field,blackout}.png` · after the same names.
Specs: `tests/screens/search.test.tsx`, `tests/screens/find.test.tsx`, `e2e/search-reader.spec.ts`.
**Ranking itself is backend** — see "For the coordinator": the frontend can only put the groups in
order, and it does.

### 6. The front door

- A job that was already done when Now opened sits **below** the ones that are not, behind one row:
  "2 done — show them". A row ticked on this screen stays exactly where it was ticked for its ten
  seconds — the same ten seconds the Undo is offered for — and then joins them (`useSunkTasks`).
- The "why" paragraph is shown for the **first** undone job only; the rest carry "Read more", and
  `/tasks` still shows every one. Four "why" paragraphs were most of a 423 px screen.
- **A scroll cue.** `useScrollCue` watches the content column and the shell paints a 24 px
  `--ground` fade along its bottom edge whenever there is more below it, on every screen. The kiosk
  has no scrollbar and no bounce: 423 px of a 2,964 px screen looked exactly like a screen that
  ended.
- While there: "Coming up" now reads "Fridge food unsafe ⚠ due in 2 h" rather than "due Fridge food
  unsafe in 2 h", and "The box thinks" reads "Landline and 999 — probably off" rather than "is
  probably off" (half the condition names are compound).

Before `round-2/now-power-off-{853,390}-*.png`, `round-2/now-power-off-dim-*.png` · after the same
names. Specs: `tests/screens/briefing.test.tsx`, `tests/screens/now.test.tsx`.

### 7. The keyboard, the phone's search, and the words landmarks use

- **A skip link** is the first focusable element in the shell on every screen: "Skip to what to do",
  off-screen until it takes focus, 48 px, targeting `#main`. `<main id="main" tabindex="-1">` is
  named after the screen it holds (the title travels up through `shell/screenTitle.ts`), so following
  the link lands focus on a landmark that announces "CPR (adult)", not "main".
- **The furniture is read last.** `<nav>` now comes after `<main>` in the DOM (the grid still draws
  it on the left, and the bar along the bottom), and the band is drawn above the content with
  `order: -1` while sitting after it in the DOM. The decorative wordmark is `tabindex="-1"` and
  `aria-hidden` — it went to the same place as the "Now" tab 34 px below it. Measured: from the skip
  link, the first job's tick box is inside 8 tab stops at both widths, against 17.
- **Search is on every phone screen.** The compact field is rendered in the screen head at every
  width; the screens that turn it off (a quick card, the map, the sheet, a guide) carry a 48 px
  "Find" control in the same place instead. Before this round a 390 px phone had neither, on
  twenty-three screens.
- **Landmarks say what the screen says.** The "Briefing" region — a region wrapping four regions,
  named after a word that is nowhere on the screen — is gone. Every remaining `<section aria-label>`
  is now the text of its own `h2`: "Read this"→"Read", "Conditions"→"What is working", "Situation
  clock"→"Clock", "Drill"→"Practise a drill", "Detected"→"Detected by the box", "Carry the
  situation"→"Carry it to another box", "The assistant"→"Ask the assistant", "The library"→"Browse
  the library", "The household plan"→"The plan", and Readiness's "Situation"→"How ready you are".
- **The theme control is a control.** It reads "Change theme" in a bordered row that is not the
  rail's destination shape, with the accessible name "Change the theme. Vault now; next is Field" — a
  verb, one label, and not a sixth place to go. The current theme rides under the verb where there is
  a row to put it (the phone's screen head) and lives in the accessible name on the rail, where a
  third line cost Find its word.
- **The map's own controls have words.** MapLibre's `NavigationControl` is not added at all; the map
  draws Zoom in, Zoom out and Face north as the app's own icon-and-word buttons over the map — a
  column in the top-right corner on the kiosk, one row along the top on a phone, where three stacked
  buttons would have taken half of the band of map above the sheet. The scale bar, which has no
  buttons and no words to miss, stays.

Before: none — this is a flow · after: the same inventory shots, plus `e2e/access.spec.ts` ("the
first tab stop is a way past the furniture, on every screen", "the wordmark is not a second Now, and
the navigation is read after the content", "every phone screen carries a search, and the theme
control is not a destination", "a section is named by its own heading, and the map has words on its
controls").

### 8. Carrying a situation to another box

The words describe the paste, because the paste is what the box offers: "The box turns this situation
into a set of codes. On the other box, type or paste each code's text in order, and it says when it
has them all." No "photograph", no "scan". The code strip says "Code 1 of 3. Work through them in
order; the other box says how many it has."

The error is inline, immediately under "Bring it in" (it used to render ~500 px above it, off a
480 px screen), and in household words: "That is not one of this box's codes. Type the line printed
under the code, starting with `{`", with the box's own sentence kept as a muted detail after it.
Missing chunks and two different sets have their own sentences. The placeholder is the first
characters of a real code; the field is labelled "The text of each code, one per line, in order";
"Copy as text instead" is now "Copy the codes as text"; the "+" is off "Bring it in"; and the panel
counts as you type ("Code 2 of 3 read. Type the next one on a new line.").

Before `round-2/situation-carry-{853,390}-*.png` · after the same names. Specs:
`e2e/situation.spec.ts` — "carrying a situation describes the paste, and says its trouble under the
button"; `tests/screens/carry.test.tsx`.

### 9. The map panels

`MapPanel` gained a third pinned region between the head and the scrolling body, and the panels lead
with their answers:

- **Nearby** pins a kind chooser and the nearest place of that kind — its name at `--t-lead`, its
  distance, bearing and rough walking time under it — above the list, with the "as the crow flies"
  caveat moved to the **bottom** of the body. The pinned action row can no longer cover the first
  result. A kind the box has nothing for says so in the head instead of leaving it blank.
- **The phone sheet grows** from 55 % to 70 % of the map as soon as its body has more in it than it
  can show, and keeps it while that panel is open (it never shrinks back under a reader). At 390x844
  the scrolling body goes from 146 px to about 210 px, and the map is still live above it.
- **Home** labels both grid references — "Your home: SU 4015 1465" and "The map is on: NY 0295 1266"
  — pins both, and lets them wrap rather than clipping after "NY".
- **Share** gives one notation (the grid reference), the address as a real link rather than a
  read-only textarea, and a QR sized from the measured panel so it is never clipped.
- **The QR's quiet zone** is the panel's own colour on a dark theme, so blackout no longer paints a
  220 px sheet of white paper; a 48 px "Make it brighter to scan" hands the full white border over
  when a camera refuses the dim one. `shell.css`'s hard-coded `background: #fff` on `.qr img` is
  gone.

Before `round-2/map-nearby-{853,390}-*.png`, `round-2/map-home-*.png`, `round-2/map-share-*.png`,
`round-2/connect-a-phone-*-blackout.png`, `round-2/situation-carry-*-blackout.png` · after the same
names. Specs: `e2e/map-home.spec.ts`, `e2e/map.spec.ts`, `tests/map/panel.test.tsx`,
`tests/map/nearby.test.ts`.

### 10. The front door's own weight, and the kiosk's small print

**Before** — one chunk, parsed before anything painted, on every screen:

```
dist/assets/index-qzbqGAXZ.css    112.90 kB │ gzip:  19.52 kB
dist/assets/index-DBkUBADL.js   2,241.68 kB │ gzip: 661.43 kB
```

**After** — what the front door loads is the first three lines; everything below is fetched by the
screen that needs it:

```
front door   dist/assets/index-B2d8Y5Ui.js      156.71 kB │ gzip:  47.63 kB
front door   dist/assets/react-D-ubgs9F.js      287.32 kB │ gzip:  92.10 kB
front door   dist/assets/index-CJMhNZOG.css      37.74 kB │ gzip:   8.24 kB
                                       total    481.77 kB │ gzip: 147.97 kB

/map         dist/assets/maplibre-CTmHzN_F.js 1,073.71 kB │ gzip: 292.38 kB
/map         dist/assets/maplibre-DNVN2dqC.css   69.92 kB │ gzip:  10.05 kB
/map         dist/assets/Map-C28QQA1X.js         42.54 kB │ gzip:  14.35 kB
/map         dist/assets/Map-o4i-qxXq.css         6.10 kB │ gzip:   1.64 kB
/map         dist/assets/grid-Cr-rPMwp.js         2.96 kB │ gzip:   1.39 kB
/map         dist/assets/PlaceSearch-JplAHmzg.js  1.22 kB │ gzip:   0.66 kB
/read, /doc  dist/assets/epub-j66FGZCx.js       351.45 kB │ gzip: 108.50 kB
/read, /doc  dist/assets/Doc-C2C9G7hi.js         10.31 kB │ gzip:   3.89 kB
/read        dist/assets/Reader-BjkdpAo0.js       3.91 kB │ gzip:   1.70 kB
first field  dist/assets/keyboard-BcX64-1B.js   107.49 kB │ gzip:  35.04 kB
first field  dist/assets/keyboard-DJV78Rqi.css    3.22 kB │ gzip:   1.06 kB
first field  dist/assets/Keyboard-DoBJkpUY.js     2.98 kB │ gzip:   1.48 kB
/plan, /sun  dist/assets/grid-C5TDArtG.js       131.58 kB │ gzip:  43.71 kB
/plan        dist/assets/Plan-CgHK-N9T.js        20.31 kB │ gzip:   4.91 kB
/tools/sun   dist/assets/SunMoon-CC1xVSxm.js      3.94 kB │ gzip:   1.62 kB
first code   dist/assets/qr-bYEHtTaU.js          25.78 kB │ gzip:  10.13 kB
/ai          dist/assets/Ai-COhFjkcI.js           6.15 kB │ gzip:   2.42 kB
```

**The front door parses 444 kB of JavaScript instead of 2,242 kB — 80 % less — and 140 kB gzipped
instead of 661 kB, 79 % less.** With the stylesheet (37.71 kB, 8.23 gzipped, against 112.90 and
19.52) the whole first paint is 482 kB, **148 kB over the wire**: inside the 250 kB the item asked
for, with the map, the reader, the keyboard, the encoder and the projection library all still on the
box and all still one tap away.

How: `React.lazy` plus `import()` for `/map`, `/doc/:id`, `/read/:id/*`, `/ai`, `/plan` and
`/tools/sun`, each behind a plain loading screen that already knows its own title (`Later` in
`router.tsx`); `kiosk/KeyboardMount.tsx` fetches `simple-keyboard` on the first field anybody focuses
(the pad's own logic split into `kiosk/editable.ts`, which has no vendor code in it, so the reader and
the shell can ask what a text field is without loading a keyboard); `components/QrCode.tsx` fetches
the encoder when the first code is drawn, through one shared promise. `manualChunks` names
`maplibre-gl`/`pmtiles`, `epubjs`, `simple-keyboard`, `proj4`, `qrcode` and React — matched on
`/node_modules/<name>/` rather than anywhere in the path, because pnpm keeps a package's own
dependencies under `.pnpm/<name>@<version>/node_modules/` and a looser test put epubjs's dependencies
in the reader chunk, which then arrived on the front door.

`SituationProvider.refresh` keeps the previous View object when the new one says the same thing
(`sameView`, which compares everything but the engine's own `meta.now` stamp), so a box in peacetime
polls every 30 s and re-renders nobody.

**Kiosk type**: `:root.kiosk` now raises `--t-meta` to 18 px as well as `--t-body`. That is every
`.btn-small` (Back, Read more, Close, all seven map tools), every chip, every badge, every task
"why", every tile's second line and the whole rail footer — most of the small print on the device the
18 px rule was written for.

**VT323** is now declared with a `unicode-range` of exactly the glyphs it draws (the wordmark's S and
O, the board clock's digits and colon), so it is never fetched for a stray character elsewhere. It is
still fetched on a vault screen with a rail, because that is where the wordmark is; it is 18 kB from
the local disk with `font-display: swap`, so it holds no paint. Moving the wordmark off the display
face is a design change the plan does not authorise, and is left.

Before `round-2/now-power-off-853-field.png`, `round-2/tasks-853-*.png`, `round-2/board-853-*.png`,
`round-2/library-853-*.png`, `round-2/calculators-853-*.png` · after the same names, re-shot at
18 px meta.

## The watch list

**Taken:**

- **2, the kiosk number pad.** `.hg-layout-numeric .hg-button` kept the vendor's 60 px height, so four
  rows plus their margins did not fit the 224 px panel and the fourth row (`. 0 -`) was sliced by the
  480 px edge: a parent could not type **0**. Every key is now the 48 px touch target, four rows fit
  with room to spare, and the whole `.sos-kb` block is written from `.kb-panel` down — now that the
  pad is fetched on demand its vendor stylesheet arrives *after* the app's, and a rule of equal weight
  would have won. `e2e/keypad.spec.ts` passes on the children's-doses screen.
- **3, the torches and the toast.** `shell.css`'s hard-coded `background: #fff` on every QR quiet
  zone is gone (see item 9). `.notices` now clears the bottom bar as well as the keyboard
  (`bottom: calc(16px + var(--kb-height) + var(--bar-clearance))`), so a toast no longer covers
  Guides, Medical and Map on a 390 px phone — and every notice carries a 48 px dismiss control, which
  it never had — and the toast is a toast's width again rather than shrinking around the new button.
- **5, the box's own machinery on the front door.** "The box" panel now says one thing about the
  machine — "Phones join it over its own WiFi, **SOS**" — and then only what is actually wrong (the
  library drive missing, the chip too hot to run the assistant, each in a sentence). The IP, the
  second bare URL, the free space and "CPU 45°C" live on System, one tap away, and inside the Connect
  a phone panel where a second phone needs them. "Connect a phone" no longer disappears when the
  mobile network goes down — joining the box's own WiFi has nothing to do with the mobile network,
  and the address went with the button. The two grammar faults are fixed under item 6.

**Left, with reasons:**

- **1, the raw pdf.js toolbar on a real document.** Round 2's chrome is in place and the vendor bar is
  hidden by `pdfViewerCss`, but the reported fault is a real PDF that throws `InvalidPDFException`
  behind a HEAD probe that succeeds — which needs a real, broken PDF on a live box to reproduce, and
  the fixture serves none. It also wants the app's three rows of chrome cut down, "of an unknown
  number" rewritten, "Next" disabled at the end, and the rail lit for the destination the document
  belongs to rather than Find. That is a screen's worth of work on the one screen this round did not
  otherwise touch, and it is the first thing for round 4.
- **2, the phone's letter keys.** The kiosk pad's letter row is 34 px wide at 390, against the 48 px
  floor, because eleven keys do not fit 390 px at 48 px each. It only ever appears at that width when
  kiosk mode is forced on a phone-sized window (the screenshot set does exactly that); a real phone
  uses its own keyboard. Fixing it properly means a different layout under 700 px — a round-4 item,
  not a token change.
- **4, the symbol and shape vocabulary.** ⚠ still does seven jobs, `999px` pills still sit beside the
  stated single 6 px radius, there are still four border weights, and vault still puts `--glow` on
  headings as a `text-shadow` in a system whose rule is "no shadows". This is one pass over every
  component with a written vocabulary at the end of it, and doing it inside a round that also moved
  the shell, the card, the map panels and the build would have made both unreviewable. It is the
  round-4 item it was already promised to be.
- **5, the eight buttons of data entry.** "The box thinks" still offers Accept / Not now per guess, up
  to eight controls on the front door. They are the engine asking a question only the household can
  answer, and the alternative — the box deciding for itself — is the fault the panel exists to
  prevent. Left deliberately.

## For the coordinator: what only the backend can fix

1. **`api/sos/search.py:205–211` counts the chips before it truncates and before it filters.**
   `groups` is built from the full result list, then `results` is cut to `limit`; the chips therefore
   describe a set the screen never shows (nine chips summing to 61 over "40 results."). The frontend
   now counts its own rendered rows, so the screen agrees with itself, but `/api/search`'s `groups`
   still lies to any other consumer. Count after the truncation, or return the pre-truncation total.
2. **Nothing de-duplicates by URL.** The same page found in several ZIM classes is several results
   ("Solar panels in a power cut" three times in the top four). The frontend de-duplicates what it
   renders; the API still spends its `limit` on duplicates, so a de-duplicated 40 can be 25 distinct
   answers. De-duplicate by `url`, keeping the highest score, before the `limit`.
3. **The exact-title jump is per source, not global** (`search.py:194–199`): each source's own top
   score is raised, so a Kiwix page titled exactly "Bleeding" is promoted inside its own source and
   lands beside the box's Severe bleeding card. With `PLAYBOOK_WEIGHT` at 1.6, any library book with
   a `search_weight` at or above 1.6 outranks the box's own guides on relevance alone. The screen now
   groups the box's own answers first whatever the score, so a household is answered correctly — but
   the ranked list `/api/search` returns (and the assistant retrieves over) is still wrong for
   `bleeding`, `power cut` and `water`. Ranking by tier before relevance is section 8's own rule and
   it is not implemented.
4. **A ZIM result's badge is the library item's full title**, build stamp and all: "NHS Medicines A to
   Z (Kiwix build, December 2025)". The frontend strips the parenthetical; the string itself comes
   from `library_items.title` in the manifest and would be better fixed there.
5. **`api/tests/test_playbooks_content.py::test_card_structure_and_screen_rule` caps the first three
   steps of a quick card at 70 characters of Markdown source.** That makes a `{{#if phones}} … {{else}}
   … {{/if}}` branch impossible in exactly the steps that most need one — step 1 of CPR, step 1 of
   severe bleeding, step 1 of childbirth, step 3 of stroke. Worse, the rule already fails on its own
   terms: with the phones down the API expands `[[call 999]]` into "999 will not connect while the
   phones are down: get help without phones", so those three steps render 65 characters longer than
   the rule allows and nothing measures it. The rule should measure the *rendered* step, in both
   phone states, and then the calls-off variants can be written where they belong.
6. **A drill has no expiry.** The live box carried "Drill started: Nuclear war" from 03:13 that
   nobody ended. The debrief now counts only what happened inside the drill's own window, but ending
   one belongs to the engine: a browser that happens to have the page open is not a timer, and two
   phones would race to end it.
