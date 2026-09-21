# Search baseline, 2026-09-20

The first measurement of Operation SOS search with a ruler: 523 hand-written gold queries in five sets
(`tools/eval/search/`) run through `sos.search.search()` (the call the API makes) keyword-only (`semantic=None`) and
with the meaning layer on (`Semantic`, as `main.py` builds it). Code under test: `search-accuracy` at `7b32096`
(clean tree). Raw run: `tools/eval/search/baseline-2026-09-20.json` (`sos eval-compare` reads it; rankings are trimmed to 5 rows,
3 when the answer is first, plus the answer row). The run finished just after midnight, so the file's `meta.date` says
2026-09-21.

Reproduce: start `kiwix-serve` and `llama-server --embedding` as `dev/run-dev.sh` does, then
`SOS_DEV=1 SOS_CORE=/home/dan/sos-content SOS_STATE=/home/dan/OperationSOS/.dev/state SOS_EXT=/home/dan/OperationSOS/.dev/extended SOS_MANIFEST_DIR=/home/dan/OperationSOS/.dev/full-manifest SOS_PLAYBOOKS_DIR=/home/dan/OperationSOS/playbooks sos eval-search --compact --json out.json`.
A second full run reproduced every one of the 1,046 ranks exactly, so the ruler is deterministic; only latency moves.

## Read this first: two things about the run

1. **Every one of the 1,046 searches came back `partial`, and that is a defect in the dev box, not noise.** The `survival`
   class (ready.gov, Appropedia, TruePrepper, CD3WD, WikiCiv, GrimGrains, Energypedia, Low-tech Magazine, two cooking sites)
   is asked as one Kiwix request, and Kiwix answers HTTP 400 because `solar.lowtechmagazine.com_mul_all` is a multilingual
   ZIM (library.xml: `eng,fra,deu,…`) while the dev database's `zim_languages` setting records it as `eng`. The other eight
   class groups answer. So today's baseline has **no keyword hits from those ten sources at all**. Any keyword-recall
   improvement that merely repairs this will show up as a large gain and is not a search-quality gain. The harness retries a
   partial answer up to three times, then stops retrying once three queries in a row stay partial (it did, after the first
   three), and records `partial` on every row. I did not touch the database or the code under test.
2. **`books` is measured in one mixed list.** Books are weighted 0.6 and shown as their own group in the app, so they sit
   low in a mixed ranking by design. As a control, the exact titles score keyword rank 13 (Moby Dick), 17 (Pride and
   Prejudice), 27 (Treasure Island), 14 (Hound of the Baskervilles), 22 (Wind in the Willows) and meaning rank 8, 4, 3, 3, 2.
   The `books` figures are therefore a rank-in-the-whole-page figure, harsh for keyword search by construction. They
   still separate meaning from keyword cleanly, because that difference is the point.

Latency (dev PC, warm Kiwix, one query at a time): median about 1.3 s keyword and 1.4 s with meaning (about +40 ms), p95
1.6 s to 1.7 s; the slowest single search was 4.4 s. Most of the 1.3 s is Kiwix full-text over the large ZIMs.

## Headline

| set | n | search | hit@1 | hit@3 | hit@5 | hit@10 | MRR@10 | nDCG@10 | p50 ms | p95 ms |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|
| own-library | 63 | keyword | 0.619 | 0.778 | 0.810 | 0.873 | 0.693 | 0.736 | 1327 | 1657 |
| own-library | 63 | meaning | 0.651 | 0.698 | 0.810 | 0.857 | 0.706 | 0.742 | 1389 | 1653 |
| paraphrase | 126 | keyword | 0.254 | 0.349 | 0.429 | 0.532 | 0.326 | 0.374 | 1321 | 1436 |
| paraphrase | 126 | meaning | 0.325 | 0.532 | 0.603 | 0.627 | 0.442 | 0.487 | 1353 | 1481 |
| safety | 34 | keyword | 0.559 | 0.765 | 0.794 | 0.882 | 0.667 | 0.719 | 1308 | 1593 |
| safety | 34 | meaning | 0.735 | 0.853 | 0.941 | 0.941 | 0.808 | 0.841 | 1359 | 1707 |
| safety/plain | 17 | keyword | 0.824 | 0.941 | 0.941 | 1.000 | 0.882 | 0.911 | 1374 | 1733 |
| safety/plain | 17 | meaning | 0.941 | 1.000 | 1.000 | 1.000 | 0.971 | 0.978 | 1396 | 1737 |
| safety/hard | 17 | keyword | 0.294 | 0.588 | 0.647 | 0.765 | 0.451 | 0.527 | 1298 | 1540 |
| safety/hard | 17 | meaning | 0.529 | 0.706 | 0.882 | 0.882 | 0.646 | 0.704 | 1332 | 1514 |
| books | 214 | keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1347 | 2121 |
| books | 214 | meaning | 0.000 | 0.009 | 0.019 | 0.117 | 0.017 | 0.039 | 1377 | 2601 |
| books/gutenberg | 151 | keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1348 | 2305 |
| books/gutenberg | 151 | meaning | 0.000 | 0.007 | 0.013 | 0.040 | 0.007 | 0.014 | 1373 | 2888 |
| books/survivor | 63 | keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1343 | 1564 |
| books/survivor | 63 | meaning | 0.000 | 0.016 | 0.032 | 0.302 | 0.042 | 0.099 | 1390 | 1604 |
| wikipedia | 86 | keyword | 0.186 | 0.326 | 0.360 | 0.500 | 0.276 | 0.328 | 1318 | 1505 |
| wikipedia | 86 | meaning | 0.128 | 0.314 | 0.337 | 0.500 | 0.231 | 0.294 | 1361 | 1539 |
| wikipedia/question | 18 | keyword | 0.111 | 0.278 | 0.333 | 0.500 | 0.210 | 0.278 | 1403 | 1763 |
| wikipedia/question | 18 | meaning | 0.000 | 0.222 | 0.278 | 0.389 | 0.110 | 0.176 | 1418 | 1755 |
| wikipedia/term | 68 | keyword | 0.206 | 0.338 | 0.368 | 0.500 | 0.293 | 0.341 | 1302 | 1484 |
| wikipedia/term | 68 | meaning | 0.162 | 0.338 | 0.353 | 0.529 | 0.263 | 0.325 | 1340 | 1514 |
| ALL | 523 | keyword | 0.203 | 0.281 | 0.312 | 0.373 | 0.251 | 0.279 | 1330 | 1616 |
| ALL | 523 | meaning | 0.226 | 0.323 | 0.367 | 0.446 | 0.289 | 0.326 | 1367 | 1682 |

Sub-groups of the first two sets:

| set | n | search | hit@1 | hit@3 | hit@5 | hit@10 | MRR@10 | nDCG@10 | p50 ms | p95 ms |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|
| own-library/answer | 51 | keyword | 0.608 | 0.725 | 0.765 | 0.843 | 0.673 | 0.713 | 1325 | 1569 |
| own-library/answer | 51 | meaning | 0.667 | 0.725 | 0.804 | 0.824 | 0.714 | 0.741 | 1389 | 1574 |
| own-library/health | 12 | keyword | 0.667 | 1.000 | 1.000 | 1.000 | 0.778 | 0.833 | 1355 | 1930 |
| own-library/health | 12 | meaning | 0.583 | 0.583 | 0.833 | 1.000 | 0.670 | 0.747 | 1397 | 1972 |
| paraphrase/answer | 102 | keyword | 0.275 | 0.373 | 0.461 | 0.559 | 0.349 | 0.398 | 1323 | 1436 |
| paraphrase/answer | 102 | meaning | 0.353 | 0.559 | 0.627 | 0.647 | 0.468 | 0.512 | 1362 | 1481 |
| paraphrase/health | 24 | keyword | 0.167 | 0.250 | 0.292 | 0.417 | 0.226 | 0.270 | 1281 | 1397 |
| paraphrase/health | 24 | meaning | 0.208 | 0.417 | 0.500 | 0.542 | 0.330 | 0.382 | 1308 | 1416 |

`hit@k`: the answer is in the top k. MRR and nDCG use the first matching result (definitions in
`tools/eval/search/README.md`). `own-library` and `safety` have expected pages the box owns; `wikipedia` demands the
article in `wikipedia_en_all_maxi` specifically.

## What the numbers say

**Where meaning search helps.**
- Paraphrases (the set built to measure it): hit@3 0.349 -> 0.532, hit@10 0.532 -> 0.627, MRR 0.326 -> 0.442. Of the
  126, 15 reach the top ten only with meaning and 3 fall out of it. Among rows both
  modes find, 29 improve and 12 worsen.
- Safety: hit@1 0.559 -> 0.735 overall and 0.294 -> 0.529 for the hard paraphrases; hit@3 0.765 -> 0.853.
- Survivor Library books, which keyword search cannot return at all (its keyword hits are the site's index pages, never the
  PDFs): 0 -> 0.302 hit@10 (19 of 63 topics), and 25 of the 47 rescued queries are books.
- Colloquial symptom wording: "child struggling to breathe with a tight chest" 15 -> 1,
  "overheated after running in a heatwave" 25 -> 2, "anaphalactic shock after eating peanuts" absent -> 4.

**Where it hurts.**
- **Wikipedia lookup gets worse.** hit@1 0.186 -> 0.128, MRR 0.276 -> 0.231, and for question-shaped queries hit@1 0.111 -> 0.000.
  Among the 57 targets found in both modes, 27 move down and 10 move up. The meaning layer adds authored pages and document
  passages that outrank the Wikipedia row, and the Wikipedia rerank (a 0.7x to 1.3x rescale of its own hits) does not
  win that back. A same-title lenient count (the article from any English Wikipedia ZIM: maxi, medicine, simple, mini),
  computed from the full top ten of an untrimmed twin of this run, is hit@1 0.326 -> 0.221 and hit@10 0.674 -> 0.628.
  Only 4 Wikipedia rows are rescued and 4 regress out of the top ten.
- **Medicine names.** own-library health hit@3 1.000 -> 0.583: for "paracetamol", "amoxicillin", "salbutamol inhaler" and
  the questions about doses, meaning inserts Where There Is No Doctor and Survival and Austere Medicine passages ahead
  of the NHS medicine page (paracetamol 3 -> 8, "how much paracetamol can an adult take" 1 -> 5, "what infections does
  amoxicillin treat" 1 -> 4, salbutamol inhaler 1 -> 4). own-library overall hit@3 0.778 -> 0.698.
- Wild mushrooms and bats/rabies drop out of the top ten (rank 9 -> 16, 10 -> 11).

**Where neither helps.**
- Gutenberg descriptions: 0 of 151 in the top five by keyword, 2 of 151 with meaning, 6 in the top ten. The household
  vector is a book's title and opening text, and a plot description without the title lands on unrelated books. Only
  Sun Tzu, Marcus Aurelius, Amundsen, Einstein, Gibbon and Lorna Doone reach the top ten.
- The NHS medicines pages are never found from a paraphrase: the 18 paraphrases whose only accepted answer is an
  `nhs_medicines` page (doses, Imodium, Nurofen, amoxicillin, the blue puffer) are absent from the first 40 results in both modes,
  although the same pages are found from the bare drug name. And the general-knowledge Wikipedia paraphrases
  (HIV, alcohol withdrawal, rabies from a bat, foxes, insects, rain, viruses) are absent in both.
- 6 own-library and 39 paraphrase queries are found by neither mode.

**Safety guard.** The box's own card is in the top three for 29 of 34 queries with meaning on
(26 of 34 keyword-only). All 17 plain wordings are in the top three with meaning on. **Five hard paraphrases miss the top
three, so the guard set does not pass today:**

| id | query | keyword rank | meaning rank |
|---|---|--:|--:|
| `safety-cpr-child-hard` | my baby has gone limp and stopped breathing | 1 | 4 |
| `safety-hypothermia-hard` | hes been out in the freezing rain for hours and is shivering hard and now confused and sleepy | 4 | 5 |
| `safety-burns-hard` | kettle of boiling water went over my kids hand and the skin is blistering | absent | 13 |
| `safety-seizures-hard` | man on the pavement is convulsing and foaming at the mouth | absent | absent |
| `safety-heat-stroke-hard` | old man collapsed in the heatwave with boiling hot dry skin and confused | 24 | 5 |

Note `safety-cpr-child-hard`: keyword search has the child CPR card first and meaning pushes it to fourth, a regression on a
guard row.

(Keyword-only additionally misses `safety-severe-bleeding-hard` at 7, `safety-cpr-adult-hard` at 9,
`safety-carbon-monoxide-hard` at 13 and `safety-seizures-plain` at 6, all of which meaning fixes.) The seizure card is
never found from "man on the pavement is convulsing and foaming at the mouth", and "kettle of boiling water went over
my kids hand" reaches the burns card only at 13 with meaning, absent without it.

## Rescued and regressed by the meaning layer

47 queries newly in the top ten, 9 newly out of it. Rescued by set: books 25, own-library 1, paraphrase 15, safety 2, wikipedia 4.
Regressed by set: own-library 2, paraphrase 3, wikipedia 4.

**Regressed** (keyword rank -> meaning rank):

- `own-a14`: 10 -> 11: do bats in the UK carry rabies
- `own-a16`: 9 -> 16: how do I tell if a wild mushroom is poisonous
- `para-a02-1`: 10 -> 14: kettle on the camping stove, how many minutes does it need to bubble before its ok to sip
- `para-a25-2`: 8 -> 20: who do I ring to find out if our area is going to be under water tonight
- `para-h04-1`: 8 -> 15: hypothermea, body temp dropping after hours out in the cold
- `wiki-chlorination-of-drinking-water`: 8 -> 13: chlorination of drinking water
- `wiki-how-does-a-heat-pump-work`: 10 -> 13: how does a heat pump work
- `wiki-how-to-tie-a-bowline`: 7 -> 12: how to tie a bowline
- `wiki-paracetamol-overdose`: 10 -> 13: paracetamol overdose

**Rescued** (keyword rank -> meaning rank; the 25 books rows are in the run file and abbreviated here):

- `own-a02`: absent -> 4: how long do I need to boil water to make it safe
- `para-a03-2`: 23 -> 4: how many capfuls of thin household Domestos in a 10L bucket of roof rainwater to sterilise it
- `para-a16-2`: 36 -> 5: which fungi are deadly, is there a test like peeling the skin or a silver spoon
- `para-a27-2`: absent -> 2: when do you swallow the pills that stop your neck gland soaking up radioactive stuff
- `para-a33-2`: absent -> 9: spurting red everywhere from a cut, what do I press on
- `para-a34-1`: 17 -> 1: my friend has food lodged in his windpipe and can't speak, going blue
- `para-a35-1`: absent -> 2: man's collapsed not breathing, how many pushes on the chest and how fast
- `para-a41-2`: absent -> 3: hobbyist transmitters in Britain, which chunks of the airwaves do they get
- `para-a47-1`: 12 -> 2: will my ice cream and peas be ruined if the electricity stays off for a day
- `para-a48-2`: absent -> 4: evacuation bag checklist for the family
- `para-a54-2`: 15 -> 1: child struggling to breathe with a tight chest at night and the reliever has run out
- `para-a55-2`: 15 -> 1: what illness follows a big dose of radioactivity, nausea and the runs
- `para-h06-2`: absent -> 4: anaphalactic shock after eating peanuts, can't breathe, what do I do
- `para-h10-1`: absent -> 3: swallowed wrongly and turning purple
- `para-h10-2`: absent -> 5: gasping with a bit of sausage lodged
- `para-h12-2`: 25 -> 2: overheated after running in a heatwave and stopped sweating
- `safety-carbon-monoxide-hard`: 13 -> 3: we all have headaches and feel sick since the boiler was fixed and the alarm is beeping
- `safety-heat-stroke-hard`: 24 -> 5: old man collapsed in the heatwave with boiling hot dry skin and confused
- `wiki-electromagnetic-pulse`: absent -> 2: electromagnetic pulse
- `wiki-ibuprofen`: 24 -> 3: ibuprofen
- `wiki-oral-rehydration-salts`: absent -> 9: oral rehydration salts
- `wiki-pmr446-walkie-talkies`: 11 -> 10: PMR446 walkie talkies
- 25 books rows: 6 Gutenberg (`book-gut-132`, `-2680`, `-3414`, `-5001`, `-731`, `-840`) and 19 Survivor Library topics (boring a well, catching trout, curing bacon, dressmaking, distilling, drying food, dyeing, herbal remedies,
  trapping, bricklaying, cheese, prospecting, angora goats, surveying, freezing weather, sick horses, baskets, hand looms, windmills), all absent
  without meaning.

## The ten worst per set (meaning on)

Ranked by meaning rank, then keyword rank; "returned" is the first three results of the meaning run. Where more than ten are
absent the choice among them is by id, so the list shows kinds of failure, not a ranking of severity.

### own-library
- `own-a06` (keyword absent, meaning absent): can I take ibuprofen and paracetamol together  
  returned: Toothache and dental abscess; Survival and Austere Medicine, 3rd; Medical
- `own-a12` (keyword absent, meaning absent): what happens when a heavy drinker stops drinking alcohol suddenly  
  returned: Chronic conditions; Ship Captain's Medical Guide, chap; Where There Is No Doctor (Hesperia
- `own-a13` (keyword absent, meaning absent): can you eat beetles and other insects  
  returned: FM 3-05.70 Survival (US Army, 2002; FM 21-76 Survival (US Army, 1992); Food storage
- `own-a15` (keyword absent, meaning absent): are urban foxes dangerous to people  
  returned: Civil unrest and breakdown of orde; Solar superstorm; Nuclear War Survival Skills (Kearn
- `own-a17` (keyword absent, meaning absent): how does rain form  
  returned: Field craft in Britain; OpenStax Concepts of Biology; Reading the weather and exposure
- `own-a18` (keyword absent, meaning absent): what is a virus and how does it spread  
  returned: Where There Is No Doctor (Hesperia; OpenStax Microbiology; OpenStax Concepts of Biology
- `own-a16` (keyword 9, meaning 16): how do I tell if a wild mushroom is poisonous  
  returned: Wild food in Britain and Ireland; FM 3-05.70 Survival (US Army, 2002; ATP 3-50.21 Survival (US Army, 201
- `own-a11` (keyword 11, meaning 13): how is HIV passed from one person to another  
  returned: Where There Is No Doctor (Hesperia; OpenStax Microbiology; OpenStax Microbiology
- `own-a14` (keyword 10, meaning 11): do bats in the UK carry rabies  
  returned: Bites and stings; FM 3-05.70 Survival (US Army, 2002; Survival and Austere Medicine, 3rd
- `own-h01` (keyword 3, meaning 8): paracetamol  
  returned: Paracetamol; Lethal pandemic; Survival and Austere Medicine, 3rd

### paraphrase
- `para-a05-1` (keyword absent, meaning absent): biggest number of those white pain tablets I can swallow in 24 hours, I'm 40  
  returned: Medical; Toothache and dental abscess; Where There Is No Doctor (Hesperia
- `para-a05-2` (keyword absent, meaning absent): whats the safe limit for painkillers from the chemist, I've got flu and a bad back  
  returned: Lethal pandemic; Chronic conditions; Mass-casualty terrorism
- `para-a06-1` (keyword absent, meaning absent): can I double up on two different headache pills at once or will it hurt me  
  returned: Head injury; Where There Is No Doctor (Hesperia; Chronic conditions
- `para-a06-2` (keyword absent, meaning absent): Nurofen and Panadol on the same day, is that ok or dangerous  
  returned: Chronic conditions; Volcanic ash and gas; Poisoning and overdose
- `para-a07-1` (keyword absent, meaning absent): Immodium, what's it for and when shouldn't I take it  
  returned: Fishing and the shore; Moving across country; Radiation
- `para-a07-2` (keyword absent, meaning absent): tablets from the chemist to stop the runs, what are they actually for  
  returned: Chronic conditions; Medicine without industry; Survival and Austere Medicine, 3rd
- `para-a08-1` (keyword absent, meaning absent): the kids have got the runs really badly and we can't get to the surgery, what helps  
  returned: Choking; Getting help without phones; Where There Is No Doctor (Hesperia
- `para-a10-1` (keyword absent, meaning absent): what is that penicillin type antibiotic from the GP for chest bugs and tooth abscesses  
  returned: Toothache and dental abscess; Survival and Austere Medicine, 3rd; Survival and Austere Medicine, 3rd
- `para-a10-2` (keyword absent, meaning absent): doctor gave me capsules for a chest infection and a gum abscess, what are they meant to clear up  
  returned: Toothache and dental abscess; Where There Is No Doctor (Hesperia; Sepsis
- `para-a11-1` (keyword absent, meaning absent): can you catch the aids virus from kissing or sharing a cup  
  returned: Where There Is No Doctor (Hesperia; Where There Is No Doctor (Hesperia; Infant feeding

### safety
- `safety-seizures-hard` (keyword absent, meaning absent): man on the pavement is convulsing and foaming at the mouth  
  returned: Fever in a child; Where There Is No Doctor (Hesperia; Ship Captain's Medical Guide, chap
- `safety-burns-hard` (keyword absent, meaning 13): kettle of boiling water went over my kids hand and the skin is blistering  
  returned: Childbirth; Where There Is No Doctor (Hesperia; Water
- `safety-heat-stroke-hard` (keyword 24, meaning 5): old man collapsed in the heatwave with boiling hot dry skin and confused  
  returned: Reading the weather and exposure; FM 4-25.11 First Aid (US Army, 200; Where There Is No Doctor (Hesperia
- `safety-hypothermia-hard` (keyword 4, meaning 5): hes been out in the freezing rain for hours and is shivering hard and now confused and sleepy  
  returned: Prolonged severe winter; Sepsis; Fever in a child
- `safety-cpr-child-hard` (keyword 1, meaning 4): my baby has gone limp and stopped breathing  
  returned: Infant feeding; Where There Is No Doctor (Hesperia; Childbirth
- `safety-carbon-monoxide-hard` (keyword 13, meaning 3): we all have headaches and feel sick since the boiler was fixed and the alarm is beeping  
  returned: Shelter and heat; Head injury; Carbon monoxide
- `safety-cpr-adult-hard` (keyword 9, meaning 2): he just dropped down and isnt breathing and has no pulse what do i do  
  returned: Shock; CPR, adult; Survival and Austere Medicine, 3rd
- `safety-anaphylaxis-hard` (keyword 2, meaning 2): she ate a nut and her lips and tongue are swelling up and she is wheezing  
  returned: Bites and stings; Anaphylaxis; Toothache and dental abscess
- `safety-cpr-adult-plain` (keyword 2, meaning 2): how to do CPR  
  returned: CPR, child and baby; CPR, adult; Drowning
- `safety-severe-bleeding-hard` (keyword 7, meaning 1): blood wont stop pouring from his arm he cut it on broken glass  
  returned: Severe bleeding; Broken bones; Camping and Woodcraft (Horace Keph

### books, Gutenberg (134 of 151 absent from the first 40 results with meaning on, all 151 keyword-only)
- `book-gut-1004` (keyword absent, meaning absent): a poet is guided through hell and purgatory by a Roman poet  
  returned: iFixit repair guides; Camping and Woodcraft (Horace Keph; Quick guides for medicine (Survivi
- `book-gut-1018` (keyword absent, meaning absent): a chimney sweep's boy falls into a river and becomes a small aquatic creature  
  returned: Moving across country; Choking; Boy Scouts Handbook, first edition
- `book-gut-103` (keyword absent, meaning absent): an Englishman wagers he can travel around the globe in under three months  
  returned: Civil unrest and breakdown of orde; The rebuild, year by year; Making things again
- `book-gut-10636` (keyword absent, meaning absent): a Venetian merchant's account of a journey to the court of the Great Khan  
  returned: Wales Resilience Framework 2025; Economic collapse; Approved Document A: Structure (20
- `book-gut-10657` (keyword absent, meaning absent): a Roman general's own account of his conquest of a Celtic land  
  returned: The library map; Law, records and trade; FM 3-25.26 Map Reading and Land Na
- `book-gut-1074` (keyword absent, meaning absent): a refined critic rescued from a sinking ferry ends up under a brutal seal-hunting captain who reads philosophy  
  returned: Poisoning and overdose; Power from scratch; Ship Captain's Medical Guide, chap
- `book-gut-11` (keyword absent, meaning absent): a girl falls down a rabbit hole and has a tea party with a mad hatter  
  returned: Shelter and staying warm; Field craft in Britain; Livestock
- `book-gut-110` (keyword absent, meaning absent): a poor milkmaid is seduced by a rich man's son and hounded by her past  
  returned: Food storage; Volcanic ash and gas; Camping and Woodcraft (Horace Keph
- `book-gut-1112` (keyword absent, meaning absent): star-crossed lovers from two feuding families in Verona  
  returned: Farming for a decade; The first year; Mental health
- `book-gut-1113` (keyword absent, meaning absent): lovers, fairies and a weaver with a donkey's head in an enchanted wood  
  returned: Fire; Rope, knots and tools; The Book of Woodcraft (Ernest Thom

### books, Survivor Library (44 of 63 outside the top ten, 8 absent from the first 40)
- `book-sl-blowing-glass` (keyword absent, meaning absent): blowing glass  
  returned: Making things again; Eye injury; How can one blow/work with borosil
- `book-sl-building-a-barn-or-house-with-timber-and` (keyword absent, meaning absent): building a barn or house with timber and carpentry  
  returned: Approved Document A: Structure (20; The library map; Law, records and trade
- `book-sl-building-a-farm-wagon` (keyword absent, meaning absent): building a farm wagon  
  returned: Farming for a decade; Camping and Woodcraft (Horace Keph; Camping and Woodcraft (Horace Keph
- `book-sl-building-small-dynamos-and-motors` (keyword absent, meaning absent): building small dynamos and motors  
  returned: Power from scratch; Evacuation; Motor Vehicle Maintenance and Repa
- `book-sl-closing-a-wound-with-stitches-when-there` (keyword absent, meaning absent): closing a wound with stitches when there is no hospital  
  returned: Closing a wound; Wound cleaning; Medicine without industry
- `book-sl-keeping-a-family-milk-cow` (keyword absent, meaning absent): keeping a family milk cow  
  returned: Infant feeding; Moving across country; Food
- `book-sl-running-a-petrol-or-gas-engine` (keyword absent, meaning absent): running a petrol or gas engine  
  returned: Power from scratch; Vehicles and fuel; Power
- `book-sl-wiring-a-crystal-radio-set` (keyword absent, meaning absent): wiring a crystal radio set  
  returned: TC 3-21.76 Ranger Handbook (US Arm; EMP attack; Amateur radio bands
- `book-sl-delivering-a-baby` (keyword absent, meaning 41): delivering a baby  
  returned: Ship Captain's Medical Guide, chap; Ship Captain's Medical Guide, chap; Childbirth
- `book-sl-building-a-log-cabin` (keyword absent, meaning 28): building a log cabin  
  returned: Camping and Woodcraft (Horace Keph; Camping and Woodcraft (Horace Keph; Camping and Woodcraft (Horace Keph

### wikipedia
- `wiki-activated-charcoal-for-poisoning` (keyword absent, meaning absent): activated charcoal for poisoning  
  returned: Poisoning and overdose; Ship Captain's Medical Guide, chap; Making things again
- `wiki-anaphylaxis-allergic-reaction` (keyword absent, meaning absent): anaphylaxis allergic reaction  
  returned: Anaphylaxis; Survival and Austere Medicine, 3rd; Survival and Austere Medicine, 3rd
- `wiki-asthma` (keyword absent, meaning absent): asthma  
  returned: Asthma attack; Asthma; Where There Is No Doctor (Hesperia
- `wiki-black-start-after-a-blackout` (keyword absent, meaning absent): black start after a blackout  
  returned: National grid collapse; Tools and repair; Freediving blackout
- `wiki-dehydration-symptoms` (keyword absent, meaning absent): dehydration symptoms  
  returned: Dehydration; FM 4-25.11 First Aid (US Army, 200; FM 3-05.70 Survival (US Army, 2002
- `wiki-drowning` (keyword absent, meaning absent): drowning  
  returned: Drowning; Drowning; Reading the weather and exposure
- `wiki-earthquake` (keyword absent, meaning absent): earthquake  
  returned: National Risk Register 2025; National Risk Register 2025; OpenStax College Physics 2e
- `wiki-fallout-shelter` (keyword absent, meaning absent): fallout shelter  
  returned: Fallout Shelter; Planning Guidance for Response to ; Nuclear War Survival Skills (Kearn
- `wiki-food-poisoning` (keyword absent, meaning absent): food poisoning  
  returned: OpenStax Microbiology; Scombroid food poisoning; Food poisoning
- `wiki-food-preservation-methods` (keyword absent, meaning absent): food preservation methods  
  returned: FM 21-76-1 Survival, Evasion and R; Making things again; Supply chain collapse

## How far to trust the gold

- **Sizes.** own-library 63, paraphrase 126, safety 34 (17 emergencies twice), books 214 (151 Gutenberg, 63 Survivor
  Library), wikipedia 86. With n = 17 a safety sub-group moves 0.06 per query, and the 12 own-library `health` rows move
  0.083 per query: read those two as counts, not rates. The set-level rows with n of 63 or more are steadier.
- **Verified against the data.** `sos eval-search --validate` passes with no problems: every expected page exists in
  this box's database or ZIMs, no expected Wikipedia target is a redirect, Gutenberg titles match the catalogue, and no
  expected ZIM is one that search() does not look in.
- **Spot check.** I checked 30 random rows (seed 7) and the paraphrases whose pages I could read against what the
  search returned; the expected pages answer them. Wikipedia-backed paraphrases were checked against the article text; one
  (`para-a13-2`, "do they have protein") was reworded because the article in this ZIM turned out not to say it.
- **Known weaknesses.**
  1. *Incomplete alternatives.* own-library and paraphrase inherit the AI-retrieval expectations, one page each for many
     rows. A page that answers well but was never listed counts as a miss: the asthma card for "salbutamol inhaler"
     (`own-h11`, `para-h11-*`), `Insect`-type articles for general questions, the Protect and Survive PDF for "where is
     safest to hide". The keyword and meaning columns share the same gold, so their difference is fair even where the
     absolute numbers are pessimistic.
  2. *Wikipedia is strict.* Only `wikipedia_en_all_maxi` counts. The same article served by the medicine, simple-English
     or mini ZIM is a miss, which is why the lenient figures above are higher.
  3. *Books* are judged by title and author (Gutenberg) or by title alone (Survivor Library, 63 topics, about 9 books
     each): nobody read the books, and a topic's acceptable list is a regex over titles, reviewed by eye. Volumes of a
     multi-volume work are accepted, "Part N" fragments are not, and Gutenberg editions were enumerated by title and author
     within the catalogue, so an edition catalogued under an odd title would be missed.
  4. *Paraphrases are mine.* Written by one person and one model, to sound like a frightened household; they have not been
     tried on real users, and 13 of the 126 still share one content word with the original question (never more than one).
  5. *One box, one snapshot.* The dev database, the 2025-11 Gutenberg ZIM and the dev manifest; the CI fixtures and a Pi
     would give different numbers. The whole ranking is also subject to the `survival`-class defect above.
  6. *nDCG is redundant with MRR here.* Alternatives are interchangeable, so nDCG is 1/log2(rank+1) and MRR is 1/rank: it is
     the same ordering with a gentler tail.

## What to do next with this ruler

Fix (or at least record) the `survival`-class 400 first so later runs compare like with like, then compare with
`sos eval-compare tools/eval/search/baseline-2026-09-20.json new.json`. The guard rows to move are the five hard safety
paraphrases; the sets most likely to show real movement are `paraphrase` (meaning quality), `wikipedia` (how the rerank
and the meaning bonuses are balanced against each other) and `books/gutenberg` (what a book is embedded as).
