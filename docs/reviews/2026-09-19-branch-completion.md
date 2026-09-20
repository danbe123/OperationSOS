# Branch completion review — 19 September 2026

## Scope and branch state

Reviewed `semantic-search-expansion` from `5506f9a` through `288699d`, including Tasks 1–9 and the Task 10 acceptance requirements. Checked the four older plan worktrees and their integration history.

| Branch | Tip supplied for review | State |
|---|---|---|
| plan-01 | df2856c | Already included in main and origin/main |
| plan-02 | 122c6f7 | Already included in main and origin/main |
| plan-03 | 20116d6 | Already included in main and origin/main |
| plan-04 | 4fc169a | Already included in main and origin/main; final maps integration is c967061 |
| semantic-search-expansion | 288699d | Review fixes and real acceptance recorded on this branch |

`git ls-remote origin` confirmed the remote main head is `5506f9a6dc4dacbd4083ae5ed7764d1858ef374d`. The four plan branch names do not exist remotely, but their commits are ancestors of that head. Their work is therefore already pushed as part of main. Untracked development logs/package metadata in the old worktrees were left alone.

## Findings addressed

- Household extraction eagerly retained the full text of every book. It now extracts a batch at a time. HTML extraction stops after enough complete paragraphs for the embedding window, preserving the full extractor's passage prefix. Build HTTP connections are reused.
- Wikipedia allocated the entire 6.47 GB vector matrix and rewrote it at every checkpoint. It now writes a memory-mapped staging file and flushes changed pages. Checkpoints are small and atomically replaced.
- Resume trusted a completed-row count even when its vector file was missing or truncated. Resume now requires the expected file size and a matching source revision, ordered-key digest, model and passage window. Corrupt checkpoints restart safely; skipped counts include earlier completed batches.
- A bounded Wikipedia sample replaced the production store and shared its checkpoint. Samples now live in `embeddings/wikipedia-sample/`, isolated from the full run. Non-positive limits are rejected.
- Separate file renames could pair new vectors with old keys. Publication now stages a complete generation and atomically switches a relative `*.current` symlink. Loaders resolve that generation once. Flat legacy indices still load. Copy the entire embeddings directory, including hidden generation directories and relative symlinks (for example with `rsync -a`); copying only the visible links is insufficient. Older generations are retained for existing readers.
- An unavailable/unreadable ZIM could abort its build, or a no-op household build could replace valid metadata with count zero. Unreadable archives are skipped at open; no-op builds leave the published household index and metadata untouched.
- Wikipedia reranking looked up URL-encoded article paths as literal archive keys. Paths are decoded once, retaining internal slashes.
- Household fusion treated every non-Gutenberg key as a Survivor Library book. It now requires one of the two supported, currently available archives; excluded or unknown sources cannot become household meaning hits.
- The CUDA build script assumed this checkout's absolute path. It now reads the pinned version relative to the script.
- The reader unit test included initial lazy-route iframe navigation in its PDF-click assertion. The assertion now measures the click itself.

A `--collection docs|household|all` option allows one collection to be rebuilt without repeating the other. The default still builds both; Wikipedia remains an explicit separate command. CPU runtime launch commands are unchanged.

## Validation and acceptance

The real build counts, measured throughput, search evidence and final suite totals are recorded in `docs/app-completion.md` under the 19 September semantic-search acceptance entry. Physical Pi acceptance remains in `docs/hardware-checklist.md`; no device checks were claimed from PC results.

Additional integrated checks passed: 10,000 situation simulation views, the map-style Node test, and `dev/smoke-selftest.sh` with access to its loopback fixture server.

The broader Playwright fixture suite is not green: 35 passed, 9 skipped and 17 failed. The browser implementation is unchanged by this branch. Failures include selectors and expectations for UI already removed on main: the wordmark, Medical navigation destination, Home search field, card step pager, always-visible map layers and visible headings on screens intentionally rendered without them. Other failures concern fixture map selection, situation wording, the Guides route and external reader links. These require a separate update against the current interface; they are not counted as semantic-search acceptance passes. Full output from this run is `/tmp/sos-review-e2e.log`.
