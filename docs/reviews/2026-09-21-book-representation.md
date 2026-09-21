# How a book is represented in meaning search, 2026-09-21

Question: the `household` collection holds one vector per book (Project Gutenberg 60,093 + Survivor Library 10,465 in the
shipped index). Books are found poorly by everyday queries. Which representation of a book ranks the right books highest, and
is it worth a full rebuild? Measured on a subset before anyone pays for one. Branch `household-repr` (from `search-models`).
Everything is reproducible from `tools/eval/search/lab/books/`; raw results in `tools/eval/search/lab/results/books/`.

## 1. Bottom line

1. **Everyday queries are not what is wrong with the vectors.** Searching the *shipped* 70,558-book index with today's
   representation (bge-small, read-only, no rebuild), the right Survivor Library book is in the top 10 for **92% of the 62
   existing topic queries** (MRR@10 0.588) and for **93% of my 58 fresh everyday queries** (MRR@10 0.692, median rank 1). The
   baseline report's figure for the same 63 Survivor topics on the app's whole result page is 30% (hit@10 0.302). The loss is
   between the vector index and the page, that is in fusion (`BOOK_WEIGHT` 0.6, `SEMANTIC_MIN`, competition from keyword and other
   sources), not in what a book is embedded as. Changing the representation does not move these queries: every difference on
   them is between -0.04 and +0.04 MRR with intervals spanning zero (section 3).
2. **Where a representation does matter is finding a Gutenberg book by what it is about** (the 151 plot-description queries). There
   the shipped index is poor: hit@10 0.272, median rank 123 of 70,558. Today's text is the first 2,584 characters of the book,
   which is very often a title page and contents list.
3. **Best simple change: embed a Gutenberg book as its catalogue description followed by only its opening** ("title by author.
   shelf name. Subjects: the page's own `dc.subject` headings. first 1,000 characters"), labelled `c0` below. With bge-small, on a
   14,222-book sample: plot-description MRR@10 **+0.065** (95% interval +0.020 to +0.112, 44 wins / 14 losses), hit@10 **+0.126**
   (+0.066 to +0.185); everyday queries **+0.003** (-0.046 to +0.051), i.e. no harm. Survivor Library books are left exactly as
   they are (`c0-gut-only`: +0.066 [+0.018, +0.116] on plot descriptions, +0.007 [-0.027, +0.042] on everyday).
4. **Multi-passage representations do not earn their cost.** Ten passages sampled across each book, pooled into one vector and
   blended with the metadata vector, is the best number on the tuning pool with e5-base-v2 (MRR@10 0.536 against 0.488 for
   today's text, +0.048 [+0.001, +0.097]; plot descriptions +0.079 [+0.014, +0.144]) but costs 10 times the passages to embed, needs
   the metadata-and-window pipeline for both ZIMs (using it for Gutenberg only, with Survivor Library left as today, wrecks the Survivor topics: -0.30 MRR with e5, -0.14 with bge), and
   is not distinguishable from the simple change on everyday queries (+0.012 [-0.048, +0.071]).
5. **The model swap does little for books.** e5-base-v2 against bge-small with today's text: plot descriptions +0.051 [-0.003, +0.107],
   everyday -0.003 [-0.058, +0.051]. It doubles the index (118 MB to about 228 MB). The bake-off's case for e5-base-v2 stands on
   the box's own library, not on books.
6. **Recommendation.** Do not rebuild for this alone. The gain is confined to plot-description queries: +0.065 MRR / +0.126 hit@10
   with bge-small at 14k books, which scales to roughly +0.03 / +0.08 at the full 70k library (section 4). It becomes free the next time the household collection is rebuilt anyway (a model change
   forces that): rebuild with `--household-text meta-opening` (implemented, opt-in, default unchanged). Spend the effort on the
   fusion of book hits into the page instead (point 1), where the measured loss is 92% to 30%. Do not adopt sampled passages.

## 2. What was measured

**Subset.** 5,222 books, then 14,222 (about 20% of the library; the 5,000 books are a strict subset of the 14,222):

| | Gutenberg | Survivor Library | total |
|---|--:|--:|--:|
| gold-target books (every acceptable book of every query that the shipped index holds) | 630 | 833 | 1,463 |
| hard distractors (same LCC shelf as a Gutenberg target, same site category as a Survivor target) | | | 2,109 |
| random distractors | | | 1,650 |
| stage 1 total | 3,427 | 1,795 | **5,222** |
| stage 2: 9,000 more random distractors | +6,000 | +3,000 | **14,222** (9,427 + 4,795) |

Seeded (`subset.py`, `subset_scale.py`). Only books the shipped index holds can be targets, so today's representation is not blamed for
a book it never embedded (69 gold entries dropped for this).

**Queries.** 271 with at least one acceptable book in the subset:

| stratum | n | what |
|---|--:|---|
| known | 151 | `books.jsonl` Gutenberg: plot description, title and author never in the query |
| sl | 62 | `books.jsonl` Survivor Library topics ("keeping bees"); every book whose title covers the topic |
| extras | 58 | **new** `books-extra.jsonl`: everyday intent ("how to build a chicken coop", "a first aid book for accidents and illness at home", "a book of ghost stories to read on a winter night", "how do I deal with sewage on a farm with no mains drains"); 27 answered by Survivor Library, 24 by Gutenberg, 7 by both; 1 to 32 acceptable books each |

The extras were written from the catalogue's title, author and shelf alone, **before any embedding was scored**, and pass
`sos eval-search --validate` (0 problems). Acceptable books are those whose title clearly covers the topic; the Survivor Library
category page was used to find candidates but never to decide, because the category is one of the representations under test.
`lab/books/extras_spec.py` holds every rule; `make_extras.py` regenerates the file. **Held out: half of the extras (28, stable hash
split, stratified by group) were not used for choosing anything; the other 30, the 151 and the 62 form the "tuning pool" (243 queries).**

**Representations** (`lab/books/reps.py`), each scored per book by cosine to the query vector:

| id | text |
|---|---|
| a | today: "title by author. first 2,584 characters of the book" (Survivor: file-name title, first 2,584 characters of pdftotext) |
| b1 | title, author, LCC shelf name only |
| b2 | b1 + the page's `dc.subject` headings (Gutenberg) or the site's category page(s) and its own title (Survivor Library) |
| c0 | b2 + the first 1,000 characters of the book |
| c1 | b2 + the first real prose (title page, contents list, licence skipped by a paragraph heuristic), up to 1,500 characters |
| c2 | b1 + the same prose (no subjects) |
| dt-k, dp-k | ten 1,500-character windows at 5%, 15% ... 95% of the book, each prefixed with the title (dt) or bare (dp); k = 3 (start, middle, end), 5 or 10 of them; scored by `max`, `mean`, `top2` (mean of the two best) or `pool` (one vector: the normalised mean) |
| b2+dt10-... | b2 combined with the windows: `avg(max)` = mean of the two cosines, `pooledvec` = normalised sum of the b2 vector and the pooled windows |
| c0-gut-only | c0 for Gutenberg, a for Survivor Library (what the implemented option does) |

**What the ZIM's book pages expose beyond today's text** (inspected on real pages): Gutenberg's HTML head carries `dc.subject`
(Library of Congress subject headings, 1 to 9 per book, e.g. Moby-Dick: Whaling -- Fiction; Sea stories; Ship captains -- Fiction ...),
`dc.creator`, `dc.language`; the "cover" page adds nothing (title, author, licence); the body's first thousands of characters are
often a contents list ("CHAPTER 1. Loomings. CHAPTER 2. The Carpet-Bag ..." is what today's Moby-Dick vector is made of). Survivor
Library has 193 `library-<category>` pages, tables of title and PDF link, that give 11,493 of its 11,802 books a site-assigned category
(170 categories); a book has one PDF and no other metadata.

**Models.** `BAAI/bge-small-en-v1.5` (CLS pooling, the app's query instruction, no passage prefix) and `intfloat/e5-base-v2` (mean
pooling, `query: ` / `passage: `), fp16 on the GPU, 512-token window, from `lab/models.py`. Extraction: the app's own
`_gutenberg_text` / `_pdf_text`.

**Metric.** Rank of the best acceptable book among the pool's books (editions of one work count as alternatives). MRR@10, hit@5, hit@10;
also nDCG@10 and coverage of the acceptable set in the top 10 (`results/books/eval_*.json`). Paired bootstrap, 4,000 resamples over
queries, `*` = interval excludes 0 (`books_report.py`, `books_cross.py`).

## 3. Results on the 14,222-book pool

Cells are MRR@10 / hit@5 / hit@10. `sl` and `extra-*` are everyday; `known` is plot descriptions.

### bge-small-en-v1.5

| representation | known (151) | sl (62) | extra-dev (30) | extra-heldout (28) | tuning pool (243) |
|---|--:|--:|--:|--:|--:|
| **a today** | 0.232/0.33/0.40 | 0.772/0.95/0.98 | 0.867/0.97/0.97 | 0.845/0.96/1.00 | 0.448/0.57/0.62 |
| b1 title, author, shelf | 0.138/0.21/0.27 | 0.752/0.97/1.00 | 0.856/0.97/0.97 | 0.754/0.93/0.93 | 0.383/0.50/0.54 |
| b2 + subjects / category | 0.201/0.29/0.36 | 0.822/0.98/0.98 | 0.867/0.93/0.97 | 0.740/0.93/0.96 | 0.442/0.55/0.60 |
| **c0 b2 + first 1,000 chars** | 0.297/0.45/0.53 | 0.799/0.97/1.00 | 0.867/0.93/0.93 | 0.798/1.00/1.00 | 0.496/0.64/0.70 |
| c1 b2 + first prose | 0.290/0.42/0.48 | 0.796/0.95/1.00 | 0.872/0.93/0.97 | 0.820/0.93/0.96 | 0.491/0.62/0.67 |
| c2 b1 + first prose | 0.196/0.30/0.34 | 0.754/0.92/0.98 | 0.847/0.97/0.97 | 0.806/0.96/1.00 | 0.419/0.54/0.58 |
| 10 windows with title, top2 | 0.311/0.40/0.48 | 0.736/0.92/0.97 | 0.836/0.97/0.97 | 0.812/0.93/0.96 | 0.484/0.60/0.66 |
| 10 windows with title, pooled | 0.261/0.38/0.45 | 0.780/0.95/0.97 | 0.823/0.93/0.93 | 0.771/1.00/1.00 | 0.463/0.59/0.64 |
| 10 windows with title, max | 0.271/0.39/0.48 | 0.686/0.87/0.94 | 0.794/0.97/0.97 | 0.790/0.93/0.96 | 0.442/0.58/0.65 |
| 10 windows, no title, pooled | 0.169/0.25/0.32 | 0.689/0.92/0.94 | 0.770/0.90/0.93 | 0.711/0.89/0.96 | 0.376/0.50/0.56 |
| b2 + windows, avg(max) | 0.277/0.38/0.48 | 0.807/0.94/0.98 | 0.900/0.97/0.97 | 0.838/0.96/1.00 | 0.489/0.60/0.67 |
| b2 + windows, pooled vector | 0.269/0.38/0.50 | 0.786/0.95/0.98 | 0.857/0.97/0.97 | 0.858/1.00/1.00 | 0.474/0.60/0.68 |
| c1 + windows, avg(max) | 0.327/0.42/0.55 | 0.821/0.97/1.00 | 0.828/0.97/0.97 | 0.804/0.96/1.00 | 0.515/0.63/0.72 |
| c0-gut-only | 0.298/0.46/0.52 | 0.787/0.97/0.98 | 0.867/0.93/0.93 | 0.842/1.00/1.00 | 0.493/0.65/0.69 |

### intfloat/e5-base-v2

| representation | known (151) | sl (62) | extra-dev (30) | extra-heldout (28) | tuning pool (243) |
|---|--:|--:|--:|--:|--:|
| **a today** | 0.284/0.38/0.46 | 0.785/0.98/0.98 | 0.903/1.00/1.00 | 0.763/0.93/0.96 | 0.488/0.61/0.66 |
| b1 | 0.118/0.17/0.23 | 0.787/0.98/0.98 | 0.806/0.97/0.97 | 0.785/0.89/0.93 | 0.374/0.47/0.51 |
| b2 | 0.265/0.33/0.39 | 0.806/0.94/1.00 | 0.806/0.97/1.00 | 0.738/0.96/1.00 | 0.470/0.56/0.62 |
| c0 | 0.308/0.42/0.50 | 0.750/0.95/0.97 | 0.886/1.00/1.00 | 0.791/0.93/0.96 | 0.492/0.63/0.68 |
| c1 | 0.288/0.41/0.47 | 0.791/0.95/0.97 | 0.809/0.97/1.00 | 0.682/0.86/0.89 | 0.480/0.62/0.66 |
| 10 windows with title, top2 | 0.309/0.42/0.50 | 0.836/0.97/1.00 | 0.823/0.97/1.00 | 0.726/0.86/0.96 | 0.507/0.63/0.69 |
| 10 windows with title, pooled | 0.298/0.40/0.53 | 0.792/0.95/0.97 | 0.838/0.93/0.97 | 0.774/0.89/0.96 | 0.491/0.60/0.70 |
| 10 windows with title, max | 0.272/0.36/0.48 | 0.757/0.92/0.98 | 0.751/0.93/0.97 | 0.695/0.86/0.96 | 0.455/0.57/0.67 |
| 10 windows, no title, pooled | 0.222/0.31/0.40 | 0.724/0.89/0.94 | 0.731/0.87/0.93 | 0.643/0.86/0.89 | 0.413/0.53/0.60 |
| b2 + windows, avg(max) | 0.328/0.44/0.54 | 0.859/1.00/1.00 | 0.923/1.00/1.00 | 0.747/0.96/1.00 | 0.537/0.65/0.72 |
| b2 + windows, pooled vector | 0.363/0.48/0.56 | 0.808/0.94/1.00 | 0.847/0.97/0.97 | 0.824/1.00/1.00 | 0.536/0.66/0.72 |
| c1 + windows, avg(max) | 0.342/0.44/0.56 | 0.821/0.95/0.98 | 0.875/0.97/1.00 | 0.746/0.86/0.93 | 0.530/0.64/0.72 |

### Paired differences (MRR@10 and hit@10, B minus A, 95% interval, `*` excludes 0, wins/losses of B)

Everyday = sl + all 58 extras (120 queries); the 5,222-book pool gave the same picture (section 8).

| comparison | plot descriptions (151) MRR | plot descriptions hit@10 | everyday (120) MRR | held-out extras (28) MRR | tuning pool (243) MRR |
|---|---|---|---|---|---|
| bge c0 vs bge a | **+0.065 [+0.020, +0.112]*** 44/14 | **+0.126 [+0.066, +0.185]*** 22/3 | +0.003 [-0.046, +0.051] | -0.048 [-0.155, +0.071] | +0.047 [+0.012, +0.084]* |
| bge c0-gut-only vs bge a | +0.066 [+0.018, +0.116]* 42/17 | +0.113 [+0.053, +0.179]* 21/4 | +0.007 [-0.027, +0.042] | -0.004 [-0.108, +0.101] | +0.045 [+0.011, +0.078]* |
| bge c1 vs bge a | +0.058 [+0.008, +0.108]* | | +0.008 [-0.045, +0.057] | -0.026 [-0.159, +0.099] | +0.043 [+0.007, +0.081]* |
| bge b2 vs bge a | -0.032 [-0.089, +0.025] | | +0.002 [-0.065, +0.069] | -0.106 [-0.269, +0.054] | -0.007 [-0.051, +0.038] |
| bge b1 vs bge a | -0.094 [-0.144, -0.049]* | | -0.034 [-0.095, +0.026] | -0.091 [-0.271, +0.085] | -0.065 [-0.104, -0.027]* |
| bge windows pooled vector + b2 vs bge a | +0.037 [-0.018, +0.093] | +0.099 [+0.026, +0.172]* | +0.008 [-0.051, +0.066] | +0.013 [-0.123, +0.149] | +0.025 [-0.018, +0.067] |
| bge c1 + windows avg(max) vs bge a | +0.095 [+0.045, +0.144]* | | +0.006 [-0.046, +0.056] | -0.042 [-0.155, +0.060] | +0.067 [+0.029, +0.106]* |
| bge windows without title, pooled vs bge a | -0.063 [-0.132, +0.004] | | **-0.098 [-0.170, -0.031]*** | -0.134 [-0.284, +0.010] | -0.072 [-0.126, -0.022]* |
| e5 c0 vs e5 a | +0.024 [-0.020, +0.069] | +0.040 [-0.026, +0.106] | -0.016 [-0.057, +0.026] | +0.028 [-0.052, +0.106] | +0.004 [-0.028, +0.038] |
| e5 c0-gut-only vs e5 a | +0.003 [-0.043, +0.049] | +0.020 [-0.046, +0.086] | +0.009 [-0.012, +0.033] | +0.022 [-0.027, +0.083] | +0.004 [-0.026, +0.033] |
| e5 b2 + windows pooled vs e5 a | **+0.079 [+0.014, +0.144]*** 49/22 | +0.099 [+0.020, +0.179]* | +0.012 [-0.048, +0.071] | +0.061 [-0.067, +0.188] | +0.048 [+0.001, +0.097]* |
| e5 b2 + windows avg(max) vs e5 a | +0.044 [-0.018, +0.107] | +0.079 [+0.000, +0.159] | +0.040 [-0.008, +0.089] | -0.016 [-0.127, +0.091] | +0.049 [+0.006, +0.093]* |
| e5 b2 + windows pooled vs e5 c0 | +0.055 [+0.006, +0.107]* | +0.060 [-0.013, +0.126] | +0.028 [-0.033, +0.089] | +0.033 [-0.090, +0.159] | +0.044 [+0.001, +0.087]* |
| e5 pooled vector for Gutenberg only, Survivor as today, vs e5 a | +0.084 [+0.019, +0.147]* | | **-0.260 [-0.328, -0.194]*** (sl -0.304 [-0.390, -0.223]*) | -0.120 [-0.299, +0.065] | |
| bge pooled vector for Gutenberg only, Survivor as today, vs bge a | +0.038 [-0.017, +0.093] | | **-0.102 [-0.150, -0.058]*** (sl -0.142 [-0.202, -0.086]*) | -0.036 [-0.140, +0.071] | -0.023 [-0.064, +0.017] |
| **model only**: e5 a vs bge a | +0.051 [-0.003, +0.107] | +0.060 [-0.013, +0.132] | -0.003 [-0.058, +0.051] | -0.082 [-0.226, +0.045] | +0.040 [+0.000, +0.079] |
| e5 b2 + windows pooled vs bge a (both changes) | +0.130 [+0.059, +0.201]* 57/24 | +0.159 [+0.060, +0.252]* | +0.009 [-0.061, +0.072] | -0.021 [-0.170, +0.131] | +0.088 [+0.037, +0.138]* |
| e5 c0-gut-only vs bge a | +0.054 [-0.004, +0.112] | +0.079 [+0.007, +0.152]* | +0.006 [-0.055, +0.066] | -0.060 [-0.227, +0.092] | +0.043 [+0.000, +0.085] |

(the two "Gutenberg only" rows are the eval's `pooled-gut-only`: a Gutenberg book is represented by the pooled vector, a Survivor Library
book stays as today. The cosines of the two styles sit on different scales, so the Survivor books lose their place among the Gutenberg
ones. `c0-gut-only` does not have this problem because its Gutenberg text stays close in kind to today's.)

### What the tables say

* **Titles, authors and shelf names alone (b1) are as good as 2,584 characters of book for everyday queries** (bge everyday -0.034
  [-0.095, +0.026]; e5 -0.018) and much worse for plot descriptions (-0.094 / -0.165, `*`). Adding the subject headings (b2) recovers
  most of the plot-description loss with e5 (-0.018) and about a third with bge (-0.032 against b1's -0.094): the subjects say what
  a book is about, but not what happens in it. Metadata is a good *front* for a representation, not a replacement.
* **Text from the book itself is what plot descriptions need**, and only a little of it: c0 and c1 (metadata + 1,000 to 1,500
  characters) reach +0.06 with bge; ten windows across the whole book add nothing over that with bge (c1 + windows +0.095 against c1
  +0.058: the difference is about +0.04 with an interval crossing zero).
* **Skipping the front matter (c1) does not beat taking the raw beginning (c0)**: 0.290 against 0.297 on plot descriptions. The prose
  heuristic is not worth having; a 1,000-character opening after the metadata is enough that the contents list no longer swamps the
  vector.
* **Bare passages without the title are harmful** (everyday -0.098 [-0.170, -0.031] with bge, -0.10 with e5): a mid-book paragraph does
  not say what book it is from. Title-prefixed windows are neutral for everyday queries.
* **Aggregation**: `max` over passages is the worst aggregator (Survivor topics 0.686 against 0.780 pooled), `mean` and `top2` and
  a pooled vector are comparable. A pooled vector keeps the index at one vector per book, which `max` and `top2` do not.
* **Model**: e5-base-v2 helps plot descriptions slightly with today's text (+0.051, interval touching zero) and not at all for
  everyday queries; with the multi-passage representation it gains more (+0.079 over its own today's text) than bge does (+0.037).
  With the simple `c0`, e5 gains less than bge (+0.024 against +0.065, neither difference from the other tested).
  The best of everything, e5 with pooled windows, beats today's bge by +0.130 [+0.059, +0.201] on plot descriptions and +0.088
  [+0.037, +0.138] on the tuning pool, and does nothing for everyday queries (+0.009 [-0.061, +0.072]).

### Everyday queries are already near their ceiling in the vector index

On the 5,222-book pool the everyday strata sit at MRR 0.78 to 0.98 for every representation that contains the title (0.52 to 0.81 for bare
passages); at 14,222 they are 0.68 to 0.92 MRR and hit@10 0.89 to 1.00. Held-out extras (28 queries) cannot separate anything (intervals of about +-0.13). That is
partly a scale effect (section 4) and partly the gold: acceptable lists hold 1 to 32 books and the best rank of any of them is
scored, so a topic with several titled-on-topic books is easy for any representation that contains the title. nDCG@10 and
coverage of the whole acceptable set (fraction of min(10, n) acceptable books found in the top 10) tell the same story
(at 14,222 books the everyday nDCG@10 is 0.63 to 0.68 and coverage 0.61 to 0.69 for a, c0, pooled windows, with either model; `results/books/eval_*.json`).

## 4. Scale, and calibration against the shipped index

Subset numbers are optimistic because the pool is 5 to 20 times smaller than the library. I measured this two ways.

**Pool-size sweep** (`scaling` in the eval JSON: targets kept, other books sub-sampled, 5 seeds), bge-small, today's text:

| pool | plot descriptions MRR / hit@10 | everyday MRR / hit@10 |
|--:|--|--|
| 1,500 | 0.514 / 0.68 | 0.953 / 1.00 |
| 5,000 | 0.324 / 0.52 | 0.910 / 0.99 |
| 8,000 | 0.278 / 0.46 | 0.876 / 0.99 |
| 14,222 | 0.232 / 0.40 | 0.813 / 0.98 |
| **70,558 (the shipped index, read-only)** | **0.118 / 0.27** | **0.638 / 0.93** |

The last row is not an extrapolation: it is the shipped `household.hnsw` searched with the same bge-small queries
(`books_shipped.py`; HNSW `ef` 2000, so approximate-search misses are not what is measured). A log-linear line through the sub-sampled
pools would have predicted plot-description MRR 0.02 at 70k, so extrapolating the subset is not trustworthy; the calibration
point above is. The ordering of representations on plot descriptions was the same at every pool size (c0 above a at 1.5k, 2.5k,
5k, 8k, 11k and 14k for both models; the pooled-windows vector above c0 for e5 at every size); on everyday queries the differences stay inside +-0.02 at every size, and the *gap* between c0 and a in MRR shrinks in absolute terms as the pool grows while
the ratio stays: at 70k the shipped plot-description MRR is 0.118, so a proportional +28% (0.297/0.232 - 1) would be about +0.03.
By the same proportional argument hit@10 (+33% at 14k: 0.40 to 0.53) gives about +0.09 on 0.272. This is a rough scaling of one measured ratio, not a measurement: the size of the effect for bge-small at full library scale is **about +0.03 MRR and +0.08 hit@10**, not the +0.065 / +0.126 measured at 14k.

Shipped index, per stratum (bge-small, today's text, all 70,558 books):

| stratum | n | MRR@10 | hit@5 | hit@10 | hit@100 | median rank |
|---|--:|--:|--:|--:|--:|--:|
| plot descriptions (known) | 151 | 0.118 | 0.192 | 0.272 | 0.470 | 123 |
| Survivor topics (sl) | 62 | 0.588 | 0.887 | 0.919 | 0.984 | 2 |
| extras, all | 58 | 0.692 | 0.879 | 0.931 | 1.000 | 1 |
| extras answered by Survivor Library | 27 | 0.578 | 0.778 | 0.889 | 1.000 | 2 |
| extras answered by Gutenberg | 24 | 0.803 | 0.958 | 0.958 | 1.000 | 1 |
| extras answered by both | 7 | 0.750 | 1.000 | 1.000 | 1.000 | 1 |
| everyday (sl + extras) | 120 | 0.638 | 0.883 | 0.925 | 0.992 | 2 |

The weak extras at full scale: candles (rank 46 of 4 acceptable books), telescope (18), knitting (18), cheap cooking (17), hats (10).

## 5. Cost of a full rebuild

Measured on real books, one process, on a busy shared PC (300 books never seen by the subset: 200 Gutenberg, 100 Survivor Library),
plus the 9,000-book extraction (5 processes, 806 s) and GPU embedding throughput of each representation on this GPU (RTX 4070
SUPER, shared, fp16 torch; production embeds through `llama-server-cuda` q8_0, which the earlier notes put at about 140 texts/s and
which I did not re-measure):

| step | per book | whole library (60,093 Gutenberg + 10,465 Survivor) |
|---|--:|--:|
| today: read + first-2,584-character text | Gutenberg 0.029 s, Survivor 0.546 s (pdftotext 0.82 s mean over the larger sample) | 1,740 s + 5,710 s = **7,450 s (2.1 h)**, one process |
| `c0-gut-only` (the implemented option): same reads, plus a regex over the page head for subjects | +0.001 s | **7,450 s (2.1 h)**, the same |
| windows: adds the plain text of the whole book and 10 windows | +0.053 s Gutenberg, +0.041 s Survivor | 4,890 s + 6,140 s = **11,030 s (3.1 h)**, one process; about 6,300 s (1.75 h) with 5 processes at the 11.2 books/s measured on the 9,000-book run |

Embedding (one vector per book, GPU torch fp16):

| representation | texts | bge-small | e5-base-v2 |
|---|--:|--:|--:|
| today (a), 70,558 | 70,558 | 1,117/s, **63 s** | 498/s, **142 s** |
| `c0-gut-only`, 60,093 short + 10,465 as today | 70,558 | 1,975/s Gutenberg, **about 40 s** | 868/s, **about 90 s** |
| 10 windows per book, then pooled | 705,580 | 855/s, **14 min** (about 84 min at the 140/s llama-server rate) | 587/s, **20 min** |

The published build took 11,876 s (3.3 h) and was bound by ZIM reading and pdftotext, not by the GPU: **the recommended option costs the
same wall time as the last build (about 3.3 h, all of it extraction)**, the multi-passage one about +1 h of extraction and +14 to 84
minutes of embedding. Neither can run without the rest of the library: a household rebuild is all or nothing (the box refuses an
index whose meta names another model, and a mixed index breaks the balance between the two ZIMs, section 3).

Index (one vector per book): today's `household.hnsw` is 118.8 MB (384 dimensions, 70,558 vectors, graph about 10 MB). With e5-base-v2
(768 dimensions) about **228 MB** on disk and resident, +109 MB; with bge-small unchanged at 119 MB. Keeping every window as its own
vector (needed for `max`/`top2`) would be about 1.2 GB (bge) or 2.3 GB (e5), which the Pi's 8 GB should not be asked to carry next to
the rest; that is a further reason not to adopt sampled passages. The query side is unchanged (one embed, one HNSW search).

## 6. What was implemented

`api/sos/embeddings.py`: `build_household(..., text_style="legacy"|"meta-opening")`, `sos build-embeddings --household-text ...`.
The default is `legacy` and produces byte-for-byte what the published index was built from (existing tests untouched except two
signatures). `meta-opening` changes Gutenberg only: "title by author. shelf name. Subjects: dc.subject headings (cut at 400
characters). first 1,000 characters", read from the same page; the build records `text_style` in the collection meta. Six new tests
(subjects read only from the page head, default unchanged, the styled text exactly, Survivor Library identical under both styles,
unknown style refused, CLI flag), whole API suite 1,656 passed. The text is identical, character for character, to the lab's `c0` on
98 of 100 real books (the other two differ by a trailing space the lab strips; `check_text_identity.py`).

Not done, deliberately: no rebuild, nothing published over `/home/dan/sos-content/embeddings`, no fusion or threshold changes.

## 7. Caveats, stated plainly

1. **The gold is title-level and single-author.** 58 new queries, 28 held out: intervals on the held-out half are about +-0.13 MRR, so
   "no difference" there means "cannot tell". The extras were judged from titles, which favours representations that contain the title
   (all of them do; the ones that add the site category or `dc.subject` show no advantage, which is what I would expect if the gold did
   not leak them). Nobody read the books. The 151 plot descriptions are the existing gold and were used for tuning.
2. **Winner's curse.** About 35 systems for each of two models were compared on the tuning pool; the best of them is chosen on the data it
   is scored on and the interval for it is too optimistic. The choice of `c0` as the recommended option was made on plot descriptions
   (where it is significant for bge in both pools and at every pool size) rather than on the pool-level maximum, which belongs to a
   multi-passage blend I do not recommend.
3. **The gain does not show up on the held-out extras or any everyday stratum**; I recommend `meta-opening` for plot-description
   queries only. The evidence for everyday benefit is nil, and for harm also nil (c0-gut-only everyday +0.007 [-0.027, +0.042] with bge).
4. **14k is not 70k.** Section 4: the absolute effect at full scale is a fraction of what the subset shows. The ordering held at every size;
   nothing beyond that was tested (no full-library run of any new representation, by instruction).
5. **e5-base-v2 was measured on books for the first time here** and is not better than bge-small with the simple representation. This
   does not overrule the bake-off's finding on the box's own library.
6. **Survivor Library text quality.** 17.7% of the Survivor Library books in the 14k sample (851 of 4,795; 141 of 833 gold targets) have
   no text layer: pdftotext returns only form feeds. The build's own `SHORTEST_CHARS` check counts those as text (a string of 2,584
   `\f` is 2,584 characters), so they are embedded as their title plus whitespace, and the published meta's `skipped_no_text` (1,353 of
   71,911) understates it (about 1,850 by this ratio). Harmless for ranking (the title survives) but unintended; a `.strip()` in the
   length check would make it explicit. Not changed here.
7. **Gutenberg prose extraction** found no prose for 80 of 3,427 books (mostly verse and lists) and 22 of 630 targets; they fall back to
   metadata only in `c1`/`c2`. `c0` uses the raw beginning and has no such gap.
8. **Extraction timings** are from one sample of 300 books on a machine shared with other jobs; treat the hours as +-30%.
9. **Embedding runs**: the first all-in-memory embedding run of the 14k pool reached about 8 GB resident and was stopped; the run was
   redone in 4,096-text shards (`books_embed.py`, resumable, about 2.8 GB resident).

## 8. The 5,222-book pool

Same runs before the scale stage (`results/books/eval_bge-small-en-v1.5.json`, `eval_e5-base-v2.json`). Plot descriptions MRR@10:
bge a 0.313, c0 0.404, b2+windows pooled 0.387; e5 a 0.361, c0 0.412, pooled 0.496. Everyday strata all 0.82 to 0.97 for every
reasonable representation. e5 pooled against e5 a on plot descriptions +0.135 [+0.069, +0.205] (65 wins / 19 losses), hit@10
+0.219 [+0.139, +0.298]; against the tuning pool +0.073 [+0.026, +0.120]. The gains are roughly twice the 14k gains, in line with the pool-size sweep.

## 9. Recommendation

1. **Do not run a household rebuild for this alone.** Expected full-library gain for plot-description queries is about +0.03 MRR@10 /
   +0.08 hit@10 with bge-small (measured +0.065 / +0.126 at 14k), nothing measurable for everyday queries.
2. **When the household collection is rebuilt anyway (for example the e5-base-v2 switch in the bake-off), build with
   `sos build-embeddings --collection household --household-text meta-opening`.** It costs the same wall time, one vector per book, and
   does not hurt. With e5-base-v2 its measured gain is smaller and not distinguishable from zero (+0.024 [-0.020, +0.069]); the
   multi-passage pooled representation is the one that helps e5 (+0.079 [+0.014, +0.144]) at 10 times the embedding and a second
   extraction path, which I would not take for a plot-description-only gain.
3. **Look at fusion next.** Survivor topics reach the top 10 of the book index 92% of the time and the top 10 of the page 30% of the
   time: that is where an everyday query "loses" a book. Suggested measurement (not done): the same 120 everyday queries through
   `sos eval-search`, listing where each acceptable book ranks in the book group before and after `BOOK_WEIGHT`, `SEMANTIC_MIN` and the
   "meaning can add rows" gate.
4. Fix the form-feed length check (caveat 6) in the same change as the next rebuild.

## 10. Reproduce

Under `tools/eval/search/lab/books/` (API venv for anything that reads a ZIM, `~/.local/share/sos-embed-venv` for torch and analysis;
scratch under `$LAB_SCRATCH/books`): `catalogue.py` (catalogue + Survivor categories), `make_extras.py` + `extras_spec.py`
(the new gold), `subset.py`, `subset_scale.py`, `extract.py` (resumable), `books_embed.py <model> [--tag=-scale]` (`BOOKS_SUBSET=subset_scale`;
sharded, resumable), `books_eval.py <tag>`, `books_report.py <tag>`, `books_cross.py <bge tag> <e5 tag>`, `books_shipped.py`
(calibration against the shipped index), `check_text_identity.py` (the implemented text against the lab's). `reps.py` defines the
representations. Raw results in `results/books/` (about 1 MB per eval file). The vectors and extracted texts are in the scratch
directory and are not committed.
