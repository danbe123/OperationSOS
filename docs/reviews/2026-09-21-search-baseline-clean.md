# Clean search baseline, 2026-09-21

The reference for every search-tuning experiment. It is the 2026-09-20 baseline (`docs/reviews/2026-09-20-search-baseline.md`)
re-run after the dev-box defect it exposed was repaired. Raw run: `tools/eval/search/baseline-clean-2026-09-21.json`
(`sos eval-compare` reads it). Code under test: `search-accuracy` at `66f9e1a` (clean tree), 523 gold queries, keyword-only
and meaning on, both from `sos.search.search()`; nothing in the gold sets changed.

## What was repaired

- **The `survival` class answered HTTP 400 on every search.** `solar.lowtechmagazine.com_mul_all` is a multilingual ZIM
  (library.xml language `eng,fra,deu,...`) but the dev database's `zim_languages` recorded it as `eng`, so Kiwix was asked for
  it in one request with nine English archives and refused the whole group. `sos index` (7.5 s here; it rescans, rebuilds
  `fts_docs` to the same 21,368 rows and re-flags the ZIMs) refreshed the setting from library.xml, so the ten survival
  sources are asked in two requests. `search()` also no longer lets one archive hide its class: a multi-archive request refused with a
  client error is retried by halves until the offender stands alone, one log line per distinct refusal, no extra request when
  nothing is refused (`f877099`).
- **Every one of the 1,046 searches is now complete: zero `partial`, zero retries but one, zero lost meaning layers.**
- **One archive stays out.** `solar.lowtechmagazine.com_mul_all` is refused by kiwix-serve even when asked for alone (`Two or more books in
  different languages would participate in search`, with `books.name`, `content` or a language filter alike): a multilingual ZIM cannot be
  full-text searched through this Kiwix build at all. It is skipped, silently for the search and once in the log. Nine of the ten survival
  sources now answer; Low-tech Magazine is not among them.
- **Found while recording the replay: nearly all of a search's time was one SQL scan.** `places.exact_place` fell back to a
  scan of the 2.7-million-row places table for every query with no exact place, 0.85 s of a 1.1 s search's own computation on the
  PC. It now scans only for a postcode (`1984262`). The latencies in the table below were measured before that fix,
  so they are the old cost; the tuning report has the after figures.

## Headline

Same layout as the earlier baseline. Latency is the dev PC with a warm Kiwix, one query at a time, before the places fix.

| set | n | search | hit@1 | hit@3 | hit@5 | hit@10 | MRR@10 | nDCG@10 | p50 ms | p95 ms |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|
| books | 214 | keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1556 | 2254 |
| books | 214 | meaning | 0.000 | 0.009 | 0.019 | 0.112 | 0.017 | 0.038 | 1590 | 2145 |
| books/gutenberg | 151 | keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1565 | 2254 |
| books/gutenberg | 151 | meaning | 0.000 | 0.007 | 0.013 | 0.040 | 0.007 | 0.014 | 1555 | 2145 |
| books/survivor | 63 | keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1544 | 2064 |
| books/survivor | 63 | meaning | 0.000 | 0.016 | 0.032 | 0.286 | 0.040 | 0.094 | 1612 | 2113 |
| own-library | 63 | keyword | 0.619 | 0.778 | 0.810 | 0.873 | 0.693 | 0.736 | 1564 | 3051 |
| own-library | 63 | meaning | 0.651 | 0.698 | 0.810 | 0.857 | 0.706 | 0.742 | 1631 | 3459 |
| own-library/answer | 51 | keyword | 0.608 | 0.725 | 0.765 | 0.843 | 0.673 | 0.713 | 1548 | 2201 |
| own-library/answer | 51 | meaning | 0.667 | 0.725 | 0.804 | 0.824 | 0.714 | 0.741 | 1627 | 2616 |
| own-library/health | 12 | keyword | 0.667 | 1.000 | 1.000 | 1.000 | 0.778 | 0.833 | 1675 | 3992 |
| own-library/health | 12 | meaning | 0.583 | 0.583 | 0.833 | 1.000 | 0.670 | 0.747 | 2050 | 4201 |
| paraphrase | 126 | keyword | 0.254 | 0.349 | 0.421 | 0.532 | 0.326 | 0.374 | 1780 | 2126 |
| paraphrase | 126 | meaning | 0.325 | 0.532 | 0.603 | 0.627 | 0.442 | 0.487 | 1818 | 2123 |
| paraphrase/answer | 102 | keyword | 0.275 | 0.373 | 0.451 | 0.559 | 0.349 | 0.398 | 1846 | 2142 |
| paraphrase/answer | 102 | meaning | 0.353 | 0.559 | 0.627 | 0.647 | 0.468 | 0.512 | 1875 | 2163 |
| paraphrase/health | 24 | keyword | 0.167 | 0.250 | 0.292 | 0.417 | 0.226 | 0.270 | 1520 | 1670 |
| paraphrase/health | 24 | meaning | 0.208 | 0.417 | 0.500 | 0.542 | 0.330 | 0.382 | 1568 | 1727 |
| safety | 34 | keyword | 0.559 | 0.765 | 0.794 | 0.882 | 0.667 | 0.719 | 1693 | 3568 |
| safety | 34 | meaning | 0.735 | 0.853 | 0.941 | 0.941 | 0.808 | 0.841 | 1701 | 4391 |
| safety/hard | 17 | keyword | 0.294 | 0.588 | 0.647 | 0.765 | 0.451 | 0.527 | 1626 | 3568 |
| safety/hard | 17 | meaning | 0.529 | 0.706 | 0.882 | 0.882 | 0.646 | 0.704 | 1653 | 4391 |
| safety/plain | 17 | keyword | 0.824 | 0.941 | 0.941 | 1.000 | 0.882 | 0.911 | 1760 | 8991 |
| safety/plain | 17 | meaning | 0.941 | 1.000 | 1.000 | 1.000 | 0.971 | 0.978 | 1799 | 5427 |
| wikipedia | 86 | keyword | 0.186 | 0.326 | 0.360 | 0.477 | 0.273 | 0.321 | 1664 | 1920 |
| wikipedia | 86 | meaning | 0.128 | 0.314 | 0.337 | 0.500 | 0.231 | 0.294 | 1702 | 2059 |
| wikipedia/question | 18 | keyword | 0.111 | 0.278 | 0.333 | 0.444 | 0.203 | 0.260 | 1696 | 1885 |
| wikipedia/question | 18 | meaning | 0.000 | 0.222 | 0.278 | 0.389 | 0.110 | 0.176 | 1694 | 2091 |
| wikipedia/term | 68 | keyword | 0.206 | 0.338 | 0.368 | 0.485 | 0.291 | 0.337 | 1660 | 1922 |
| wikipedia/term | 68 | meaning | 0.162 | 0.338 | 0.353 | 0.529 | 0.263 | 0.325 | 1707 | 2059 |
| ALL | 523 | keyword | 0.203 | 0.281 | 0.310 | 0.369 | 0.250 | 0.278 | 1630 | 2238 |
| ALL | 523 | meaning | 0.226 | 0.323 | 0.367 | 0.444 | 0.289 | 0.325 | 1658 | 2305 |


## What changed against the earlier baseline

The two runs differ in the code under test only by the survival class answering; the same 1,046 searches, the same ruler.

| | keyword | meaning |
|---|---|---|
| queries whose rank changed | 15 of 523, all lower | 40 of 523, all lower |
| of which crossed a bucket (top 1, 3, 10, miss) | 2 | 1 |
| by set | 1 own-library, 2 paraphrase, 12 wikipedia | 27 books, 11 wikipedia, 1 own-library, 1 paraphrase |
| survival rows in the recorded rankings | 0 -> 56 (in 53 queries) | 0 -> 21 (in 20 queries) |

- **Keyword hits from the survival sources now exist, and they rescue nothing.** Not one gold query gets a better rank. They
  displace: the wikipedia set's hit@10 keyword falls 0.500 -> 0.477 (two targets slide past ten: `para-a24-1` 39 -> absent, and
  the Wikipedia rows behind them), because a survival-site result now sits in the slots ahead of a target that used to be 7th or 10th.
  Every other headline figure is the same to three places: own-library, paraphrase, safety and books are unchanged with meaning on
  or off, wikipedia hit@1 0.186 and 0.128 as before.
- **The findings of the earlier baseline stand.** Meaning on: paraphrase hit@3 0.349 -> 0.532, safety hit@1 0.559 -> 0.735; own-library
  health hit@3 1.000 -> 0.583; Wikipedia hit@1 0.186 -> 0.128. Safety plain 17 of 17 in the top three with meaning on, safety hard 12 of 17
  (`safety-cpr-child-hard` 1 -> 4, `-hypothermia-` 4 -> 5, `-burns-` absent -> 13, `-seizures-` absent -> absent, `-heat-stroke-` 24 -> 5 are the five outside it).
- Rescued and regressed by meaning (newly in / out of the top ten): 47 and 8 (was 47 and 9; `own-a16` 9 -> 10 keyword is now regressed).
  The list of regressed rows is in the run file (`changes`).

## Reproducing

`sos index`, then `kiwix-serve` and `llama-server --embedding` as `dev/run-dev.sh` starts them, then
`sos eval-search --compact --json out.json --record .dev/search-recordings/NAME`. `sos eval-search --replay .dev/search-recordings/NAME`
reproduces all 1,046 ranks of this run exactly with no service (0 differences, 0 unanswered questions; about 70 s for both modes),
which is what the tuning experiments run on.
