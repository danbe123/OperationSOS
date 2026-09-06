# Round 1: critique

Reviewed against `docs/superpowers/specs/2026-09-06-interface-redesign.md` (sections 5 and 6), the
design rules in section 11 of `docs/superpowers/specs/2026-09-03-operation-sos-design.md`, and the
294 screenshots in `docs/superpowers/critique/round-0/`.

## Verdict

The shell works: the rail and the bar never move, the destinations are icon-plus-word, the panels are
flat and quiet, and a stranger would find Guides, Medical and Map without being told. What the shell
carries has not caught up with it — the two screens a life depends on are the two that were not
finished (a quick card set in body type, and a situation sheet that paints the chosen state in the
colour that means "working"), and the kiosk's number pad hides the digits 1, 4 and 7. Under that sit
the ordinary faults of a first pass: one list of jobs wearing four different names, a Now screen
whose largest word is "62", and a band that no longer says how long the power has been off.

## The ten

### 1. The quick card is not a quick card

**Screen** `/medical/card/:slug`. **Files** `quick-card-853-vault.png`, `quick-card-390-vault.png`,
and the field and blackout pairs.

CPR renders as a plain ordered list at body size — the same 18 px as a paragraph on Guides — with
half the kiosk screen and two-thirds of the phone screen empty below it. The inventory asks for
"extra-large type" and the design plan assigns `--t-display` (40 px) to "a quick card's steps"; that
never landed. Someone kneeling over a body reads this at arm's length in the dark.

**Fix** Set the card's steps at `--t-display` with the step number in the same size and weight as the
step, one step per line, using the empty space. Keep the ⚠ warning at `--t-lead`. Move the "call 999"
line from the bottom of the card to the top, above step 1, as the same 999 component used on
`/medical` (see item 4), so the first thing on the screen is the call and the second is the first
compression.

### 2. The chosen condition state is painted green

**Screen** `/situation`. **Files** `situation-sheet-853-vault.png`, `situation-sheet-853-field.png`,
`situation-sheet-853-blackout.png`, and the 390 set.

Selecting "✕ Off" gives that button a **signal-green** border in vault and field and the palest pink
border in blackout — in every theme, the colour that means *working* everywhere else in the app.
`.btn[aria-pressed="true"] { border-color: var(--signal) }` in `components.css:22` beats
`.state-set.state-danger` in `screens/situation.css:13`, so the per-state colours round 0 added never
appear. In blackout the selected button is the *dimmest* of the three, which in that theme's
luminance ladder reads as "working". A frightened person cannot tell what the box thinks is broken,
on the one screen whose whole job is to tell them.

**Fix** Raise the `.state-set.*` rules above the generic pressed style (or scope the pressed rule so
it does not apply to `.state-btn`) so the set state carries `--ok` / `--warn` / `--danger` on its
border, its text and a filled `--sunken` ground, and the two unset states stay on `--line`. Verify by
eye in all three themes that the set button is the loudest of the three, not the quietest.

### 3. The kiosk number pad hides 1, 4 and 7

**Screen** every kiosk field with `inputmode="numeric"` — children's doses, the admin PIN, the timer
minutes, the System thresholds. **Files** `childrens-doses-853-vault.png`,
`childrens-doses-853-field.png`.

simple-keyboard's own stylesheet sets `.hg-theme-default.hg-layout-numeric .hg-button { width: 33.3% }`,
and the numeric layout has four keys a row (`'1 2 3 {bksp}'`), so each row is 133 % wide and
`justify-content: center` in `shell.css:163` throws the overflow off both ends: the left column's
labels are clipped away entirely and "done ▾" reads "do". A parent typing a four-year-old's age to
get a paracetamol dose cannot type 1, 4 or 7, and cannot find the key that closes the pad.

**Fix** Add `.sos-kb.hg-layout-numeric .hg-button { width: auto; flex: 1 1 0; min-width: 64px; }` to
`shell.css` and re-shoot `childrens-doses-853-*`. While there: the pad opens over the dose it was
asked to compute, so scroll the answer, not just the field, into view above `--kb-height`.

### 4. Medical says the same warning twice, and 999 has five faces

**Screen** `/medical`, `/medical/card/:slug`, `/medical/dose`, `/tools/timers`, `/radio`.
**Files** `medical-phones-down-853-vault.png`, `medical-853-vault.png`, `quick-card-853-vault.png`,
`timers-853-vault.png`, `phone-and-radio-853-vault.png`.

With the phones down, `/medical` stacks two red-and-amber notices that say one thing — "Phone numbers
on this page will not connect…" then "**999 will not connect** while both networks are down" — with
two different labels ("Getting help without phones", "How to get help without phones") for the same
page, and each notice draws its warning symbol twice (`<Icon name="alert">` plus a literal `⚠` in
`Medical.tsx:50` and `CallsNotice.tsx:12`). Worse, the same `.panel panel-danger` carries both "call
999" and "999 will not connect": one red panel, two opposite meanings. Across the app the 999 line
appears five different ways — a red panel with a phone icon, a small `.warning` line at the *bottom*
of a quick card, a sentence inside the dose disclaimer, a sentence with a stray "📞 999" appended on
Timers, and a dot-run on Phone and radio.

**Fix** Make one `<Emergency999>` component with two states — *can call* (phone icon, `--danger`
panel, "Life-threatening emergency: call 999. Urgent advice: 111.") and *cannot call* (⚠ symbol,
`--warn` ground so it is visibly not the same panel, "999 will not connect while both networks are
down", one link "Getting help without phones"). Use it at the top of `/medical`, `/medical/card/*`,
`/medical/dose`, `/tools/timers` and `/radio`, suppress `CallsNotice` on any screen that renders it,
and delete the duplicated `⚠` glyphs.

### 5. The band no longer says how long

**Screen** the shell, everywhere. **Files** `now-power-off-853-vault.png`, `now-power-off-390-vault.png`,
`situation-sheet-853-vault.png`, `now-drill-853-vault.png`.

The brief's own sketch of the band reads "● Power off 4 h". The built band reads "⚡ Power ✕ off" —
`.cond-chip-compact .cond-for { display: none }` in `components.css:97` hides the duration on the one
element that is meant to be memorable, so the box tells you what is broken but not for how long,
which is the number that decides whether the freezer is still safe. The chips are also `min-height:
40px` (`components.css:96`) although they are `<Link>`s and the first thing a hand reaches for. And
"▲ 4 to do" is rendered with `cond-chip cond-warn` — the identical pill, in the identical amber, as a
condition state — so a count of jobs reads as an eleventh thing that is wrong.

**Fix** Show `cond-for` in the compact chip (a phone fits "Power off 4 h"; drop the chip's icon
before dropping the duration) and raise `min-height` to `var(--touch)`. Give the jobs link its own
look — plain text with a count and a right chevron, or the small button style already used by
"Situation" — so nothing in the band that is not a condition wears a condition chip.

### 6. Now opens by telling you it is Now

**Screen** `/`. **Files** `now-power-off-853-vault.png`, `now-peacetime-853-vault.png`,
`now-empty-household-390-vault.png`.

In a power cut the largest words on the front door are "Now" (the `h1`, which repeats the lit rail
item and says nothing) and "Do now". Nothing on the screen names what is happening; the reader has to
decode a small chip in the band. In peacetime the largest thing on the screen is **62**, a score out
of 100 whose meaning is never given, followed by "worth 12 points" — game vocabulary on an emergency
box, and a number that is meaningless on a box where nobody has registered yet
(`now-empty-household-390-vault.png` shows 62 with an empty household). There is no plain "start
here" the brief asks for.

**Fix** Make the `h1` the answer: the scenario name when one is running ("National grid collapse ·
1 h in"), "Power off" when only conditions are off, and "Everything is working" in peacetime; drop
the word "Now" from the content (the rail already says it). Replace "62 out of 100 ready" and "worth
12 points" with a plain sentence — "You have water for 1.5 days. Three things would help most." — and
render each gap as the same task row used by "Do now", not as an underlined link. Add a single
first-run line above them: "New box? Add who lives here, then your water and food."

### 7. One list of things to do, under four names

**Screens** `/`, `/tasks`, `/s/:slug`, the band, `/search`, `/situation`. **Files**
`now-power-off-853-vault.png`, `tasks-853-vault.png`, `scenario-right-now-853-vault.png`,
`find-results-853-vault.png`, `situation-drill-853-vault.png`.

The same list is "Do now" on Now, "All tasks" in its header, "Tasks" as a screen title, "Right now"
as its first bucket, "Checklist" on a scenario and "4 to do" in the band. Tasks then prints its count
three times on one screen — the band chip, a "4 to do" pill by the title, and "4 to do, 0 done."
under it — which is the double count round 0 removed from the checklist, moved house. The same drift
hit the guides: the destination is "Guides", its first section is "Situations", Find labels the same
content **"Playbook"**, and the drill form says "Choose a playbook…" — a word the brief says a
household never has to learn.

**Fix** Pick one noun and one bucket name and use them everywhere: "Things to do", with buckets
"Right now", "Today", "This week", "Done". Header link "All of them", scenario panel heading "Things
to do for this guide". Delete the pill next to the Tasks title and keep the sentence. Map the API's
`badge` to household words in one place (`playbook` → "Guide") and change the drill select to "Choose
a situation…".

### 8. A scenario leads with a switch, and hides half its tabs

**Screen** `/s/:slug`. **Files** `scenario-right-now-853-vault.png`, `scenario-right-now-390-vault.png`,
`scenario-later-853-vault.png`.

"This has started" is a filled `--signal` button — the app's one primary style — sitting above the
guidance, so the loudest thing on a screen someone opened to *read* is a box-wide state change with
its consequence set beside it in muted grey. Below it, six tabs do not fit: at 853 the last reads
"Go d" against the edge, at 390 only three of six show, and there is no fade, chevron or count to say
more exist, so "Long term", "UK specifics" and "Go deeper" are invisible content. On the phone the
tick list still comes after all the prose.

**Fix** Demote "This has started" to an outline button in the screen head beside Map and Print, with
its consequence as the button's own second line or a tooltip-free line under the head; the guidance
becomes the first thing under the title. Give the tab strip a `scroll-snap` row with a `--ground`
gradient fade at both ends and arrow buttons on the kiosk, or wrap the tabs to two rows at 390 so all
six are visible. On one column, put the task panel above the prose.

### 9. Search: a button with no word, and two fields that do different things

**Screens** every kiosk screen head, `/guides`, `/search`. **Files** `guides-853-vault.png`,
`guides-filtered-853-vault.png`, `find-empty-853-vault.png`, `now-power-off-853-vault.png`.

The compact search submit renders the magnifier with no word (`SearchBar.tsx`: `{!compact && <span>Search</span>}`),
breaking the rule that every icon has a word — and because it is the only filled `--signal` element
on most screens, it is also the first thing the eye lands on, on every screen, for the least urgent
control in the app. Guides then stacks a second text field directly beneath it: "Search the box" over
"Filter the guides", two inputs, no visual difference, one that leaves the screen and one that does
not. And on the kiosk the auto-opened keyboard buries what both were asked for — `find-empty-853` and
`guides-filtered-853` show only a result *count* above the keys, with the results themselves out of
reach.

**Fix** Give the compact button its word ("Search") and the quiet button style, keeping the accent for
the screen's own primary action. On Guides drop the head's search field and let the filter be the only
input, labelled "Filter these guides" with the chips directly attached to it. On the kiosk, scroll the
first result row — not the field — into view above `--kb-height` after a search, and render the count
line immediately under the field so it is not the only thing visible.

### 10. Cards that all look alike, and rows you cannot hit

**Screens** `/guides`, `/medical`, `/search`. **Files** `guides-853-vault.png`, `guides-390-vault.png`,
`medical-853-vault.png`, `find-results-390-vault.png`.

Each of the twenty situation tiles carries a summary line that repeats its own title and then
ellipses — "Nuclear war · Nuclear war: what to do right now…" — twenty tiles of dead text with the
useful part cut off. On Medical, the two quick cards (the life-critical, two-tap items) are drawn
smaller and plainer than the NHS A-to-Z tiles below them, so the least urgent thing on the screen is
the biggest. And a Find result is tappable only on its underlined title — a ~16 px target on a phone,
below the 48 px floor, with the rest of the row inert.

**Fix** Replace the tile summary with the guide's own first line ("Blast, then fallout: stay in for
48 hours") and, where none exists, show no line rather than the title again. Give the quick cards a
distinct treatment — full-width rows with the `--danger` left edge already used by the 999 panel, at
`--t-lead` — so Medical's order of loudness is 999, quick cards, then everything else. Make the whole
result row the link (`display: block; min-height: var(--touch)`), with the badge inside it.

## Watch list

1. **Unchecked ticks read as disabled.** In vault and blackout an empty checkbox is a filled grey
   square with no border (`now-power-off-390-vault.png`, `tasks-853-blackout.png`); only field draws a
   real empty box. The "Show done" filter reuses the same square as a task tick, so a filter and a job
   look identical. Draw the empty state as a 26 px `--line-strong` outline on `--sunken` in all three
   themes, and give the filter a different control.

2. **The generic tells that survived.** Dot-joined meta strings ("305 m · 4 min on foot · 040° NE" in
   `map-nearby-853-vault.png`; "1.8 GB · as at 2026-08 · OGL v3" in `library-853-vault.png`;
   "Emergency 999 · NHS 111 · Power cut 105 · Floodline…" in `phone-and-radio-853-vault.png`), arrows
   appended to controls ("◀ Day before", "Day after ▶", "Next ›" in `sun-and-moon-853-vault.png` and
   `situation-carry-853-vault.png`), "5 results in 120 ms" on Find, and the tracked-out uppercase
   "SITUATION" eyebrow that exists on the kiosk band but not the phone one — so it is decoration, not
   information. Also: filter chips, source chips and condition states are all the same 999 px pill.

3. **System words in front of a household.** "Load 0.30 / 0.20 / 0.10" and "Memory 2100 of 8000 MB"
   (`system-853-vault.png`), "zim" as a badge (`library-853-vault.png`), "the situation is
   unavailable: the engine is not answering" with no "Try again" (`now-engine-down-853-vault.png`),
   the lowercase suggestion badges "wikipedia / pages / **query**" (`keyboard-853-vault.png`), and
   "walking time by Naismith's rule (5 km/h)" (`map-nearby-853-vault.png`).

4. **British English and UK formats.** `/situation` has `<h2>Practice a drill</h2>` (US) while Now's
   button says "Practise a drill" — the same feature, two spellings, one wrong
   (`situation-drill-853-vault.png`, `now-peacetime-853-vault.png`). The stock "Use by" field renders
   as **mm/dd/yyyy** (`stock-853-vault.png`).

5. **What the phone spends its first 150 px on.** "☀ Theme: Vault" gets a full row of its own above
   every screen title (`now-peacetime-390-vault.png`); Print takes the top, non-scrolling slot above
   the map's seven-tool scroller, which itself has no scroll cue and clips "Home" mid-word
   (`map-390-vault.png`, `map-share-390-blackout.png`); the drill banner adds two more rows before any
   content (`now-drill-853-vault.png`). Also on the phone: `Remove` sits at equal weight beside `Edit`
   on every person and every stock line (`household-853-vault.png`, `stock-853-vault.png`), and the
   reader prints its title twice, once in the head and once as the article `h1`
   (`reader-853-vault.png`).

## Applied

Every screenshot below is `docs/superpowers/critique/round-0/<name>` before and
`docs/superpowers/critique/round-1/<name>` after, at the same width and in the same theme. The whole
inventory was re-shot with `node scripts/screenshots.mjs round-1`.

### 1. The quick card is not a quick card

The card's steps run at `--t-display` (40 px), one to a line, with the step number in the same size
and weight as its words (`styles/type.css`, `.card-html ol`). The `⚠` warning stays at `--t-lead`, and
the "call 999" line moved from the bottom of the card to the top, above step 1, as the same
`<Emergency999>` component `/medical` uses. `screens/Card.tsx` renders nothing else.

Before `round-0/quick-card-853-vault.png`, `round-0/quick-card-390-vault.png` (and the field and
blackout pairs) · after the same names under `round-1/`.

### 2. The chosen condition state is painted green

Root cause: `.btn[aria-pressed="true"]` in `components.css` outranked `.state-set.state-danger`. The
generic pressed rule is now scoped — `.btn.active:not(.state-btn), .btn[aria-pressed="true"]:not(.state-btn)`
— so a state button never wears the accent, and `screens/situation.css` gives the unset states the
plain `--line` border while the set one carries `--ok` / `--warn` / `--danger` on its border and its
text over a `--sunken` ground, in bold. Checked by eye in all three themes: the set state is the
loudest of the three.

Before `round-0/situation-sheet-853-{vault,field,blackout}.png` and the 390 set · after the same
under `round-1/`.

### 3. The kiosk number pad hides 1, 4 and 7

`shell.css` adds `.sos-kb.hg-layout-numeric .hg-button { width: auto; flex: 1 1 0; min-width: 64px; }`,
which undoes simple-keyboard's own `width: 33.3%` on a four-key row. Every digit and `done ▾` is on
the screen and at least 48 px wide. While there: a field can name what has to stay in sight
(`data-kb-reveal`), and the keyboard brings that up instead of the field, so the dose the pad was
asked to compute sits above the pad; every other field is scrolled to the top of what is left rather
than centred. New spec `e2e/keypad.spec.ts`.

Before `round-0/childrens-doses-853-{vault,field}.png` · after `round-1/childrens-doses-853-*.png`.

### 4. Medical says the same warning twice, and 999 has five faces

New `situation/Emergency999.tsx` with two states and no others: *can call* — `--danger` panel, phone
icon, "Life-threatening emergency: call 999. Urgent advice: 111." — and *cannot call* — a `--warn`
bordered panel on `--sunken`, the `⚠`, "999 will not connect while both networks are down" and one
link, "Getting help without phones". It is at the top of `/medical`, `/medical/card/*`,
`/medical/dose`, `/tools/timers` and `/radio`; `CallsNotice` is suppressed on all five and draws its
own `⚠` once. The Phone-and-radio dot-run became a "Numbers to ring" list.

Before `round-0/medical-phones-down-853-vault.png`, `round-0/medical-853-vault.png`,
`round-0/quick-card-853-vault.png`, `round-0/timers-853-vault.png`,
`round-0/phone-and-radio-853-vault.png` · after the same under `round-1/`.

### 5. The band no longer says how long

`components.css` no longer hides `.cond-chip-compact .cond-for`; the chip says "Power ✕ off 1 h" and
drops its icon under 700 px before it drops the duration (`shortDuration` in `situation/conditions.ts`).
The chips are `min-height: var(--touch)`. The jobs link is no longer a condition pill: it is the small
button style the "Situation" link already uses, reading "3 things to do". The band's tracked-out
"SITUATION" eyebrow is gone with it.

Before `round-0/now-power-off-853-vault.png`, `round-0/now-power-off-390-vault.png`,
`round-0/situation-sheet-853-vault.png`, `round-0/now-drill-853-vault.png` · after the same under
`round-1/`.

### 6. Now opens by telling you it is Now

`situation/nowTitle.ts` makes the `h1` the answer: "National grid collapse · 1 h in" while a scenario
runs, "Power off" or "Power off, mobile patchy" when only conditions are off, "Everything is working"
in peacetime. The word "Now" is gone from the content; the rail still says it. `Readiness.tsx` drops
the score and the points for a plain sentence — "You have water for 1.5 days. One thing would help
most." — renders each gap as the same row shape as a job (48 px, no underline), and shows
"New box? Add who lives here, then your water and food." while nobody is registered. The engine-down
line lost its system words and gained a **Try again** button.

Before `round-0/now-power-off-853-vault.png`, `round-0/now-peacetime-853-vault.png`,
`round-0/now-empty-household-390-vault.png`, `round-0/now-engine-down-853-vault.png` · after the same
under `round-1/`.

### 7. One list of things to do, under four names

One noun: **things to do**. `/tasks` is titled "Things to do", its count is said once in a sentence
(the pill is gone), Now's panel is "Right now" with "All of them" beside it, a guide's panel is
"Things to do for this guide", and the band says "3 things to do". The API's own vocabulary is
translated in one place, `api/words.ts`: `playbook` → "Guide", `docs` → "Documents", `zim` →
"Offline copy", `query` → "Search for this", and every badge, source chip and suggestion goes through
it. The drill and clock selects say "Choose a situation…".

Before `round-0/now-power-off-853-vault.png`, `round-0/tasks-853-vault.png`,
`round-0/scenario-right-now-853-vault.png`, `round-0/find-results-853-vault.png`,
`round-0/situation-drill-853-vault.png` · after the same under `round-1/`.

Kept as they were, with reasons: the fourth bucket is still "Within the hour" — the engine raises
four buckets and the critique's list names three, and dropping one would put hour jobs under "Today";
and "Done" is a filter on this list, not a fifth bucket, so it stays a chip.

### 8. A scenario leads with a switch, and hides half its tabs

"This has started" moved into the screen head beside Map and Print as an outline `btn-small` carrying
its consequence on a second line, so the guidance is the first thing under the title. The tab strip
wraps instead of scrolling (`components.css`, `.tabs { flex-wrap: wrap }`), so all six phases are
visible at 853 and at 390 with no fade, chevron or count needed to say the rest exist —
`e2e/ux.spec.ts` now asserts that no tab is past the end of the strip. On one column the task panel
is above the prose (`screens/scenario.css` grid areas).

Before `round-0/scenario-right-now-853-vault.png`, `round-0/scenario-right-now-390-vault.png`,
`round-0/scenario-later-853-vault.png` · after the same under `round-1/`.

### 9. Search: a button with no word, and two fields that do different things

The compact submit has its word ("Search") and the quiet button style; the accent is left to the
screen's own primary action. Guides no longer carries the head's search field at all, so its filter —
"Filter these guides" — is the only input on the screen, in one bordered block with its chips
attached. On Find the count line sits immediately under the field, says "5 results." and not
"5 results in 120 ms", and when the on-screen keyboard is up the results are scrolled to the top of
what is still visible.

Before `round-0/guides-853-vault.png`, `round-0/guides-filtered-853-vault.png`,
`round-0/find-empty-853-vault.png`, `round-0/now-power-off-853-vault.png` · after the same under
`round-1/`.

### 10. Cards that all look alike, and rows you cannot hit

`api/words.ts:tileLine` strips a summary that opens by repeating its own title and shows no line at
all when nothing useful is left, and the browser fixture now carries each guide's real first line
("A nationwide or regional blackout lasting days to weeks.") instead of a generated
"<title>: what to do right now…". Medical's quick cards are full-width rows at `--t-lead` with the
`--danger` left edge the 999 panel wears, so the screen's order of loudness is 999, quick cards, then
everything else. A Find result is one target: `display: block`, `min-height: var(--touch)`, badge
inside.

Before `round-0/guides-853-vault.png`, `round-0/guides-390-vault.png`, `round-0/medical-853-vault.png`,
`round-0/find-results-390-vault.png` · after the same under `round-1/`.

## The watch list

Taken:

1. **Unchecked ticks read as disabled.** Checkboxes are drawn, not left to the browser: a 26 px
   `--line-strong` outline on `--sunken` when empty and a filled `--signal` box with a tick when done,
   the same in all three themes (`components.css`). The "Show done" filter is a chip, not a tick, so a
   filter and a job no longer look like the same control.
2. **Generic tells.** The dot-runs are sentences: a nearby place reads "620 m to the east, about 8 min
   on foot" (`map/nearby.ts`, with `compassWord`), a library item "4.5 MB, copied 2026-01. Licence:
   CC BY-SA 4.0.", the phone numbers a list. "◀ Day before" and "Day after ▶" are icon-and-word
   buttons. "5 results in 120 ms" is "5 results.". The uppercase "SITUATION" eyebrow is deleted.
3. **System words in front of a household.** "Load 0.30 / 0.20 / 0.10" is "Working lightly"; "Memory
   2100 of 8000 MB" is "26% used of 7.8 GB"; the `zim` badge is "Offline copy"; the engine-down line
   says "The box cannot read the situation" with a **Try again** button; the suggestion badges read
   "Wikipedia", "Page" and "Search for this"; the nearby panel says "as the crow flies. The walking
   time is a rough one; the box has no route planner." instead of naming Naismith's rule.
4. **British English and UK formats.** `/situation` says "Practise a drill", the same as Now. The
   stock "Use by" field is a `dd/mm/yyyy` text field parsed by `tools/dates.ts`, because a native date
   input takes its order from the browser's own locale and shipped `mm/dd/yyyy` on a page already
   marked `lang="en-GB"`; a saved date reads back as "use by 06/09/2026".
5. **The phone's first 150 px** — the theme button no longer has a row to itself above the title on
   the five screens with no Back button; it shares the title's line (`screen-head-noback`).

Left, with reasons:

- **Filter chips, source chips and condition states are all the same 999 px pill** (watch list 2).
  Separating them is a change to the shape vocabulary the whole app shares, which is a round-2
  decision about the component set rather than a fix inside one of the ten.
- **Print above the map's tool scroller, the scroller's own cut-off "Home", and the drill banner's two
  rows** (watch list 5). The map toolbar is the seven tools the brief names and Print is in the head
  by the round-0 plan; changing either is a map layout question that wants its own pass.
- **`Remove` at equal weight beside `Edit`** (watch list 5). The only ways to make it quieter are a
  smaller target, which breaks the 48 px floor, or a new button variant, which adds to the set the
  design plan keeps small.
- **The reader printing its title twice** (watch list 5). The second title is the article's own `h1`
  inside the ZIM, in the reader iframe; suppressing it means rewriting fetched content.
- **`datetime-local` fields** on the situation sheet and the fallout timer still take their order from
  the browser. The watch list names the stock field; the same treatment for a date *and* a time wants
  its own small component rather than a fourth ad-hoc parser.
