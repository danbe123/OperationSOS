# Search gold sets

Hand-written gold for `sos eval-search` (the search-quality benchmark, `api/sos/searcheval.py`). Not to be confused with
`../questions.jsonl`, which is the AI assistant's retrieval set.

## Schema

One JSON object per line, in `<set>.jsonl`:

```json
{"id": "own-a01", "query": "how do I make water safe to drink", "expected": [{"item": "page:water-disinfection"}],
 "set": "own-library", "group": "answer", "tags": ["guard"], "notes": "why this row is what it is"}
```

| field      | meaning |
|------------|---------|
| `id`       | unique across every file |
| `query`    | what the user types, exactly |
| `expected` | a non-empty list of **alternatives**: a result matching any one of them is a hit |
| `set`      | must equal the file name without `.jsonl` |
| `group`    | optional sub-set, reported separately (`answer`/`health`, `plain`/`hard`, `gutenberg`/`survivor`, `question`/`term`) |
| `tags`     | optional; `guard` marks the safety guard rows |
| `notes`    | judgement calls, dropped alternatives, deliberate misspellings |

Each `expected` entry has exactly one of these keys:

| key | shape | resolves to |
|-----|-------|-------------|
| `url` | `"/read/wikipedia_en_all_maxi/Iodine"` | itself (`/p/…`, `/m/…`, `/medical/card/…`, `/s/…`, `/doc/…`, `/read/<zim>/<path>`) |
| `item` (+ `path`) | `{"item": "card:choking"}`, `{"item": "nhs_medicines", "path": "www.nhs.uk/medicines/loperamide/"}` | the URL `evalrun.expected_url` gives (same shape as `questions.jsonl`) |
| `gutenberg` (+ `title`) | `{"gutenberg": 2701, "title": "Moby Dick; Or, The Whale"}` | `/book/gutenberg/2701`; `title`, if present, must equal the catalogue's |
| `survivor` | `{"survivor": "the_practical_bee-keeper_1851"}` | `/kiwix/content/survivorlibrary.com_en_all/www.survivorlibrary.com/library/<slug>.pdf` |

A result is a hit when its URL equals the expected URL or continues it at a `/` or `#` boundary (so `/p/water-disinfection`
matches any section of that page, and a PDF library item matches any of its pages).

`sos eval-search --validate` checks every row against the real database and ZIMs: JSON and shape, unique ids, no repeated
query within a set, every expected page present (authored pages and documents in `fts_docs`, ZIM entries present and not
redirects, Gutenberg ids in `books`, Survivor Library slugs in the ZIM), and that a ZIM item is one search() actually
looks in (`fts=1`). It exits non-zero on any problem. Gold is verified against this machine's library
(`SOS_MANIFEST_DIR=.dev/full-manifest`), not the CI fixtures.

## The sets

| set | rows | what it measures |
|-----|-----:|------------------|
| `own-library` | 63 | the 55 `answer` and 12 `health` questions of `questions.jsonl`, minus four whose only pages are iFixit guides (not keyword-searched), with expected items that are not in this library dropped (`nhs_uk`, `zimgit-*`, dated NHS/iFixit ids). |
| `paraphrase` | 126 | two frightened-household rewordings of every own-library question, sharing as few content words as possible with it. **The meaning-search set.** Same `expected` as the original. Some deliberate misspellings (see `notes`). |
| `safety` | 34 | 17 emergencies, each plain and in a hard paraphrase; the box's own quick card must be in the top 3. Tagged `guard`: no change may regress it. |
| `books` | 214 | 151 known-item descriptions of Project Gutenberg books (`group: gutenberg`; title and author never in the query; every edition of the work is acceptable) and 63 practical topics answered by Survivor Library books (`group: survivor`; every book whose title clearly covers the topic). |
| `books-extra` | 58 | fresh everyday-intent queries ("how to build a chicken coop", "a first aid book for accidents at home", "a book of ghost stories to read on a winter night"), written after the model bake-off from the catalogue's metadata alone, before any embedding was scored: 27 answered by Survivor Library (`group: survivor`), 24 by Gutenberg (`gutenberg`), 7 by both (`both`). `expected` lists every book whose title clearly covers the topic (1 to 32 books), Survivor Library category pages were used to find candidates but not to decide (the site's category is a representation under test). Half are held out by `lab/books/books_eval.py`'s stable hash. Rebuilt by `lab/books/make_extras.py` from `lab/books/extras_spec.py`. |
| `wikipedia` | 86 | known-item lookups of one English Wikipedia article. Meaning search only reorders Wikipedia's keyword hits, so the figure that matters is the target's rank with the rerank off and on. |

`heldout-2026-09-21.jsonl` (62 rows, `group` is the class: medicine-name, medicine-question, medicine-paraphrase, everyday, safety-plain, safety-hard, wikipedia) was written before
the tuning was finished and its results were not looked at; it is a held-out check, not a tuning set. It is left out of a default run and of `ALL`: run it by naming it
(`sos eval-search heldout-2026-09-21`), and do not tune on it.

`injury-heldout-2026-09-22.jsonl` (46 rows, task 25) is the same kind of check for injury descriptions: 33 unseen
injury/location phrasings (`group: injury`; bleeding, wounds, burns and scalds, sprains, fractures, eye, head, nosebleed,
bites) whose box quick card should lead, and 13 contrasts (`group: contrast`, tagged `contrast`) that share an injury or
body word but are not an injury described -- names ("Sam Gash", "Robert Burns poems"), phrases ("power cut", "bike brake
bleeding", "burn a CD", "arm wrestling rules") and book requests -- which must not be read as one. It was committed before
any search ran against it and is run once, by naming it. Any gold file with `heldout` as a word of its name is held out.

## Metrics

Alternatives are interchangeable, so the first matching result is *the* relevant one:
hit@k (in the top k), MRR@10 (1 / rank, 0 beyond ten) and nDCG@10 (1 / log2(rank + 1), binary relevance), plus median
and p95 latency. `--semantic both` also lists the queries the meaning layer newly put in the top ten (rescued) or
newly took out of it (regressed). `sos eval-compare a.json b.json` prints the delta of two runs.

## Record and replay (fast experiments)

A live run takes about 30 minutes because every query is a round of Kiwix searches and an embedding call. Keep what
the searches consumed once, then run the search code against it with no service at all:

```
sos eval-search --record .dev/search-recordings/NAME --compact --json run.json     # live, both modes
sos eval-search --replay .dev/search-recordings/NAME --json replay.json            # no Kiwix, no embedding server
```

Per distinct query the recording holds every multi-archive Kiwix request's hits (or refusal), the query vector, the
nearest 100 passages of the box's own library and of the household books, and the Wikipedia rerank cosines
(`api/sos/searchreplay.py`). A replay opens the same database read-only and is deterministic; its timings are only
the search's own computation, and it reports the questions its recording could not answer (`meta.replay_misses`): a
change that asks Kiwix something new gets a refusal for it, so a non-zero count means that run is not comparable.
Record again after a database rebuild or an index rebuild. Recordings live under the git-ignored `.dev/`.

`lab.py` runs named parameter sets over a replay in parallel and prints one comparison table (see its docstring).

## Known limits

- `own-library` and `paraphrase` inherit the AI-retrieval expectations of `questions.jsonl`; a page that answers the
  question well but was never listed there (for example the asthma card for "salbutamol inhaler") counts as a miss.
- Survivor Library judgements are by title only; Gutenberg ones by title and author. Nobody read the books.
- Gutenberg multi-volume works accept their numbered volumes; single-volume "Part N" fragments are not accepted.
