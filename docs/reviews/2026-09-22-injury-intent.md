# Injury intent, 2026-09-22 (task 25)

The owner's report, live on `main` (`51ef892`): "gash on arm" put the page "The essentials, printed" first,
the **Broken bones** card second and a Wikipedia footballer ("Sam Gash") third. Further down were "Falling
(accident)", the Spinal injury card and "Olympic Arms". **Wound cleaning** was 26th, and **Severe bleeding** and
**Closing a wound** were not in the top 30. The owner asked: "quick card broken bones higher than severe bleeding or
closing a wound or wound cleaning??" The cause: Broken bones is the only card that says "arm" (five times), and
`fts_match_expanded` ANDs `("gash" OR "wound" OR "cut" OR "laceration" OR "bleeding")` with `"arm"`. The dense
cosine is 0.50, below every floor.

Branch `injury-intent`, from `main` at `51ef892`. The plan is Codex's read-only advice
(`.superpowers/sdd/2026-09-18-semantic-search-expansion/codex-injury-advice.md`). I implemented its priorities 1, 2
and 3 as one fix. Priority 4 (a compact card-only dense index) was not done; see §6.

## 1. What changed

**Held-out set first** (`48c99fb`). `tools/eval/search/injury-heldout-2026-09-22.jsonl` has 46 rows:

- 33 injury phrasings not seen before, across bleeding, wounds, burns and scalds, sprains, fractures, eye, head,
  nosebleed and bites.
- 13 contrasts that must not trigger the injury policy. Names: "Sam Gash", "Olympic Arms", "Robert Burns poems",
  "Burn Notice", "Broken Arrow film". Phrases: "power cut what to do", "bike brake bleeding", "broken link",
  "burn a CD", "arm wrestling rules", "Achilles heel meaning". Book requests: "a book about treating gunshot
  wounds", "old book on first aid for snake bites".

I checked it against the real DB and ZIMs (`--validate`) and committed it before any search ran against it.
`searcheval` now treats any gold file with `heldout` as a dash-word of its name as held out, so lab and default runs
never include it.

**Replay depth** (`f9902f9`, Codex §9). `ReplaySemantic` sliced whatever depth had been recorded without saying so,
so a 100-deep recording answered task 24's 500-deep card rescue with no reported miss. Recordings now keep the depth
they asked for, `RECORD_K` is 500, and asking deeper than the recording counts as a `semantic_depth` miss. I made a
fresh recording (`.dev/search-recordings/rec-all-2026-09-22`, 500 deep) with main's search code. Every number below
is a replay of it, with 0 kiwix, 0 wikipedia and 0 semantic_depth misses.

**Injury analysis** (`api/sos/query.py`, `8de0e2d`, Codex §2):

- `analyse_injury(raw) -> InjuryIntent` gives `(conditions, locations, modifiers, confidence, purpose,
  matched_rules)`. It reads the raw words in order, keeping stopwords, because "my", "himself" and "won't" are what
  make a word bodily.
- Nonmedical phrases are removed first as one compiled pattern: "power cut", "brake bleeding", "burn a CD",
  "broken glass", "blood sugar" and others.
- Unambiguous words confirm a condition on their own: wound, laceration, scald, fracture, sprain, haemorrhage.
- Ambiguous words need support. The words are cut, gash, burn, broken, bleeding, twisted and bite. The support can
  be a body part, a reflexive ("myself"), a care word ("treat", "stitches"), a severity word ("won't stop",
  "pouring"), or an injury pattern:
  - hot liquid spilled or splashed on a person
  - a limb "bent the wrong way"
  - "bone sticking out"
  - a twist to a joint
- A single word typed alone that is an injury on its own ("gash", "burns", "bleeding") confirms too.
- Places that are the condition keep their anatomy: nose with bleeding is a nosebleed, not severe bleeding. The same
  applies to the eye with a foreign body or a blow, and the head with an impact.
- `purpose` is `book` for a book, novel or poem request and `lookup` for a film, meaning or biography. Only `care`
  intent is `confirmed`.
- `fts_match_conditions` asks for the condition's words with the place left out.

**Card subjects** (Codex §4):

- Eleven injury cards gain search-only front matter: `conditions:` (ids from `query.CONDITION_IDS`) and `aliases:`
  (lower case, scoped to the card).
  - Severe bleeding: heavy bleeding, won't stop bleeding, tourniquet, stab wound.
  - Wound cleaning: cut, gash, graze, laceration, puncture wound.
  - Closing a wound: gaping cut, deep cut, stitches, steri-strips.
  - Broken bones: broken arm or leg, bent the wrong way, splint. It gets **no** wound or bleeding words.
  - The other seven cards: Burns, Sprains and strains, Head injury, Eye injury, Nosebleed, Bites and stings, Spinal
    injury.
- `playbooks/schema.json` accepts both fields (cards only, with an enum and an alias pattern), and
  `playbooks/README.md` documents them.
- `sos index` writes the aliases once, on the card's "When to use" row, into a new `fts_docs.aliases` column. That
  column is appended so the body stays column 1 for `snippet()`. An old index is rebuilt with the column on first
  start, and its rows are kept. The subjects go into a new `card_subjects` table.
- The keyword query ranks with `bm25(title 5, body 1, aliases 5)`.
- Displayed titles and bodies are unchanged. The content tests read every alias as a query and fail if it names a
  condition its card does not treat.

**Search policy** (`api/sos/search.py`, `460cd3a` and `f6d63ad`). It is gated on confirmed care intent. Each piece is
a module switch, and `lab.py` can switch each one off:

| piece | switch | what it does |
|---|---|---|
| condition retrieval | `INJURY_RETRIEVAL` | Adds a condition-only keyword query beside the full query, for the box's own passages and for the documents. Adds every card that mentions the condition, however low bm25 puts it. |
| weighted coverage | `INJURY_WEIGHTING` | Rows are sorted and scored on how much of the injury they carry, not on equal-weight term share. Weights: condition 4, place 1, qualifier 0.5, and each other query word ("adder", "stove") 1. |
| card subjects | `INJURY_SUBJECTS` | A card's curated `conditions`, not its warnings, say what it is about. Broken bones mentions a wound but is not a wound card. A card with no injury subject (Anaphylaxis, Shock) is judged by its own words. |
| promotion | `INJURY_PROMOTION` | The strongest card for the condition goes first and a second one sits inside `KEPT_TOP`. This runs outside the meaning layer, so it works with embeddings absent. Cards are ordered by (query condition and card main subject, longest of the card's own aliases found in the query, coverage, score). No other card is kept for an injury query. |
| evidence penalty | `MEDICAL_UNSUPPORTED_FACTOR` = 0.25 | Applies to a row with no evidence of the condition itself: only the body word, or an ambiguous spelling with nothing medical beside it (Sam Gash, Olympic Arms, a bicycle forum "bleeding" brakes). The row is multiplied down, not dropped. There is no blacklist. |

The search counts a confirmed injury as medical intent: it applies `MEDICAL_BOOST` and gives no Wikipedia lift. The
result-cache key version is now 3.

## 2. Where I departed from Codex, and why

- **"Other words" count in the weighted coverage.** Codex's formula counts condition, location and modifier only.
  Measured, that dropped "what should I do after an adder bite" from 1st to 10th in keyword-only mode: "adder" was
  worth nothing, and the "Ticks and adders" page's title stopped counting. Each remaining query word now counts
  like a place.
- **A card without curated subjects is judged by its text.** It is not treated as incidental. Codex says a card's
  subject comes from metadata. Applied to cards with no metadata, "throat swelling up after a wasp sting and hives
  everywhere, do I use the epipen" put the Anaphylaxis card 21st (it was 2nd). Only a card whose curated subject is
  another injury (Broken bones for a wound) is penalised.
- **The policy stands aside in two cases** (not in Codex):
  - A graver emergency appears beside the injury: anaphylaxis, epipen, not breathing, unconscious, seizure. That
    fixed the Anaphylaxis case above.
  - An adder or tick bite. The Bites and stings card sends both to the "Ticks and adders" page, so leading with
    the card would contradict it.
- **The box's own authored content and the medical library count an ambiguous word without a medical word beside
  it.** "Power cut" is already removed as a phrase. External rows still need context. Without this, the "Ticks and
  adders" page was penalised for "bite".
- **No bare `cut` in condition retrieval.** In this library "cut" is a power cut far more often than a wound, so
  only the phrases "a cut", "the cut", "deep cut" and "cuts and grazes" are asked for.
- **No `ConditionEvidence` dataclass with six fields.** The evidence is a set of conditions per row, plus weighted
  coverage, plus the promotion tuple. That gives the same ordering guarantee with less state.
- **Rows the meaning layer added are not penalised.** Their own floor is already their evidence gate.
- **No aliases in the dense representation.** That needs re-embedding and belongs with priority 4, which was not
  done.
- **Medicines.** For an injury query the kept cards are the injury cards, and medicine pages are kept beside them
  by the existing `_keep_rows`. The old blanket `[] if medicines else card_pages` rule only covers the non-injury
  path now.
- **`INJURY_CARDS_KEPT` stays 2**, as Codex said. Keeping 3 was measured neutral on every gold set and would put
  Severe bleeding 3rd rather than 8th for "gash on arm". It is a one-constant change if the owner wants it.

## 3. Ablation: what each piece does

This is a replay of the gold sets (the aggregate guardrails) and of the three required queries. It uses meaning on;
keyword-only gives the same outcomes for these queries. Wound cards are Severe bleeding, Wound cleaning and Closing a
wound.

| experiment | gash on arm: wound cards at | Broken bones at | noise in top 10 | spilled boiling water: top 3 | injury-fresh h@1 / h@3 | para MRR |
|---|---|---|---|---|---|---|
| before (`INJURY_INTENT` off) | 26, 32, 36 | **2** | Sam Gash @3, football glossary @10 | Butchery, Broken bones, Heat stroke | 0.864 / 0.864 | 0.498 |
| **all on (control)** | **1, 2, 8** | not in top 40 | none | **Burns**, Where There Is No Doctor, Shock | **0.955 / 1.000** | **0.509** |
| retrieval only | 12, 20, 27 | **1** | Sam Gash @7, glossary @8 | Broken bones, … | 0.864 / 0.864 | 0.498 |
| retrieval + promotion | 1, 3, 27 | 2 | Sam Gash @9, glossary @10 | Burns, Broken bones, … | 0.955 / 1.000 | 0.509 |
| no retrieval | 1, 2, 8 | — | none | Burns, Shock, … | 0.955 / 1.000 | 0.509 |
| no weighting | 1, 3, 11 | 17 | none | Burns, Heat stroke, … | 0.955 / 1.000 | 0.509 |
| no card subjects | 1, 2, 13 | **8** (above Severe bleeding) | none | Burns, …, Wound cleaning | 0.955 / 1.000 | 0.509 |
| no promotion | 1, 2, 8 | — | none | Burns, …, Heat stroke (3rd, meaning on) | 0.955 / 1.000 | 0.509 |
| no evidence penalty | 1, 2, 9 | — | glossary @7 | Burns, "Menstrual cup", … | 0.955 / 1.000 | 0.509 |
| no alias index | 1, 2, 8 | — | none | Burns, … | 0.955 / 1.000 | 0.507 |

Reading the table:

- **Condition retrieval alone is Codex's warning, measured.** With retrieval on and nothing else, Broken bones goes
  from 2nd to 1st.
- **Promotion without subjects and weighting protects the wrong neighbours.** Broken bones stays 2nd, between the
  wound cards.
- **Subjects are what keep Broken bones below the wound cards.** Without them it is 8th, above Severe bleeding at
  13th.
- **The penalty is what keeps the football glossary out of the top 10.**
- **Weighting is what keeps Heat stroke out of "spilled boiling water".**
- **Two pieces showed no effect here:**
  - Condition retrieval, because task 24's OR fallback (`FTS_OR_BELOW` 10) already brings the wound cards in for
    these queries.
  - The alias index, because task 24's `SYNONYMS["gash"]` and the cards' own words already carry these queries.
  Both are kept: condition retrieval is the route that does not depend on the OR fallback firing, and aliases are
  the curated route. By these measurements, though, neither is load-bearing on today's sets.
- **The aggregate guardrails do not tell the pieces apart.** Weighting, subjects, promotion and the penalty each
  largely compensate for the others. Only the per-query view above shows what each one does.

Latency, replayed one query at a time, p50 of search's own compute:

| queries | meaning on (main → branch) | keyword only (main → branch) |
|---|---|---|
| all 245 | 87.7 → 98.4 ms (+10.7) | 66.9 → 71.2 ms (+4.3) |
| the 28 confirmed injury queries | 67.0 → 107.0 ms (+40.0) | 48.1 → 85.0 ms (+36.9) |
| the rest | +6.3 ms | +1.6 ms |

Both medians are inside the +50 ms budget. An earlier draft ran at +52 ms on injury queries. Two changes brought it
down: the nonmedical phrases became one compiled pattern, and each row's words are tokenised once.

## 4. Guardrails, before → after

"Before" is `main`'s own code on its own (pre-reindex) database. "After" is this branch on the reindexed database.
Both are replays of the same fresh recording.

| guardrail | required | main | this branch |
|---|---|---:|---:|
| safety/plain in the top 3 | 17/17 | 17/17 | **17/17** |
| safety/hard in the top 3 | 16/17 | 16/17 | **16/17** |
| own-library hit@3 | ≥ 0.873 | 0.873 | **0.873** |
| own-library/health hit@3 | 1.000 | 1.000 | **1.000** |
| wikipedia hit@1 | ≥ 0.395 | 0.419 | **0.419** |
| paraphrase MRR | ≥ 0.500 | 0.497 | **0.509** |
| heldout-2026-09-21 MRR | ≥ 0.681 | 0.681 (0.6806) | **0.681** (0 queries differ) |
| books/survivor hit@10 | ≥ 0.714 | 0.714 | **0.714** |
| books-extra hit@10 | ≥ 0.776 | **0.759** | **0.759** (0 queries differ) |
| injury-fresh hit@1 / hit@3 | no passing query regresses | 0.864 / 0.864 | **0.955 / 1.000** |
| injury-fresh, keyword only | — | 0.500 / 0.591 | 0.682 / 0.773 |
| safety/hard, keyword only | — | 10/17 | 12/17 |

On this fresh recording, **main itself** measures books-extra hit@10 at 0.759, not the documented 0.776, and
paraphrase MRR at 0.497, not 0.500. The live Kiwix and embedding answers have drifted since task 24's recording.
This branch leaves books-extra exactly where main is (per query) and lifts paraphrase MRR to 0.509.

No gold query anywhere ranks lower than on main. The 12 that moved all moved up:

- gash on arm 26 → 1
- deep cut leg 14 → 2
- spilled boiling water on my leg miss → 1
- kettle over the kid's hand 2 → 1
- spilled the boiling kettle on my arm 3 → 1
- blood soaking through the bandage 3 → 1
- forearm bent on the trampoline 5 → 3
- concussion 7 → 5
- sprained ankle 22 → 16
- three book rows outside the top 10, which also moved up

The fixed alternating halves agree. On the tune half, paraphrase MRR goes 0.474 → 0.495 and safety MRR
0.775 → 0.804. The check half is identical to `injury-off`. None of the 22 injury-fresh rows regressed:

| query | main | branch |
|---|---:|---:|
| inj-01 gash on arm | 26 | 1 |
| inj-04 deep cut leg | 14 | 2 |
| inj-06 spilled boiling water on my leg | — | 1 |

The other 19 were already in the top 3 and still are. inj-04 is 2nd under its strict gold (Severe bleeding or Wound
cleaning): Closing a wound leads, because its alias "deep cut" is the query's own phrase. I did not change `inj-04`'s
gold to count it.

The required outcomes, live:

- **gash on arm**: a wound card is first, and Broken bones is below all three wound cards (it is not in the top 10).
- **deep cut leg**: a wound card is in the top 3 (Closing a wound, then Wound cleaning).
- **spilled boiling water on my leg**: Burns is first.
- **gash on arm, noise**: Sam Gash, Olympic Arms, the football glossary and the bicycle-brake question are not in
  the top 10.
- **Sam Gash**: the biography is still first.
- **With the embedding server unreachable**: the same four answers (§5).

Full backend suite: **1,919 passed** (main: 1,816). `sos validate-playbooks --all-scenarios`: OK, 131 documents.

## 5. The held-out set, run once

I recorded it once, live, with main's code, then replayed it with main and with this branch. The policy was frozen
at `460cd3a` when this ran, and I changed nothing after looking. `f6d63ad` came after the run and changes speed
only: I replayed again to check that every held-out and gold query keeps its rank. The only difference is which
section of a promoted card is shown, now usually "When to use", the row that carries the aliases.

| group | mode | main h@1 / h@3 / MRR | branch h@1 / h@3 / MRR |
|---|---|---|---|
| injury (33) | meaning on | 0.758 / 0.818 / 0.790 | **0.970 / 1.000 / 0.985** |
| injury (33) | keyword only | 0.636 / 0.697 / 0.674 | **0.970 / 1.000 / 0.985** |
| contrast (13) | meaning on | 0.385 / 0.538 / 0.499 | 0.385 / 0.538 / 0.499 (identical ranks) |
| contrast (13) | keyword only | 0.231 / 0.385 / 0.327 | identical |

Injury rows that moved up:

- slashed hand on broken glass 36 → 1
- grazed knee from falling off bike 16 → 1
- touched the iron and burnt my fingers miss → 1
- toddler pulled a cup of hot tea onto himself miss → 1
- rolled my ankle playing football miss → 1
- deep laceration on the forearm 3 → 1
- puncture wound from a rusty nail in foot 4 → 1
- cut my finger chopping onions 2 → 1

**One injury row moved down: "cut on forehead gaping open", 1 → 2.** Wound cleaning's alias "cut" matches, while
Closing a wound's "gaping cut" does not, because the words are apart in the query. Closing a wound is now 2nd.

None of the 13 contrasts is read as an injury. "A book about treating gunshot wounds" has a condition but book
purpose, so it is not confirmed. Every contrast's expected-page rank is unchanged. Top-10 lists differ from main only
in which section of a card is shown, the aliases row.

## 6. Live, at `f6d63ad`

My own API ran on :8100 against a copy of the dev state, reindexed with `sos index`, sharing Kiwix :8090 and the
embedding server :8091 read-only. I then started a second instance on :8101 with the embedding URL pointed at a
closed port. Both were stopped by PID afterwards.

**gash on arm** (main at :8000, for comparison: The essentials printed, **Broken bones**, **Sam Gash**, Falling
(accident), Where There Is No Doctor, Spinal injury, CD3WD, FM 4-25.11, Boy Scouts Handbook, football glossary):

1. Wound cleaning (card)
2. Closing a wound (card)
3. Falling (accident) (MDWiki)
4. Where There Is No Doctor p.131
5. FM 4-25.11 First Aid p.136
6. FM 4-25.11 First Aid p.46
7. Survival and Austere Medicine p.88
8. Severe bleeding (card)
9. Emergency War Surgery p.605
10. Emergency War Surgery p.89

**deep cut leg:**

1. Closing a wound (card)
2. Wound cleaning (card)
3. Emergency War Surgery p.368
4. MedlinePlus "Leg lengthening"
5. Survival and Austere Medicine p.501
6. Emergency War Surgery p.519
7. CD3WD health page
8. MDWiki "Fascial compartment"
9. Where There Is No Doctor p.139
10. Shock (card)

**spilled boiling water on my leg:**

1. Burns and scalds (card)
2. Where There Is No Doctor p.455
3. Shock (card)
4. Where There Is No Doctor p.146
5. Camping and Woodcraft p.332
6. The essentials, printed
7. Ship Captain's Medical Guide ch.4
8. Boy Scouts Handbook p.79
9. Making things again
10. Ship Captain's Medical Guide ch.1

**Sam Gash:**

1. Sam Gash (Wikipedia)
2. Wound cleaning (card)
3. Closing a wound (card)
4. Gash (EP)
5. Survival and Austere Medicine p.54
6. Severe bleeding (card)
7. MDWiki "Gaseous signaling molecules"
8. The Book of Woodcraft p.373
9. Dark Island (album)
10. MDWiki "Physician writer"

**With the embedding server unreachable**, all four top-10 lists are the same, except that one card section differs
("deep cut leg" shows Closing a wound's "When to use"). One live call for "gash on arm" took 386 ms (341 ms inside search) and 228 ms
with no embedding server.

**Priority 4 (card-only dense index) was not done.** Every required outcome is met with the keyword path alone.
Building it would mean writing a new collection into `/home/dan/sos-content/embeddings`, which the running `main`
stack shares, and adding record and replay support for a new call. That is a separate task.

## 7. Honest concerns

1. **The held-out set is not independent of the rules.** I wrote it, then wrote `analyse_injury` in the same
   session, with those phrasings in mind. Some rules may be shaped by them: "bit" plus an animal, "bone sticking
   out", hot tea "onto himself". The 0.97 held-out hit@1 is an upper bound, not a clean estimate. The contrast
   result (no injury read, ranks identical) is the more trustworthy half.
2. **The analyser is a hand-written rule set.** It will miss wordings nobody wrote a rule for. "Spurting red
   everywhere from a cut, what do I press on" is only "possible", because it has no body part and no bleed word.
   It will also misfire now and then: "a Yankee is knocked out and wakes up…", a novel's plot, reads as a head
   injury (a book row outside the top 10 moved 21 → 17). When the analysis misses, the search is exactly main's.
   When it misfires, a card is promoted.
3. **Most pieces are redundant on today's gold.** Condition retrieval and the alias index showed no measurable
   effect on any set. Their value is structural (they do not rely on the OR fallback or on `SYNONYMS`), and that is
   unproven.
4. **"Sam Gash" still shows the wound cards at 2, 3 and 6.** That comes from task 24's `SYNONYMS["gash"]` and the OR
   fallback, and main does the same. The biography leads, as required. Expanding "gash" only for a confirmed injury
   would be a small follow-up.
5. **Severe bleeding is 8th for "gash on arm"**, behind first-aid manual pages. Keeping 3 cards
   (`INJURY_CARDS_KEPT = 3`) was neutral on every set and puts it 3rd. I left it at Codex's 2 for the owner to
   decide.
6. **`lab.py`'s `before` experiment is not bit-identical to main.** The new aliases column changes FTS5's
   document-length statistics, and 2 of 603 queries differ. That is why the "before" column in §4 comes from
   main's own code on its own database.
7. **The aliases column is also searched by the AI assistant's retrieval** (`ai.py` gives it bm25's default weight,
   1). Its tests pass, but it was not measured separately.
8. **On first start the migration copies the 21,681-row `fts_docs` into a new table.** That takes seconds on the PC
   and was not timed on the Pi. The aliases stay empty until `sos index` runs.
9. **Injury queries cost about 40 ms more at p50** (whole-set median +10.7 ms). Most of it is the two extra
   condition queries and reading every candidate's body. It was not measured on the Pi.
