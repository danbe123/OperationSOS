# Round 4: critique

Reviewed against `docs/superpowers/specs/2026-09-06-interface-redesign.md` (sections 5 and 6), the
round-0 plan, the round-1, round-2 and round-3 critiques with their Applied sections, the 354
screenshots in `docs/superpowers/critique/round-3/` (59 entries at 853x480 and 390, three themes,
dim and print variants), and — this round's weight — the **real box** at `http://127.0.0.1:8080`
driven with Playwright: the real library (Where There Is No Doctor, FM 21-76, the NHS and WikiMed
ZIMs), real scenarios (National grid collapse, Severe storms and flooding, Lethal pandemic), real
quick cards (CPR adult, Severe bleeding, Choking, Hypothermia), real pages (water disinfection,
getting help without phones, the field-craft set), real searches (`bleeding`, `power cut`,
`boil water`, `adder bite`, `insulin`), a real Wikipedia article in the reader, a real 26 MB PDF in
the document viewer, the assistant with a real question, the map and Nearby around Southampton with
the health overlay, the on-screen keyboard and the number pad, a phone at 360, a landscape phone at
844x390, print media with PDF exports, and the whole situation flow — power off since four hours
ago, mobile and landline off, Now, a scenario started and ended, a card, `/board` — with every
condition put back to working and the scenario ended afterwards.

## Verdict

Round 3's ten mostly landed where they were measured: print is paper in all six palettes, the number
pad fits its four rows, the skip link and the landscape bar work, and the front door no longer opens
on finished jobs. What the round could not see is what this one was asked to look at — with the real
library and three conditions off, the redesigned chrome eats the whole kiosk (the first job on Now is
at y=432 of 480, step 1 of the CPR card at y=444, and a guide's tab strip ends at y=462 with no
guidance under it), every PDF in the library fails to open behind a raw pdf.js toolbar with no error
because the viewer is handed the app's own route instead of the file, and every search snippet in the
box prints its highlight markup as literal `<b>` tags. Beneath that, the quick card's steps are 18 px
body type on every real card in all three themes — the round-1 fault restored by round 3's own
shrink ladder, because the fixture had four short steps and CPR has eight long ones.

## The ten

### 1. With three conditions off, no content is above the fold on Now, a quick card or a guide

**Screens** `/`, `/medical/card/:slug`, `/s/:slug`, at 853x480 and 360x740. **Live state** power off
5 h, mobile off, landline off; kiosk mode. Screenshots of the same shape:
`now-power-off-853-*.png`, `now-phones-down-853-*.png`, `now-drill-390-*.png`.

Measured on the real box at 853x480 with three conditions off:

| screen | chrome | first content |
|---|---|---|
| `/` | band 113 px (chips wrap to two rows) + head 58 + 999 panel 88 + "Read the briefing aloud" 60 | first task's tick box top = **432** of 480 |
| `/medical/card/cpr-adult` | band 113 + head 58 + 999 panel + "8 steps / More below" + "When to use" | step 1 top = **444** of 480 |
| `/s/grid-collapse` | band 113 + head 58 + "This has started" 56 + 999 panel 96 + summary + tabs | tab strip bottom = **462**, zero guidance |

At 360x740 the band is **169 px** (three chips over two rows, then a third row for "3 to do" and
"Situation") and the first tick is at **y=646 of 740** — 87 % down the phone. The band is the one
element the plan calls memorable and it is the one that grows without limit: a real grid collapse
turns six or seven conditions off, not three.

**Fix** Cap the band at one row at every width: the scenario and its clock, then a single collapsed
condition chip — "⚡ 3 things off · 3 to do ›" — that opens the sheet, with the individual chips only
on `/situation` and `/board` where there is room for them. Use `Emergency999`'s `compact` variant
(one `--t-lead` line, already built for the card) on every screen, not the 88–96 px panel. Move "Read
the briefing aloud" into the screen head beside Search. Add an e2e assertion that with four
conditions off, at both widths and in all three themes, the first task row on `/`, the first step of
every quick card and the first paragraph of a guide have their top above 0.6 × viewport height.

### 2. Every PDF in the library fails to open, behind the raw pdf.js toolbar, with no message

**Screen** `/doc/:id`. **Live** `/doc/where-there-is-no-doctor`, `/doc/where-there-is-no-doctor#page=350`,
`/doc/fm-21-76-survival#page=52` — all three identical. Screenshots: `document-missing-*.png` is the
only doc entry in the set and it never loads a file.

`Doc.tsx:273` renders `<PdfFrame url={item.url} …>`, and `item.url` from `/api/library/<id>` is the
**app route** `/doc/where-there-is-no-doctor`, not the file. `pdfViewerUrl` puts that in pdf.js's
`file=` parameter, the SPA serves `index.html`, and pdf.js throws `InvalidPDFException: Invalid PDF
structure` (verified in the console on every document). The HEAD probe in `Doc.tsx` probes the same
route, gets 200, so `missing` is never set and `DocumentMissing` never renders. The real file is at
`/docs/core/where-there-is-no-doctor.pdf`, which returns 200 `application/pdf`.

What a household sees: the app's own chrome in five rows (band 113, Back, a title row carrying the
full catalogue string "Where There Is No Doctor (Hesperian, 1992 revised edition)", "Page [1] of an
unknown number / Previous / Next", "Find in this document / Smaller 100% Bigger"), then at y=405 the
**untouched pdf.js toolbar** — light grey, twelve wordless icons, "0 of 0", "Automatic Zoom", a
bright blue progress line, the only white slab in a blackout screen — and then nothing. Zero pixels
of the book, no error, on the box's two flagship references. `#page=350` is ignored. The rail lights
**Find** while a document is open. The console also carries two CSP violations per load: pdf.js
applies inline styles that the app's own `style-src 'self'` blocks.

**Fix** Stop feeding the route to the viewer. **Backend**: add a `file_url` to the library item
(`/docs/<tier>/<id>.<ext>`) so the frontend never has to guess. **Frontend**: use it for `PdfFrame`,
`EpubReader` and the HEAD probe; render `DocumentMissing` on a `documenterror` as well as a 404;
collapse the three chrome rows to one (Previous · "Page 4 of 210" · Next · Find · Text size); say
"Page 4 of 210" and, before the count is known, "Counting the pages…" rather than "of an unknown
number"; disable Next at the last page; light the rail for the destination the document was opened
from; drop the edition parenthetical from the screen title. Add `'unsafe-inline'` for the viewer's
own frame or ship a hashed stylesheet. Add an e2e that opens a real PDF and asserts a rendered page
canvas exists and `#toolbarContainer` is not visible.

### 3. Search snippets print raw `<b>` tags, and the box's own answers repeat three to five times

**Screen** `/search`. **Live** `bleeding`, `power cut`, `boil water`, `adder bite`, `insulin`.
Screenshots: `find-results-*.png`.

Three faults, all on the one screen a frightened household types into.

- **The markup is escaped, not rendered.** Measured `innerHTML` of a snippet:
  `&lt;b&gt;Adders&lt;/b&gt; The &lt;b&gt;adder&lt;/b&gt; is the only venomous snake…`. Every snippet
  of every query shows literal `<b>` and `</b>` around the matched word. One card's snippet also
  leaks the template token `[[call 999]]`.
- **De-duplication is by URL, and the box's own results carry section anchors**, so round 3's fix
  does not reach them. `bleeding` → "Severe bleeding" **five times** under "From this box", one row
  per matching section (Stop or escalate, When to use, Source, Warnings, and the tourniquet step) —
  its Source and its Warnings ranked as answers in their own right. `power cut` → "Solar panels in a
  power cut" **four times** in the top four. `adder bite` → "Ticks and adders" **three times**.
- **Library snippets are the source site's own furniture.** `bleeding` → "Anticoagulant medicines –
  Side effects" with the snippet "…Help us improve our website Can you answer a 5 minute survey about
  your visit today? Take our survey Support links Home Health A to Z NHS services Live Well … ©
  Crown copyright". Two of the top NHS results are entirely this.

**Fix** Render the API's highlight as a highlight — sanitise to `<b>` only and set it as HTML, or
have the API return match offsets. De-duplicate on the document, not the URL: strip `#…` before
comparing, keep the highest-scoring section per document, and show at most one row per guide or card
with a "3 more places in this guide" link. Strip NHS/GOV.UK page furniture from snippets, and never
render a snippet that contains no match. **Backend also**: `boil water` returns the box's own "Water
outdoors" page but never its **Water disinfection** reference page, which is the definitive answer
with the dosing table — round 3's coordinator item 3 (rank by tier before relevance) is still not
implemented, and the assistant retrieves over the same wrong list (see item 10).

### 4. The quick card's steps are 18 px body type on every real card, in every theme

**Screen** `/medical/card/:slug`. **Live** `cpr-adult` (8 steps), `choking` (7), `severe-bleeding`,
`hypothermia` (7), measured in vault, field and blackout. Screenshots: `quick-card-*.png`,
`quick-card-dim-*.png`, `quick-card-phones-off-*.png`.

`getComputedStyle` on every `ol li` of every card, in all three themes: **18 px**. The brief and the
round-0 plan both assign `--t-display` (40 px) to "a quick card's steps"; round 1 built it; round 3's
"the screen measures the third step and gives up a whole size at a time — display, lead, body" always
bottoms out at body, because the fixture card had four short steps and every real card has seven or
eight long ones. The card is once again a plain ordered list at paragraph size — the exact fault
round 1 opened with. On `choking` only **3 of 7** steps are above the fold on the kiosk in peacetime,
and none at all with the band up (item 1).

**Fix** Build the pagination round 3's own item 1 proposed and did not: one step per screen at
`--t-display`, a "Step 3 of 8" line, and 48 px Previous and Next, with a "Show all steps" for the
person who wants the list. That is what a card read at arm's length over a body wants, and it makes
the size independent of how many steps a card has. Failing that, set a floor of `--t-lead` (22 px)
and never let a quick card render at `--t-body`. Assert the computed step size in e2e on `cpr-adult`,
`choking` and `severe-bleeding`, in all six palettes.

### 5. The situation sheet asks for a date in mm/dd/yyyy, and is 3,733 px long

**Screen** `/situation`. **Live** setting "power off since four hours ago" — the flow this round was
asked to walk. Screenshots: `situation-sheet-853-*.png`, `situation-sheet-390-*.png`,
`print-situation-sheet-*.png`.

The "Time" control is a bare `datetime-local`, so it renders in the browser's locale, not the page's:
on this box it reads **"09/06/2026, 03:12 AM"** — 6 September shown as `09/06`, in twelve-hour time,
on a page marked `lang="en-GB"`, in the one field that decides whether the freezer food is still
safe. Round 1 fixed exactly this for the stock "Use by" field with `tools/dates.ts` and left the
`datetime-local` fields as a deferred item; two rounds later it is still the only date entry in the
box that lies about its own order.

Around it, the sheet is **3,733 px of scroll in a 423 px column** — 8.8 screens — because every one
of the ten conditions renders the full form whether or not anything is wrong with it: state buttons,
a "Since" select, a "Time" field, a "Note" field, a "Save note" button and a meta line. Nine of those
ten are working. A household that wants to add "the water has gone too" scrolls past four irrelevant
forms to reach it, and the screen head (Back, the title, Board, Print report, Find) scrolls away with
them, leaving no way back but the rail. The note placeholder — "street is dark as far as the shop" —
is truncated mid-word at "the shc" in a 285 px field on an 853 px screen with 200 px spare beside it,
and starts lowercase.

**Fix** Give the sheet a text date field parsed by `tools/dates.ts` ("dd/mm/yyyy hh:mm", placeholder
`06/09/2026 03:12`) as round 1 did for stock, or drop the field entirely in favour of the "Since"
choices plus "Choose a time…". Collapse a working condition to one row — its name, its state buttons
and nothing else — and reveal Since/Time/Note only for a condition that is not working, or behind a
"More" disclosure. Make the screen head sticky on the kiosk. Widen the note field to the panel and
capitalise its placeholder. **Print (content of the same screen)**: the print stylesheet prints the
whole live form — segmented buttons, selects, empty note inputs, "Save note", the carry textarea
containing `{"i":0,"n":3,"d":"H4sIAAAA…`, "Start drill" — and the instruction "Tap a state." on
paper. Print a static table instead: service, state, since, note.

### 6. Nearby answers from wherever the map happens to be, and never says where that is

**Screen** `/map` → Nearby, and `/map` itself. **Live** home set at 50.93, -1.43 (Southampton), the
health overlay on. Screenshots: `map-nearby-*.png`, `map-home-*.png`, `map-853-*.png`.

`/map` opens on **NY 0295 1266** at a 100 km scale — the Cumbrian coast, roughly 500 km from the
home the box has stored — and Nearby searches from that centre. The panel's answer, at
`--t-lead` in the pinned head where round 3 put it, is "**West Cumberland Hospital** — 5.13 km to the
north-west, about 1 h 02 min on foot", while the engine's own `meta.home.nearby` for this household
says "Spire Southampton Hospital, 184 m, 3 min on foot". Nothing on the panel says which point it
searched from. A frightened person reads that the nearest A&E is an hour's walk when it is three
minutes away.

Three more in the same panel: "Workington Community Hospital" is listed **twice** in the runners-up
(16.2 km and 16.3 km — two OSM nodes for one hospital); a pharmacy is named "**Unnamed**"; and the
caveat prints an OpenStreetMap tag name at a household — "The overlay does not carry the
`emergency=yes` tag". The Home panel reads "Your home: SU 4015 1465 — Home", the label appended after
an em dash so the word Home appears twice in one line. The map surface itself is mid-grey OSM in all
three themes, the brightest large area on a blackout screen at night.

**Fix** Open `/map` on the stored home at a street scale when a home is set, and only on the default
extent when none is. Put the origin in Nearby's pinned head — "From your home, SU 4015 1465" with a
48 px "Search from the map centre instead" — and change the pinned action's label to match whichever
is in force. De-duplicate results by name within 100 m. Show a place with no name as "Pharmacy (no
name recorded)". Rewrite the caveat without the tag name: "These come from OpenStreetMap and include
small hospitals with no A&E." Tint the map surface per theme (a dark wash in vault and blackout, the
paper style in field). Drop the trailing "— Home" when the label is the default.

### 7. The board contradicts itself about the clock and still speaks in system tags

**Screen** `/board`. **Live** with power/mobile/landline off and the grid-collapse scenario running.
Screenshots: `board-853-*.png`, `board-390-*.png`, `board-dim-*.png`.

On one screen, at once: the clock reads **06:12**; the Power tile reads "✕ off **for 5 h**" (so,
since 01:01); and the log line reads "**06:01** Mains power off **since 00:00** (kiosk) 10 min ago".
Two statements of the same fact an hour apart — the event stamp is local and the embedded "since" is
UTC. Every log line still carries "**(kiosk)**", and the drill line still reads "Drill ended: **0
tasks done in 120 minutes (drill)**" — the exact string round 3's item 4 says it dropped, and the
suffix `api/words.ts:eventTitle` was built to translate. The board does not use that translation.

The log is the bottom third of the across-the-room screen, in the smallest type on it, and its last
line is sliced by the 480 px edge with "Tap anywhere to go back" printed over it; the Mobile and
Landline tiles and "No stock recorded" are clipped to make room. The bulletin line reads "BBC local
radio FM, see the **comms module** for your station at 07:00" — a system word on the screen designed
to be read from a doorway — with its radio glyph vertically centred against a four-line wrap while
the sunset glyph beside it is top-aligned. With nothing running the headline is "**Something is
off**", which is the one thing a glance screen must not say.

**Fix** Route every board log line through `eventTitle` (fix the board, not the string). Render all
times in one zone — the box's local zone — and assert it in a test that sets a condition and reads
the tile and the log line back. Cap the log at three lines and give the space to the tiles. Replace
"see the comms module for your station" with the station or "your local BBC station". Make the
peacetime-with-something-off headline name it: "Power off · 5 hours". Top-align the icons in the
right column.

### 8. Three strips hide their own contents on the widest screen, and the keyboard buries every answer

**Screens** `/guides`, `/search`, `/ai`, `/map`. **Live** at 853x480, kiosk mode. Screenshots:
`guides-853-*.png`, `guides-filtered-853-*.png`, `find-results-853-*.png`, `find-empty-853-*.png`,
`map-853-*.png`, `map-share-853-*.png`.

- **Guides' filter chips.** `.chips` is `overflow-x: auto`, `clientWidth` 526 against `scrollWidth`
  826. "Reference (9)" starts at x=893 and "Tools (7)" at x=1030 — both past the 853 px edge — and
  measured live there is **no fade and no chevron**. Two of six categories are unreachable on the
  kiosk and nothing says they exist. The same six chips wrap onto three rows and are all reachable at
  390.
- **The map toolbar.** Print became the eighth tool in round 2 and the strip no longer fits: "Share"
  is clipped mid-word and Print sits behind a bare "**›**" with no word — in a box whose rule is that
  an icon always has a word.
- **Find's source chips.** `/search?q=bleeding` renders eight chips over four rows — including
  "Wicipedia (Welsh Wikipedia, with images) (8)" and "Motor Vehicle Maintenance and Repair Q&A (Stack
  Exchange) (2)" — filling the 480 px screen. The first result's top is at **y=553**: no result at
  all above the fold, before the keyboard is even open.
- **The keyboard.** Typing on the kiosk is the only way to search on it, and with the pad up the
  screen holds the band, "Find", the field and one chip row sliced in half: **zero results**, exactly
  the fault round 2's item 3 said it had fixed. The assistant is the same — its answer renders one
  line ("If the mains water supply fails, water companies must provide bottled water and") with the
  rest and all three citations under the pad. The number pad on `/medical/dose` scrolls the age field
  it was opened for clean off the top, so only "⚠ Enter the child's age." and the NHS source line
  remain visible.

**Fix** Wrap the Guides chip row at 853 as it wraps at 390 (it is 826 px of chips in a 757 px
column — two rows). Give the map toolbar the labelled overflow it needs ("More tools ›") or move
Print back to the head. Shorten Find's chips to the household word the badge already uses and put
everything past the fourth behind one "More sources" control. When the pad opens, pin the focused
field and at least the count plus the first two rows above `--kb-height` (round 2's rule, now broken
by the chip strip), and on `/ai` scroll the answer, not the field, into view; on `/medical/dose` use
the `data-kb-reveal` hook round 1 added so the age field stays on the screen. Extend
`e2e/keyboard-rail.spec.ts` to assert at least one result row is visible with the pad up.

### 9. The theme control is the loudest thing on the box, and its label does not fit its button

**Screen** every screen, both widths. **Live measurement** and screenshots: every `*-853-*.png` and
every `*-390-*.png` in the round-3 set.

In the rail the label span is **48 px wide holding 67 px of text** — it overflows its own border by
19 px and is clipped by the rail edge, which is why "Change theme" reads as "Change / theme" running
into the content column in all 177 kiosk screenshots. Its icon measures **6.8 px** against 20 px for
every rail destination, so the one control in the rail that is not a destination is also the only one
whose icon is illegible. On a 360 px phone and at 844x390 the same control is the only boxed,
two-line, icon-bearing element in the screen head, sitting on its own row **above** the search field
and above the "999 will not connect" panel: during a triple outage the most prominent control on the
front door is a cosmetic setting. Round 3 gave it a verb and an accessible name; it did not give it a
size.

**Fix** In the rail: label it "Theme" (the current theme stays in the accessible name, as round 3
set it), give the icon the destinations' 20 px box, and keep it visually separate from the five
destinations. On phones: make it a plain text item at the end of the head's first row beside Back, or
move theme switching into System and reach it from Find — nothing in the brief requires a theme
control on every screen. Add a test that no control's `scrollWidth` exceeds its `clientWidth` in the
rail at 853x480.

### 10. Copy, with the real content in it

Mostly **content-only** — route to whoever owns `playbooks/` and the manifest — except the first
three, which are the frontend's own strings.

- **`/` "Coming up": "Fridge food unsafe ▲ passed passed 1 h ago"** — the word twice, live, on the
  front door; and an event that has already happened sits under a heading called "Coming up".
  Round 3's item 6 fixed the "due" prefix and not the "passed" one.
- **`/` "Read": four buttons for two things to read.** "What still works in an outage", "Power",
  "Getting help without phones", "Communications" — the module each page belongs to renders as a
  sibling button of the same size and style, so a first-time user sees four destinations, two of
  which are category names.
- **`/` "The box thinks" offers the same guess twice**: "Internet — probably off" from the implication
  rule and again as "Internet — probably off · The box has detected this itself (internet)", each
  with its own Accept / Not now — ten buttons of data entry on the front door.
- **CPR step 1 with the phones down**: "Shout for help, a phone on speaker beside you — 999 will not
  connect while the phones are down: **get help without phones** ." — a step that hands you a phone
  and then says the phone will not work, with the link pushed to the right edge of the line by the
  step layout and an orphan full stop after it. Round 3 fixed the later steps of five cards and left
  step 1 of CPR, severe bleeding, childbirth and stroke because of the backend's 70-character rule;
  the rule needs to measure the rendered step (round 3's coordinator item 5) so these four can be
  written.
- **The assistant cites "(playbooks)"**: "[3] Cyber attack on infrastructure **(playbooks)**" — the
  word round 2 recorded as gone from every user-facing string.
- **`/medical` prints the catalogue**: "Self-built dated snapshot of nhs.uk made by `sos build-nhs`;
  the primary health reference and the target of the **AI health router**", "Licence: OGL v3",
  "zimgit", "(US framing, US drug names)", "Core" and "Offline copy" on every row of an offline box.
- **Peacetime says "Everything is working"** as the `h1` and the board headline over "Food: 0 days
  for 1 person / Water: 0 days / Medicine: 0 days / No meeting point written down / Nobody is
  registered yet". Reserve it for a box that is both undisturbed and ready; otherwise "Nothing is
  wrong. The box is not ready yet."
- **"Phones join it over its own WiFi, / SOS / ."** — a line break before the name and an orphan full
  stop after it, and "WiFi" for "Wi-Fi".
- **Two names for one place**: `/` in peacetime links "Situation sheet"; `/` in a power cut and
  `/tasks` link "Situation". The read-aloud button is "Read this section aloud" on a guide, "Read
  this module aloud" on a module and "Read this page aloud" on a page.
- **A running scenario states its time four ways at once**: the head reads "National grid collapse ·
  Active · Started Sun 06:11 · just started, right now · End situation", the band reads "National
  grid collapse | just started", and Now's `h1` reads "National grid collapse · just started".

## Watch list

1. **The symbol and shape vocabulary, deferred three rounds.** ⚠ now does eight jobs: danger, the
   drill chip, the engine-down line, the Timers tile, "AI can be wrong", the empty-form hint "Enter
   the child's age", the OpenStreetMap caveat, and the "passed"/"due" markers in Coming up. Beside
   it: `999px` pills on `.chip`, `.badge` and `.cond-chip-compact` against a stated single 6 px
   radius; four border weights (1 px panels, 2 px state buttons, 3 px accent edges, 6–8 px progress);
   and `--glow` still applied as a `text-shadow` in vault, in a system whose rule is "no shadows".
   Round 2 called it the round-3 item, round 3 called it the round-4 item. It is now the round-5 one
   and it is the last chance.

2. **The reader and the EPUB viewer.** A real Wikipedia article prints its title twice (the screen
   head and the ZIM's own `h1`), renders full-brightness colour photographs inside blackout at night,
   draws body links in a colour indistinguishable from body ink, and labels its control "Text size
   100%" — a percentage, not a verb. `EpubReader` in `Doc.tsx` registers three hard-coded palettes
   (`#0a0f0a`, `#39ff7a`, `#1a3f8a`, `#ff7070`) that are not in `tokens.css` and do not follow dim —
   the second-palette fault round 2 fixed for the PDF viewer and did not fix for the EPUB one.

3. **Print has no identity and one inconsistent heading size.** No running header, no footer, no
   product name, no printed-on date and no page numbers on any printable screen, so a sheet pulled
   out of the box cannot be identified or reassembled. Print `h1` measures 28 px on a quick card and
   22 px on a page against the stated 20 pt. A printed scenario is 27,009 px — about 26 A4 sides — and
   carries live relative timestamps ("ticked 3 days ago", "1 of 3 done, last change 3 days ago") onto
   paper. `/medical/card/*` also runs its two warnings into one paragraph, each prefixed "Warning:",
   on screen and on paper.

4. **Two destinations lit at once, and other wayfinding.** On `/ai` both **Find** and **AI** carry the
   lit rail style; on `/doc/:id` the rail lights **Find** whatever the document was opened from. "Ask"
   is a disabled primary with nothing saying why — the rule round 2 set for "Start drill". The number
   pad offers a **minus** key on a child's age field. On a landscape phone and a 360 phone the bar
   carries five destinations and neither System nor the assistant, which are reachable only through
   panels on Now and Find.

5. **Dim in field, and the fixture drifting from the box.** Measured mean luminance change between
   the round-3 pairs and their `-dim` twins: vault −37 %, blackout −24 %, **field −12 %** — a
   near-white slab at night — and dim is never named on screen in any theme, so nobody can tell it is
   on. Separately, three faults this round found live were invisible in 354 fixture screenshots (the
   PDF viewer, the 18 px card steps, Nearby searching from Cumbria) and one fixture fault was not
   real (the blank map canvas). Round 5 should shoot at least the card, the doc viewer, Find and
   Nearby against the real API.

## For the coordinator: what is not the frontend's to fix

- **Backend** — item 2: `/api/library/<id>` returns `url` as the app route, with no field naming the
  file on the drive. Add `file_url`.
- **Backend** — item 3: de-duplication and tier-before-relevance ranking (round 3's coordinator items
  2 and 3, still open); snippet generation that returns page furniture and template tokens
  (`[[call 999]]`); chip counts (round 3's coordinator item 1).
- **Backend** — item 7: the board's log strings mix local and UTC clocks; the `(kiosk)`/`(drill)`
  suffixes are written into the event text at source.
- **Backend** — item 10: `test_card_structure_and_screen_rule` still caps the first three steps at 70
  characters of Markdown source, which is what blocks a calls-off variant in step 1 of CPR, severe
  bleeding, childbirth and stroke (round 3's coordinator item 5).
- **Content** — item 10: the `/medical` library descriptions, the "(playbooks)" citation label, the
  "comms module" bulletin string, and the peacetime "Everything is working" wording.
- **Still open from round 3** — a drill has no expiry; the live box carried a "Drill ended: 0 tasks
  done in 120 minutes" from an unended drill into this round's board.
