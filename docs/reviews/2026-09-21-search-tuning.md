# Search tuning, 2026-09-21

The ruler of `docs/reviews/2026-09-20-search-baseline.md` (523 gold queries, `sos eval-search`), used to repair what it
exposed and to change the ranking only where it proved the change. Every number here is from the **clean baseline**
(`docs/reviews/2026-09-21-search-baseline-clean.md`, `tools/eval/search/baseline-clean-2026-09-21.json`) or from
the final live run (`tools/eval/search/after-tuning-2026-09-21.json`, code at `835edde`, clean tree, both modes, no
search partial, no meaning layer lost). The experiments were replays of a recording of the clean run
(`sos eval-search --record/--replay`, `tools/eval/search/lab.py`); the final live run reproduces the replay of the same code
**rank for rank (0 of 523 differences)**, and its keyword-only half reproduces the clean baseline's 523 ranks exactly.

## Result

Meaning layer on, clean baseline -> after tuning (keyword-only in the last column, which did not change):

| set | n | hit@1 | hit@3 | MRR@10 | keyword-only hit@1 / hit@3 / MRR |
|---|--:|---|---|---|---|
| own-library | 63 | 0.651 -> **0.635** | 0.698 -> **0.810** | 0.706 -> 0.718 | 0.619 / 0.778 / 0.693 |
| own-library/health | 12 | 0.583 -> 0.583 | 0.583 -> 0.833 | 0.670 -> 0.697 | 0.667 / 1.000 / 0.778 |
| paraphrase | 126 | 0.325 -> **0.389** | 0.532 -> **0.595** | 0.442 -> **0.497** | 0.254 / 0.349 / 0.326 |
| safety | 34 | 0.735 -> **0.824** | 0.853 -> **0.971** | 0.808 -> 0.887 | 0.559 / 0.765 / 0.667 |
| safety/plain | 17 | 0.941 -> 1.000 | 1.000 -> **1.000** | 0.971 -> 1.000 | 0.824 / 0.941 / 0.882 |
| safety/hard | 17 | 0.529 -> 0.647 | 0.706 -> **0.941** | 0.646 -> 0.775 | 0.294 / 0.588 / 0.451 |
| wikipedia | 86 | 0.128 -> **0.395** | 0.314 -> 0.570 | 0.231 -> 0.481 | 0.186 / 0.326 / 0.273 |
| wikipedia/question | 18 | 0.000 -> 0.444 | 0.222 -> 0.667 | 0.110 -> 0.537 | 0.111 / 0.278 / 0.203 |
| books | 214 | 0.000 -> 0.000 | 0.009 -> 0.005 | 0.017 -> 0.019 | 0 / 0 / 0 |
| books/survivor | 63 | 0.000 -> 0.000 | 0.016 -> 0.016 | 0.040 -> 0.048 | hit@10 0.000 -> 0.349 (was 0.286) |
| ALL | 523 | 0.226 -> 0.289 | 0.323 -> 0.400 | 0.289 -> 0.351 | 0.203 / 0.281 / 0.250 |

Latency, dev PC, warm Kiwix, one query at a time: keyword p50 1,630 ms -> 244 ms, meaning p50 1,658 ms -> 278 ms (p95 2,305 -> 486).
**Almost all of that fall is not the fusion**: recording the replay showed `places.exact_place` scanning the 2.7-million-row places
table for every query that is not a place (0.85 s of a 1.1 s search's own computation); it now scans only for a postcode
(`1984262`, ranks unchanged). The cost of the meaning layer itself moved from +28 ms to +34 ms of median, well inside the
+100 ms allowed.

### The guardrails

| guardrail | required | result |
|---|---|---|
| safety/plain in the top three | 17 of 17 | **17 of 17** (16 of 17 keyword-only) |
| safety overall and safety/hard improve | up | hit@3 0.853 -> 0.971, hard 12 -> 16 of 17 in the top three, hit@1 0.735 -> 0.824 |
| own-library hit@1 and hit@3 not below the clean keyword baseline | >= 0.619 / 0.778 | 0.635 / 0.810 (keyword 0.619 / 0.778) |
| paraphrase MRR rises | up | 0.442 -> 0.497 (keyword 0.326) |
| Wikipedia not worse than keyword-only | >= 0.186 / 0.326 / 0.273 | 0.395 / 0.570 / 0.481 |
| median latency rise at most 100 ms | <= +100 ms | -1,380 ms in all; +34 ms over keyword-only against +28 ms before |

The five hard paraphrases the clean baseline missed at the top three: `safety-cpr-child-hard` 4 -> 1 (keyword had it first, the
old fusion fourth), `safety-hypothermia-hard` 5 -> 2, `safety-burns-hard` 13 -> 2, `safety-heat-stroke-hard` 5 -> 3 are in;
**`safety-seizures-hard` ("man on the pavement is convulsing and foaming at the mouth") is still not found at all**: the seizure card is the
17th nearest passage at cosine 0.591, under every floor, and no keyword reaches it.

## What was adopted

Every change below is in `api/sos/search.py` with the reason next to its constant, and has tests (`api/tests/test_search_fusion.py`,
`test_search.py`, `test_places.py`, `test_embeddings.py`). The spec (section 3 of the search-precision-and-semantic design) says the same.

1. **The repair.** A multi-archive Kiwix request refused with a client error is retried by halves until the offender stands alone, so
   one misfiled archive cannot hide its class (`f877099`); the dev database's `zim_languages` was refreshed with `sos index`. Nine of the
   ten survival sources now answer; Low-tech Magazine, a multilingual ZIM, is refused by this kiwix-serve even alone and stays out (logged once).
2. **Reciprocal-rank fusion of the box's own passages** (`DENSE_WEIGHT` 2.0, documents worth `DENSE_DOC_SHARE` 0.5): the nth nearest of the
   twenty is worth `weight / (5 + n)` times 2, replacing `0.5 x weight x (cosine - 0.60) / 0.22`. bge-small's cosines for the nearest
   twenty sit within a few hundredths of each other, so distance scored a stranger nearly as high as the answer. Household books keep the distance bonus.
   Rank fusion with weight 2 against the same configuration with the old bonus: paraphrase MRR 0.481 vs 0.453, safety MRR 0.887 vs 0.843
   (rows `F` and `F-additive` below), and 0.70-0.72 vs 0.73 on own-library MRR; weights 1 and 3 are worse on safety or on own-library
   (`F-rrf1`, `dense-weight-3`).
3. **Own-page floor 0.69** (was 0.66) for a page the words missed. One measured effect: `safety-heat-stroke-hard`-type wordings stop pulling a
   stranger in above the card; safety hit@1 0.794 -> 0.824, hard 0.588 -> 0.647 (`F-floor0`). This rests on one hard row and the test that documented "0.68 answers"
   now says 0.69.
4. **Quick cards kept in the first three**: the card the words ranked first, and the two cards nearest in meaning at cosine >= 0.62. This is the
   emergency promotion rule. Without it (`no-cards-kept`, `F-nocards`): safety hit@3 0.853, hard 12 of 17; with it 0.971 and 16 of 17.
   **False-promotion rate on the other sets** (books excluded, 275 queries): a card newly enters the first three for 60 of them (22%: own-library 18 of 63,
   paraphrase 26 of 126, wikipedia 16 of 86); for 4 it is a listed answer (`para-a32-1`, `para-a33-2`, `para-h10-2`, `para-a30-2`); it pushes a listed
   answer out of the first three for **none**, and moves 6 rows down a place or two (`own-a05` and `own-h01` among them, see below).
5. **Wikipedia lifted by a ramp on its cosine, not rescaled** (`WIKIPEDIA_LIFT` 0.6 between cosine 0.72 and 0.82; not applied to medical queries). See the recommendation.

**Measured and not adopted**: normalised-score fusion (worse on safety and paraphrase than rank fusion: `norm`); per-class floors, ceilings and
weights beyond the document share and the own-page floor (grid below: no gain outside noise); protection of an exact or near-exact title (below);
Wikipedia as rank fusion, a narrowed multiplicative rescale, and additive bonuses over the whole cosine range (below).

### Title protection, tried and dropped

The brief's fourth experiment (a page titled as the query, or with two thirds of its words, never put below where the words ranked it) was
built four ways and dropped. On the clean control it works: `prot-title-.66` own-library hit@3 0.698 -> 0.825 and health hit@3 0.583 -> 1.000, `protc-title-.66`
health 0.917. But it is not additive with rank fusion, which restores the same rows (`rrf-1`: health 0.917, own hit@3 0.825; `F-noprotect`
vs `F`: own-library 0.718 vs 0.716, wikipedia hit@1 0.407 vs 0.430); its variants that leave the cards alone break the safety guard
(`prot-title-.66`: plain 16 of 17, safety hit@3 0.824), the variants that yield to the cards lose the rows they were for, and its only gain in the final
configuration is two Wikipedia rows the lift already gives. It restored none of the health rows at the end: `own-h01` "paracetamol"
(keyword 3, final 6) and `own-h02` "ibuprofen" (3 -> 5) stay down. With three protected Wikipedia/dictionary rows ahead of the NHS page and two kept
cards, three places are not enough for both. Simplicity wins: the code is gone (`2dd5adc`; it is in `c39a441`).

## The experiments

Every row is a replay of the clean recording at commit `c39a441` (`git archive c39a441 api tools`, then `tools/eval/search/lab.py --replay
.dev/search-recordings/clean-2026-09-21`; the recording is not in git, the tooling to make it is). Hit values are meaning-on; all 523 queries; wikipedia is 86.
`F` is the pre-cleanup form of the adopted configuration: it applied the old rescale, not nothing, to medical queries, which is why the adopted row's wikipedia
figures (0.395 / 0.570 / 0.481) differ from `F`'s (0.430 / 0.581 / 0.516), and its title protection and card lift were the four-way experiments above.

| experiment | what | own h1 | own h3 | health h3 | para h3 | para MRR | safety h1 | safety h3 | plain 3 | hard 3 | wiki h1 | wiki h3 | wiki MRR |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `keyword` | keyword only (the control for everything) | 0.619 | 0.778 | 1.000 | 0.349 | 0.326 | 0.559 | 0.765 | 16/17 | 10/17 | 0.186 | 0.326 | 0.273 |
| `control` | (i) today's values: the clean baseline's meaning mode | 0.651 | 0.698 | 0.583 | 0.532 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.128 | 0.314 | 0.231 |
| `rrf-1` | (ii) reciprocal-rank fusion, weight 1 | 0.635 | 0.825 | 0.917 | 0.516 | 0.437 | 0.676 | 0.882 | 17/17 | 13/17 | 0.186 | 0.349 | 0.288 |
| `rrf-2` | (ii) reciprocal-rank fusion, weight 2 | 0.635 | 0.714 | 0.583 | 0.563 | 0.472 | 0.765 | 0.853 | 17/17 | 12/17 | 0.116 | 0.337 | 0.240 |
| `rrf-3` | (ii) reciprocal-rank fusion, weight 3 | 0.603 | 0.698 | 0.583 | 0.548 | 0.461 | 0.794 | 0.882 | 17/17 | 13/17 | 0.070 | 0.221 | 0.182 |
| `norm` | (ii) normalised-score fusion (cosine min-max over the top 20) | 0.603 | 0.698 | 0.583 | 0.556 | 0.469 | 0.706 | 0.853 | 17/17 | 12/17 | 0.081 | 0.314 | 0.200 |
| `prot-exact` | (iv) an exact title is never put below its keyword place | 0.635 | 0.698 | 0.583 | 0.532 | 0.442 | 0.676 | 0.853 | 17/17 | 12/17 | 0.233 | 0.372 | 0.312 |
| `prot-title-.66` | (iv) the same for a title with 2/3 of the query's words | 0.683 | 0.825 | 1.000 | 0.532 | 0.442 | 0.676 | 0.824 | 16/17 | 12/17 | 0.233 | 0.395 | 0.325 |
| `protc-title-.66` | (iv) as above, but never above a card in the first three | 0.683 | 0.810 | 0.917 | 0.532 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.221 | 0.384 | 0.313 |
| `protm-title-.66` | (iv) title row above every meaning-only row instead | 0.651 | 0.698 | 0.583 | 0.532 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.128 | 0.314 | 0.231 |
| `card-.70` | (v) the nearest passage overall, if a card at cos >= .70, stays in the top 3 | 0.651 | 0.698 | 0.583 | 0.540 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.128 | 0.314 | 0.231 |
| `card-best-.62` | (v) the nearest card at cos >= .62 stays in the top 3 | 0.651 | 0.698 | 0.583 | 0.556 | 0.448 | 0.735 | 0.882 | 17/17 | 13/17 | 0.128 | 0.302 | 0.230 |
| `card-kw` | (v) a card the words ranked first stays in the top 3 | 0.651 | 0.698 | 0.583 | 0.532 | 0.442 | 0.735 | 0.882 | 17/17 | 13/17 | 0.128 | 0.314 | 0.231 |
| `card-2best-.62` | (v) the two nearest cards at cos >= .62 stay in the top 3 | 0.651 | 0.698 | 0.583 | 0.579 | 0.455 | 0.735 | 0.941 | 17/17 | 15/17 | 0.128 | 0.291 | 0.229 |
| `card-kw+2best-.62` | (v) both of the last two | 0.651 | 0.698 | 0.583 | 0.571 | 0.453 | 0.735 | 0.971 | 17/17 | 16/17 | 0.128 | 0.291 | 0.229 |
| `wiki-off` | (vi) Wikipedia rerank off | 0.651 | 0.698 | 0.583 | 0.532 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.105 | 0.198 | 0.180 |
| `wiki-rrf-.3` | (vi) Wikipedia rank fusion, weight 0.3 | 0.651 | 0.698 | 0.583 | 0.532 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.140 | 0.337 | 0.264 |
| `wiki-rrf-1` | (vi) Wikipedia rank fusion, weight 1.0 | 0.651 | 0.683 | 0.583 | 0.524 | 0.441 | 0.735 | 0.853 | 17/17 | 12/17 | 0.337 | 0.500 | 0.454 |
| `wiki-narrow-.15` | (vi) multiplicative rescale narrowed to 0.85-1.15 | 0.651 | 0.698 | 0.583 | 0.532 | 0.442 | 0.735 | 0.853 | 17/17 | 12/17 | 0.105 | 0.256 | 0.199 |
| `A` | (iv)+(v): title protection 2/3 + cards kept (two nearest, keyword first) | 0.683 | 0.810 | 0.917 | 0.571 | 0.453 | 0.735 | 0.971 | 17/17 | 16/17 | 0.221 | 0.384 | 0.313 |
| `A+rrf2` | A + rank fusion weight 2 | 0.667 | 0.810 | 0.917 | 0.579 | 0.481 | 0.794 | 0.971 | 17/17 | 16/17 | 0.233 | 0.384 | 0.322 |
| `Cadd` | A + additive, doc bonus halved, own ceiling .75 (per-class tuning) | 0.667 | 0.825 | 0.833 | 0.603 | 0.491 | 0.765 | 0.971 | 17/17 | 16/17 | 0.221 | 0.372 | 0.314 |
| `A+wikiadd.5` | A + Wikipedia additive bonus, cosine ramp .5 to .8, weight .5 | 0.603 | 0.714 | 0.583 | 0.571 | 0.449 | 0.676 | 0.971 | 17/17 | 16/17 | 0.488 | 0.674 | 0.607 |
| `T1` | A + rank fusion 2, own floor +.03, doc share .5 (iii) | 0.651 | 0.810 | 0.917 | 0.595 | 0.497 | 0.824 | 0.971 | 17/17 | 16/17 | 0.233 | 0.384 | 0.326 |
| `T1+ramp.25` | T1 + Wikipedia ramp .72-.82, weight .25 | 0.619 | 0.810 | 0.917 | 0.595 | 0.497 | 0.765 | 0.971 | 17/17 | 16/17 | 0.477 | 0.674 | 0.584 |
| `T1+ramp.4nomed` | T1 + Wikipedia ramp weight .4, not for medical queries | 0.635 | 0.810 | 0.917 | 0.595 | 0.497 | 0.824 | 0.971 | 17/17 | 16/17 | 0.407 | 0.547 | 0.491 |
| `F` | T1 + ramp weight .6, not for medical queries (see note) | 0.635 | 0.810 | 0.917 | 0.595 | 0.497 | 0.824 | 0.971 | 17/17 | 16/17 | 0.430 | 0.581 | 0.516 |
| `F-noprotect` | F without title protection | 0.635 | 0.810 | 0.833 | 0.595 | 0.497 | 0.824 | 0.971 | 17/17 | 16/17 | 0.407 | 0.581 | 0.502 |
| `F-nocards` | F without the card rules | 0.635 | 0.825 | 0.917 | 0.556 | 0.484 | 0.765 | 0.912 | 17/17 | 14/17 | 0.430 | 0.581 | 0.516 |
| `F-nowiki` | F without the Wikipedia lift | 0.651 | 0.810 | 0.917 | 0.595 | 0.497 | 0.824 | 0.971 | 17/17 | 16/17 | 0.233 | 0.384 | 0.326 |
| `F-rrf1` | F with rank-fusion weight 1 | 0.635 | 0.841 | 1.000 | 0.563 | 0.457 | 0.676 | 0.971 | 17/17 | 16/17 | 0.442 | 0.581 | 0.521 |
| `F-additive` | F with the old additive bonus instead of rank fusion | 0.651 | 0.810 | 0.917 | 0.571 | 0.453 | 0.735 | 0.971 | 17/17 | 16/17 | 0.395 | 0.570 | 0.490 |
| `F-docw1` | F with documents worth as much as pages | 0.651 | 0.810 | 0.917 | 0.579 | 0.481 | 0.824 | 0.971 | 17/17 | 16/17 | 0.430 | 0.570 | 0.509 |
| `F-floor0` | F without the own-page floor +.03 | 0.635 | 0.810 | 0.917 | 0.595 | 0.497 | 0.794 | 0.971 | 17/17 | 16/17 | 0.430 | 0.581 | 0.514 |
| `F-nomedskip` | F with the lift on medical queries too | 0.603 | 0.794 | 0.833 | 0.595 | 0.497 | 0.765 | 0.971 | 17/17 | 16/17 | 0.581 | 0.744 | 0.664 |
| `adopted` | ADOPTED (fb112fc..835edde): rank fusion 2, doc share .5, floor .69, kept cards, Wikipedia lift .6 not medical | 0.635 | 0.810 | 0.833 | 0.595 | 0.497 | 0.824 | 0.971 | 17/17 | 16/17 | 0.395 | 0.570 | 0.481 |

### Tuned on half, checked on the other half

Fixed alternating split within each set (rows sorted by id, even positions tune, odd positions check; `lab.py --halves`). The rank-fusion parameters (weight,
own floor, document share) were chosen on the tune half of paraphrase and safety (`grid.py`, 3 x 3 x 3 x 3 = 108 combinations for rank fusion and 216 for the
additive form; at `c39a441`); the two halves and own-library, which no tuning looked at, then read:

| config (adopted, final code) | own-library h1 / h3 / MRR | paraphrase h1 / h3 / MRR | safety h1 / h3 / MRR | plain / hard in top 3 |
|---|---|---|---|---|
| keyword-only, tune half | 0.625 / 0.781 / 0.696 | 0.286 / 0.381 / 0.356 | 0.294 / 0.588 / 0.451 (hard only in this half) | - |
| adopted, **tune** half | 0.688 / 0.812 / 0.752 | 0.365 / 0.540 / 0.465 | 0.647 / 0.941 / 0.775 | - |
| keyword-only, check half | 0.613 / 0.774 / 0.689 | 0.222 / 0.317 / 0.295 | 0.824 / 0.941 / 0.882 | - |
| adopted, **check** half | **0.581** / 0.806 / 0.683 | 0.413 / 0.651 / 0.530 | 1.000 / 1.000 / 1.000 | - |
| Wikipedia, keyword-only tune / check hit@1 | 0.140 / 0.233 | | | |
| Wikipedia, adopted tune / check hit@1, hit@3 | 0.395 / 0.628 | 0.395 / 0.512 | | |

Read the check half honestly: paraphrase and safety improve as much or more on the half nothing was tuned on (paraphrase MRR 0.295 -> 0.530 on check against 0.356 -> 0.465 on tune; the
safety set is 17 emergencies in two wordings, so the halves are 17 rows of each kind and the numbers move 0.06 a row), and **own-library hit@1 on the check half is 0.581, under
keyword's 0.613**, while it is 0.688 against 0.625 on the tune half. The own-library figure that passes the guardrail (0.635 against 0.619) is one row of 63 and is not a comfortable margin.

The grids' best rows agree with the choice within noise (tune half paraphrase MRR + safety MRR; check half in the last columns), from `tools/eval/search/grid.py` at `c39a441`:
rank fusion weight 2.0 with own floor +.03 and document share 0.5 gave paraphrase MRR 0.467 / safety MRR 0.775 (tune), 0.538 / 1.000 (check), own-library 0.651 / 0.810 / 0.720;
weight 3.0 with document share 1.0 gave 0.436 / 0.814 tune, 0.518 / 1.000 check and lower own-library hit@1 (0.635); the additive form's best was 0.467 / 0.745 (tune), 0.524 / 0.971 (check).
The Wikipedia ramp grid (24 combinations of floor, ceiling and weight, `gridwiki.py`) had the same shape: hit@1 0.395-0.465 on the tune half and 0.419 on the check half across the plateau of weights 0.4 to 0.8.

## Rescued and regressed

Clean baseline meaning -> after tuning, movements across the first three (books excluded), from the two run files:

- **own-library**: into the top three 7: `own-a07` 4 -> 3 loperamide, `own-a10` 4 -> 2 amoxicillin, `own-a16` 17 -> 1 wild mushroom, `own-a19` 7 -> 1 sharpen a knife,
  `own-h07` 6 -> 3 amoxicillin, `own-h08` 4 -> 3 loperamide, `own-h11` 4 -> 3 salbutamol inhaler. Out of the first ten: `own-a02` 4 -> absent "how long do I need to boil water".
- **paraphrase**: into the top three 9: `para-a03-2`, `para-a27-1`, `para-a31-1` (12 -> 1, the gas-heater fumes), `para-a32-1` (absent -> 3, the spilled kettle), `para-a32-2` (21 -> 1),
  `para-a33-2` (9 -> 3), `para-a48-2`, `para-h06-2` (peanuts, 4 -> 2), `para-h10-2` (5 -> 2). Out of the top three 1: `para-a29-1` 1 -> 4 (concrete for radiation shielding).
- **safety**: into the top three 4, the four hard ones above. Out: none.
- **wikipedia**: into the top three 24, out 2 (`wiki-electromagnetic-pulse` 2 -> absent, `wiki-ibuprofen` 3 -> 25: a medical query gets no lift, and the rank-fused own passages take the rows above it;
  `wiki-oral-rehydration-salts` 9 -> absent and `wiki-pmr446-walkie-talkies` 10 -> 12 leave the first ten).
- **Against keyword-only**, rows now lower than keyword had them (own-library and safety): `own-a05` paracetamol dose 1 -> 5, `own-a08` diarrhoea 1 -> 2, `own-a10` amoxicillin 1 -> 2,
  `own-a11` HIV 11 -> 17, `own-a14` bats and rabies 10 -> 13, `own-a28` fallout shelter 1 -> 2, `own-a51` flood warning 1 -> 2, `own-h01` paracetamol 3 -> 6, `own-h02` ibuprofen 3 -> 5,
  `own-h11` salbutamol inhaler 1 -> 3. No safety row is lower than keyword had it.

Per adopted change, the rows that change first-three / miss status when it is ablated (replay, ablated -> adopted):

- **kept cards** (rows `no-cards-kept` -> adopted): `para-a30-2` 4 -> 3, `para-a32-1` absent -> 3, `para-a33-2` 8 -> 3, `para-h10-2` absent -> 2, `safety-cpr-child-hard` 2 -> 1,
  `safety-hypothermia-hard` 4 -> 2, `safety-carbon-monoxide-hard` 4 -> 1, `safety-burns-hard` 7 -> 2, `safety-heat-stroke-hard` 6 -> 3; the one loss: `wiki-low-blood-sugar` 10 -> 11.
- **Wikipedia lift** (`wikipedia-lift-0` -> adopted): 30 of the 35 rows that change are Wikipedia targets moved to first or second place (`wiki-how-does-a-heat-pump-work` 16 -> 1, `wiki-how-do-solar-panels-work` 37 -> 2,
  `wiki-using-a-compass-to-find-north` 38 -> 1, `wiki-what-is-e-coli` 14 -> 1, `wiki-salmonella`, `wiki-tsunami`, `wiki-amateur-radio` and `wiki-sourdough-starter` absent -> 1 or 2, ...); and four own-library rows:
  `own-a16` 14 -> 1 and `own-a19` 5 -> 1 (a Wikipedia article on mushrooms or knives is the answer the gold accepts), `own-a28` 1 -> 2 and `own-a51` 1 -> 2 (the lift puts "Fallout shelter" and "Flood warning" articles ahead of the box's own page). None is a safety row.
- **rank fusion, floor 0.69, document share**: the remainder of the table above (own-library health hit@3 0.583 -> 0.833, paraphrase +0.06 hit@3, safety +0.09 hit@1).

## What is still wrong

- **Safety**: `safety-seizures-hard` (absent). Nothing else in the 34 is outside the top three.
- **own-library, 12 of 63 outside the top three**: `own-a02` boil water (absent), `own-a05` paracetamol dose (5), `own-a06` ibuprofen with paracetamol (absent), `own-a11` HIV (17), `own-a12` alcohol withdrawal (absent),
  `own-a13` insects (absent), `own-a14` bats and rabies (13), `own-a15` urban foxes (absent), `own-a17` how rain forms (absent), `own-a18` what a virus is (absent), `own-h01` paracetamol (6), `own-h02` ibuprofen (5).
  The five general-knowledge rows (insects, foxes, rain, viruses, alcohol) are found by neither keyword nor meaning: the box holds nothing that answers them but Wikipedia, which the gold does not accept for these rows.
- **Medicine names**: health hit@3 is 0.833, against 1.000 keyword-only: `paracetamol` and `ibuprofen` (and the dose question `own-a05`) have the NHS page third or fifth behind the two kept cards and the rank-fused passages. This is the price of the emergency rule and of weight 2; weight 1 gets health hit@3 back to 0.833-0.917 at the cost of safety (hit@1 0.676, hard hit@1 0.529: `dense-weight-1`).
- **paraphrase**: 51 of 126 outside the top three, 43 outside the top ten; 46 own-library and paraphrase queries are found by neither mode. The NHS medicine pages are still not found from a paraphrase.
- **wikipedia**: 37 of 86 outside the top three, 34 outside the top ten. Medical targets get no lift (`wiki-ibuprofen`, `wiki-what-causes-a-stroke`, `wiki-dehydration-symptoms` ...).
- **books**: unchanged in kind: Gutenberg descriptions 6 of 151 in the top ten (as before), Survivor Library 22 of 63 (was 18): a Survivor topic reaches the top ten more often, none reaches the first place.

## Recommendation for the Wikipedia rerank

**Keep it on, with the lift instead of the rescale.** The brief's test was whether anything beats keyword-only on the Wikipedia set; the lift does, by a wide margin:

| Wikipedia, 86 lookups | hit@1 | hit@3 | MRR@10 |
|---|--:|--:|--:|
| keyword only | 0.186 | 0.326 | 0.273 |
| meaning on, the old 0.7x-1.3x rescale (clean baseline) | 0.128 | 0.314 | 0.231 |
| meaning on, rerank off (`wiki-off`) | 0.105 | 0.198 | 0.180 |
| meaning on, rerank as a narrowed rescale (0.85x-1.15x) | 0.105 | 0.256 | 0.199 |
| meaning on, rerank as rank fusion, weight 0.3 / 1.0 | 0.140 / 0.337 | 0.337 / 0.500 | 0.264 / 0.454 |
| meaning on, **the lift (adopted)** | **0.395** | **0.570** | **0.481** |

The cosine of the target article sits at 0.77 to 0.89 and that of the other hits at 0.58 to 0.79 (72 queries whose target Kiwix found: the target has the highest cosine of the hits in 59), so a lift over 0.72 to 0.82 carries the
signal and leaves the rest alone; the old rescale moved every hit alike and was too small to win back what the meaning layer's own pages took. The check half agrees (hit@1 0.395 against keyword's 0.233).
**What it costs**: the 6.5 GB store on the Pi, and no lift for medical queries (by design: the box's card leads there). If the Pi cannot hold it, the honest fallback is not "rerank off", which is worse than keyword-only for this set
(0.105 against 0.186 hit@1: the meaning layer's own rows fill the places), but leaving the rerank code path unused and accepting keyword-order Wikipedia hits below the meaning layer's additions. The switch is `WIKIPEDIA_LIFT = 0.0`.

## Caveats

- The gold sets were used to tune and to report; the alternating split is the only guard, on 63, 126, 34 and 86 rows. Most changes here are a handful of rows each: a floor (one hard safety row), the kept-card count (four rows), title protection (two).
- The `wiki` and `own-library` gold rows are the previous agent's; none was edited, and none is believed wrong. `own-a16` and `own-a19` gain because the lift puts a Wikipedia article first, which their gold accepts.
- `sos eval-search --replay` uses the recorded Kiwix answers; a change that asks Kiwix something new gets no answer for it and the run says so (`meta.replay_misses`, 0 here).
- One full-suite run failed once on `test_situation_api.py::test_the_view_reacts_to_a_power_cut` and passed alone and in two later full runs (1,687 passing at the end): a flake of the situation tests under load, not of anything touched here.
- The dev box only: a Pi's latencies, Kiwix and the vector stores' RAM were not measured.
