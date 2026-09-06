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
