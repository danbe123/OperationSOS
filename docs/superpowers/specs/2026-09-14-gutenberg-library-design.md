# The book collections read like books: design

**Status:** draft for the owner's review, 2026-09-14. Written after a design conversation that the owner ended
with "finish this idea"; the decisions in section 0 were taken without a final answer and are the first things
to check.

## 0. Decisions taken on the owner's behalf

| Decision | Chosen | Why | If wrong |
|---|---|---|---|
| Drive standard | 1 TB NVMe is the standard build; core tier grows to about 680 GB | The owner asked "can we not change the build to be 1 TB as standard"; the two book collections are the point of the box's ereader and they only fit in core on a 1 TB drive | Revert section 1; the collections stay on the external drive and the reader carries a drive badge |
| What moves to core | `gutenberg_en_all` (221 GB) and `survivorlibrary.com_en_all` (252 GB) | Together with today's 204 GB core that is 677 GB, leaving over 250 GB free on a 1 TB drive. Khan Academy (180 GB) would push it to 857 GB and under 70 GB headroom on the boot drive | Move Khan Academy too and raise the size test's upper bound |
| Where Gutenberg hits appear in search | Their own "Books" group after the manuals and reference groups | An emergency box should lead with guidance; a novel matching "fire" must not outrank the survival guide | Score them into the main ranking instead (section 5) |
| Full integration | Catalogue search, a shelf, the paginated reader with position memory | The owner said "I want the full integration" | Drop the shelf (section 7) |
| Semantic search | In this spec as phase 2, built after phase 1 ships | The owner asked for it; phase 2 needs phase 1's catalogue table | Split it into its own spec |
| Search depth | Title, author and subjects only for Gutenberg; no full text | The ZIM carries no full-text index and its 220 GB of text cannot be extracted on the box | Phase 2's per-book embeddings cover "books about X" |

## 1. The 1 TB standard

The design doc and README describe a 500 GB NVMe for core and a 2 TB USB drive for the extended library.
Core is 152 items, 204 GB. The extended tier is 664 GB, of which three items dominate: Survivor Library 252 GB,
Gutenberg 221 GB, Khan Academy 180 GB.

Changes:

- `README.md` hardware table and `docs/superpowers/specs/2026-09-03-operation-sos-design.md` section 3: the NVMe is
  1 TB (2280, the same Pimoroni NVMe Base). The external drive stays optional and is now "for Khan Academy, media
  and your own files".
- `manifest/core.json` gains the two ZIM items with `tier: "core"`, `category: "books"`, unchanged `dest`
  (`zim/<id>.zim`) and `source` (`kiwix`); `manifest/extended.json` loses them.
- `api/tests/test_manifest_content.py::test_core_size_near_target` bounds become `600e9 < total < 850e9`;
  `test_extended_tier_and_required_ids` drops the two ids from `EXTENDED_REQUIRED` and a new
  `test_core_has_the_book_collections` pins them in core.
- `docs/app-completion.md` gets a dated entry; the line saying Survivor Library "does not fit" is superseded.

Provisioning: `sos sync core` on the box downloads both from the Kiwix mirror as it does every other ZIM. The PC has
about 130 GB free, so it cannot hold the Gutenberg ZIM; anything that needs the file on the PC (section 3's
layout check, phase 2's embedding build) runs with the box's NVMe or a USB copy attached to the PC, the way the
maps are built.

## 2. What the ZIM contains

The Kiwix Gutenberg ZIM is produced by openzim's `gutenberg2zim`. Verified from the scraper's source
(`sources/gutenberg/exporter.py`, `core/exporters/json_exporter.py`, 2026-09-14): for each book it stores

- `<id>.html` — the book as one HTML page (what the Kiwix reader shows today),
- the EPUB and, where Gutenberg has one, the PDF, as their own entries (the "all" build the manifest names
  carries EPUB, HTML and PDF formats),
- `covers/<id>_cover_image.webp` when the book has a cover,
- and, once per ZIM, `books.json`, `authors.json`, collection JSON files and a title index entry per book, author
  and collection (`index/<name>`) that Kiwix's suggest endpoint searches.

`books.json` gives, per book: id, title, subtitle, author (name, birth and death years), formats with paths,
cover path, popularity (download count), language and subjects.

**The build on the owner's drive may predate the scraper rewrite.** Older builds name entries
`<Title>.<id>.epub`, keep the catalogue in `full_by_title.js` and have no `books.json`. The first task of the plan
is therefore a layout check with the ZIM mounted: list its entries, confirm the paths above, and record the
result in `docs/app-completion.md`. The catalogue importer (section 4) is written against the current layout with
the entry names in one table at the top of the module, so an older build costs a table edit, not a redesign.

## 3. Reading a Gutenberg book

A book opens in the EPUB reader the Library already has (`web/src/screens/Doc.tsx`, epub.js, paginated flow),
not in the Kiwix HTML reader. The reader is given the EPUB's URL inside the ZIM:
`/kiwix/content/gutenberg_en_all/<epub path>`, which kiwix-serve already serves through Caddy on the same origin.
Gutenberg EPUBs are between 100 KB and a few MB, so epub.js fetching the whole file is fine.

Route: `/book/gutenberg/<id>` → `Book` screen. It fetches `GET /api/books/gutenberg/<id>`, shows title, author
and cover in the screen header, then the reader with the compact toolbar (one `.doc-tools` bar: Previous, Next,
Text size). Books whose formats include no EPUB (a few hundred, mostly non-text) open the ZIM's HTML page in the
Kiwix reader as today; the API says which with `epub_url: null` and the screen redirects to `/read/...`.

**Position memory** is new; nothing in the app remembers a reading position today. The reader saves the epub.js
location (a CFI) and the percentage read on every `relocated` event, debounced to one write per two seconds, with
`PUT /api/reading/<key>` where the key is `gutenberg:<id>` for a collection book and `doc:<id>` for a Library
EPUB, so the manuals gain position memory for free. On open, the reader displays the saved CFI when there is one.
Positions live in the box's database, not the browser, because the box is shared by every device on the hotspot
and the kiosk screen; a phone and the touchscreen see the same bookmark.

## 4. The catalogue

`sos index` gains a step `index_books` after the title index. For every available ZIM item whose manifest
`category` is `books` and whose id is in `BOOK_ZIMS` (`gutenberg_en_all` only for now), it reads `books.json` and
`authors.json` through `kiwix.raw_article` (streamed with `ijson` if the file is over 20 MB; `books.json` for
70,000 books is about 40 MB) and rewrites two tables:

```
books(zim TEXT, id INTEGER, title, subtitle, author, author_years, subjects TEXT, language, popularity INTEGER,
      epub_path TEXT, html_path TEXT, cover_path TEXT, PRIMARY KEY (zim, id))
fts_books USING fts5(title, author, subjects, content='books', content_rowid='rowid', tokenize='porter unicode61')
```

The step deletes and re-inserts the ZIM's rows in one transaction, is a no-op when the ZIM is absent (the tables
keep their last contents; the API filters on the item's `available` flag), and logs one line
`index: 69,412 books from gutenberg_en_all`. It adds about 40 MB to `sos.db`.

API (`api/sos/routers/books.py`):

- `GET /api/books?q=&author=&subject=&sort=popular|title&limit=40&offset=` — catalogue browse and search.
  `q` runs an FTS match on `fts_books` (bm25 with title weighted 5, author 3, subjects 1); without `q`, sorted by
  popularity. Rows carry `id, title, author, author_years, subjects, cover_url, epub_url, html_url, popularity`.
- `GET /api/books/subjects` — the 200 most frequent subjects with counts, for the browse chips.
- `GET /api/books/gutenberg/<id>` — one book, plus `position` (section 3) when there is one.
- `GET /api/reading` — the shelf (section 7); `PUT /api/reading/<key>`, `DELETE /api/reading/<key>`.

Everything is read-only against the ZIM; nothing is written into it.

## 5. Search

`api/sos/search.py` gains a `books` class: when the query has terms, an FTS query on `fts_books` (limit 10) is
added alongside the Kiwix and `fts_docs` queries, with `source: "books"`, `badge: "Books"`, `url:
/book/gutenberg/<id>`, `title` the book's title, `snippet` "<author> · <first three subjects>", and a score
`0.6 / (5 + rank)` so a book never outranks a matching guide or document. `CLASS_TITLES["books"] = "Books"`; the
frontend `ORDER` list in `web/src/api/results.ts` places `books` after `reference` and before `uk-official`, so
the group renders below the guidance groups. The Kiwix search of the Gutenberg ZIM itself is dropped from the
per-class fan-out (it has no full-text index; its `_ftindex:no` tag makes `/search` return nothing useful), which
also removes a wasted request from every query today.

`suggest()` adds up to three `fts_books` title-prefix matches after the document titles.

## 6. Browsing

`/books` → `Books` screen: a search box (title, author, subject), subject chips from `/api/books/subjects`, a
"Popular" default listing, and result cards with cover, title, author and years. Paged by 40. The Library screen's
"books" category card ("Project Gutenberg — 69,000 books") links here instead of to the ZIM's own front page.
Survivor Library keeps its Kiwix front page: its books are page scans with no EPUB, so the reader cannot reflow
them; it is listed under the same category with the badge "scanned".

## 7. The shelf

"My books" is the top section of the Library screen when it is non-empty: every key in the reading table, newest
first, as cover, title, author, "42% read" and a Continue button that opens the book at its saved position. A
long-press or the card's × removes the entry (`DELETE /api/reading/<key>`). Opening a book is what shelves it;
there is no separate "add to shelf" action. The table:

```
reading(key TEXT PRIMARY KEY, title TEXT, author TEXT, cover_url TEXT, cfi TEXT, percent REAL, updated_at TEXT)
```

## 8. Phase 2: semantic search

Built after phase 1 ships and its catalogue exists.

- **Model**: `bge-small-en-v1.5` in GGUF (about 35 MB, 384 dimensions), served by the existing `llama-server`
  with `--embedding` on a second port, or by a second unit `sos-embed.service` if the chat model's server cannot
  serve both. A core `model` manifest item carries it. If the model or the vector files are absent, everything
  below is silently off and search behaves as phase 1.
  **Mandatory query prefix:** bge-small-en-v1.5 was trained with an asymmetric instruction applied to the query
  side only — every query embedded on the box must be prefixed with `"Represent this sentence for searching
  relevant passages: "` before the embedding call; passages indexed by `sos build-embeddings` are NOT prefixed.
  Getting this backwards produces no error, just silently worse retrieval (2026-09-16 model review) — the
  `api/tests/test_embeddings.py` fixture in section 11 must assert the prefix is applied to queries and absent
  from indexed passage text. `granite-embedding-small-english-r2` (Apache 2.0, same 384 dimensions, no prefix
  requirement, 8192-token window vs bge-small's 512) is a same-format bake-off candidate if bge-small's fixed
  512-token window or MIT licence ever become a problem; the vector format is identical either way.
- **Build** (`sos build-embeddings`, PC only, the GPU): one vector per Gutenberg book from
  "<title> by <author>. <subjects>. <first 300 words of <id>.html>" (needs the ZIM attached; about an hour on
  the RTX 4070); one vector per `fts_docs` row of the Library (about 20,000 chunks, minutes). Output:
  `embeddings/books.f16.bin` + `books.ids`, `embeddings/docs.f16.bin` + `docs.ids`, as core `build` items with
  sha256, about 55 MB and 15 MB.
- **Query** on the box: embed the query (one call to the embedding server, about 50 ms on the Pi 5), then a
  brute-force cosine over the in-memory fp16 matrices with numpy (70,000 × 384 in about 20 ms). No vector
  database. Results are fused with the keyword results by reciprocal rank fusion: books get a semantic list of
  20 fused with the FTS list; documents likewise. The AI answerer's grounding (`ai.py`) takes the fused top
  passages instead of BM25 alone.
- **Memory**: about 70 MB resident for both matrices; acceptable beside the 3 GB chat model on the 8 GB Pi.

## 9. Error handling

- ZIM absent (drive unplugged in the old layout, or before the first sync): `/api/books` returns an empty list
  with `available: false`; the Books screen says "Project Gutenberg is not on this box yet"; search omits the
  group; shelf entries for its books show "not available" and still keep their position.
- `books.json` missing or unparseable: `index_books` logs a warning naming the entry and leaves the tables as
  they were; `sos index` continues.
- EPUB fetch fails in the reader: the existing "Could not open this book" message, plus a link to the HTML page
  in the Kiwix reader.
- A saved CFI that no longer resolves (the ZIM was rebuilt): epub.js falls back to the start; the position is
  overwritten on the next `relocated`.

## 10. Scope

In: sections 1 to 8 for `gutenberg_en_all`. Position memory for Library EPUBs comes with section 3.

Out: reflowing Survivor Library (page scans; OCR is a different project), full text of Gutenberg in search,
Khan Academy in core, per-device positions, annotations and highlights.

## 11. Testing

- `api/tests/test_books.py`: `index_books` against a fixture `books.json` (six books, one without an EPUB, one
  without a cover) served by the kiwix `respx` fixtures; the FTS weighting (a title hit beats a subject hit); the
  absent-ZIM no-op; the reading endpoints round trip and the shelf ordering.
- `api/tests/test_search.py`: the `books` group appears with the right badge, url and score ceiling; the
  Gutenberg ZIM is not in the Kiwix fan-out.
- `api/tests/test_manifest_content.py`: the size bounds and the core/extended id pins of section 1.
- `web/tests/screens/book.test.tsx`, `books.test.tsx`, `library.test.tsx` (shelf section): render, redirect for an
  HTML-only book, position save debounce (fake timers), continue-at-position.
- Hardware checklist (`docs/hardware-checklist.md`): open a Gutenberg book on the touchscreen, page forward,
  reopen from a phone and land on the same page; search "Robinson Crusoe" shows the Books group below the guides.
- Phase 2 adds `api/tests/test_embeddings.py` with a four-row fixture matrix and a stub embedding server.
