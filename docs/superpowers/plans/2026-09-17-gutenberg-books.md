# Gutenberg Collection Books Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Project Gutenberg and Survivor Library into the core tier on a 1 TB drive, and let a household read a Gutenberg book on the box: catalogue search and browse, a "My books" shelf, and the paginated EPUB reader remembering where you were.

**Architecture:** `sos index` gains an `index_books` step that opens the Gutenberg ZIM **directly with python-libzim** (no kiwix-serve needed; at install time `sos index` runs before kiwix-serve starts), reads the scraper's catalogue entry `full_by_popularity.js`, and rewrites two SQLite tables, `books` and `fts_books`. A new router serves catalogue browse/search, one-book detail, and a `reading` position table. The book opens in the EPUB reader `Doc.tsx` already has, extended with a `memory` prop that saves the epub.js position (CFI plus an approximate percentage) to the box and reopens at it; Library EPUBs get the same. Search gains a `books` result group that the frontend renders below the guidance groups. Everything is read-only against the ZIM.

**Tech Stack:** FastAPI + SQLite FTS5 (existing), `libzim` (new dependency: python-libzim, manylinux x86_64 and aarch64 wheels for CPython 3.12 and 3.13, so it installs on the PC and the Pi), React + `epubjs` (existing).

**Spec:** `docs/superpowers/specs/2026-09-14-gutenberg-library-design.md`, as amended by its "Amendments (2026-09-17)" section, which Task 10 writes and which records the facts below. Section 8 (phase 2 semantic search) is out of scope.

## What the real ZIM contains (checked against the scraper source, 2026-09-17)

The 2025-11 `gutenberg_en_all` ZIM was built by gutenberg2zim **3.0.1** (released 2025-11-24). That version writes the layout below; the `books.json` layout the spec's section 2 describes exists only on the scraper's unreleased main branch. Every entry-name rule lives in one place, the top of `api/sos/books.py`, so a later build costs one table edit.

- Catalogue: `full_by_popularity.js` (every book, most downloaded first) and `full_by_title.js`, each `var json_data = [[title, author name, "hep", id, shelf], ...];` where `"hep"` is three `0`/`1` characters for html, epub, pdf, `id` is the numeric Gutenberg id and `shelf` is a Library of Congress class code (`"PR"`, `"Q"`, ... or `""`). No subjects, no subtitle, no author years, no download counts.
- Book entries: `<slug>.<id>.html`, `<slug>.<id>.epub`, `<slug>.<id>.pdf` where `slug = title.strip().replace("/", "-")[:230]`.
- Covers: `covers/<id>_cover_image.jpg` (present only for books that have one; the catalogue does not say which).
- Authors: `authors_lang_en.js` (`[name, gut_id]` pairs) — not needed.
- Front page `Home`; a title index per book that Kiwix suggest searches.

Consequences for the spec: no `subjects` column, no subject chips, no author years; browse chips are LCC **shelves** with names from the scraper's own `en.json` (39 codes); popularity is the book's position in `full_by_popularity.js`; EPUB and cover existence are checked per book against the archive at index time so the API never links to an entry that is not there.

## Global Constraints

- British English in every user-facing string and comment: "licence" not "license", "colour" not "color".
- Never write "NOMAD" anywhere (a project-wide house rule already enforced by existing tests).
- No network access from unit tests. The importer reads a ZIM built in the test session by libzim's writer; the router and search tests seed the tables directly; `respx` mocks any Kiwix call (`api/tests/conftest.py` fixtures `mocks`/`kiwix_mock`).
- `index_books` is a no-op (not an error) when the ZIM is unavailable or its catalogue is missing or malformed; it never raises, and `sos index`'s other steps still run.
- Every new SQL table follows `api/sos/db.py`: appended to the `SCHEMA` string, `CREATE ... IF NOT EXISTS`. `db.connect()` does **not** apply the schema; `db.init_schema(conn)` does (the app calls it at startup).
- `manifest/core.json` and `manifest/extended.json` are one JSON object per line. Edit the target lines as text; never round-trip a whole file through `json.dumps`.
- The real ZIM is downloading to `/home/dan/sos-content/zim/gutenberg_en_all.zim` (aria2c; the `.aria2` control file beside it means "not finished"; the file is preallocated so its size proves nothing). Expected sha256 `01677c8d554a1cab2cbfd020ac99ebca7dd6c74d3ce0d13f266a2ba603dfaf28`. Only Task 10 touches it.
- Python: `api/.venv/bin/python`, tests `cd api && .venv/bin/python -m pytest -q`, lint `api/.venv/bin/ruff check api`. Web: `pnpm --dir web vitest run`, `pnpm --dir web exec tsc --noEmit`.
- Commit after every task with the message given; do not push.

---

## File structure

| File | Responsibility |
|---|---|
| `manifest/core.json`, `manifest/extended.json` | Task 1: move two items between tiers |
| `README.md`, `docs/superpowers/specs/2026-09-03-operation-sos-design.md` | Task 1: 1 TB hardware description |
| `api/tests/test_manifest_content.py` | Task 1: size bounds, core id pins, core category set |
| `api/sos/db.py`, `api/tests/test_db.py` | Task 2: `books`, `fts_books`, `reading` tables |
| `api/sos/books.py` (new) | Task 3: layout table, `ZimReader`, `parse_catalogue`, `index_books`; Task 4: query helpers |
| `api/sos/sync.py`, `api/pyproject.toml` | Task 3: wire `index_books` into `index()`, add `libzim` |
| `api/tests/test_books.py` (new), `api/tests/conftest.py` | Task 3: fixture ZIM + importer tests; Task 4: router tests |
| `api/sos/routers/books.py` (new), `api/sos/main.py` | Task 4: `/api/books`, `/api/books/shelves`, `/api/books/gutenberg/{id}`, `/api/reading*` |
| `api/sos/library.py`, `api/tests/test_library.py` | Task 4: the Gutenberg library card opens `/books` |
| `api/sos/search.py`, `api/tests/test_search.py` | Task 5: `books` result group, no fan-out to the book ZIMs, suggest |
| `web/src/api/results.ts`, `web/src/api/types.ts` | Task 5: group order and the `book` result kind |
| `web/src/api/client.ts`, `web/src/api/types.ts` | Task 6: API methods and types |
| `web/src/screens/Doc.tsx`, `web/src/reader/position.ts` (new) | Task 6: `EpubReader` `memory` prop, `readingPercent` |
| `web/tests/screens/doc.test.tsx`, `web/tests/reader/position.test.ts` (new) | Task 6 |
| `web/src/screens/Book.tsx` (new), `web/src/router.tsx`, `web/tests/screens/book.test.tsx` (new) | Task 7 |
| `web/src/screens/Books.tsx` (new), `web/src/router.tsx`, `web/tests/screens/books.test.tsx` (new) | Task 8 |
| `web/src/screens/Library.tsx`, `web/tests/screens/library.test.tsx` | Task 9: "My books" shelf |
| `docs/superpowers/specs/2026-09-14-gutenberg-library-design.md`, `docs/app-completion.md`, `docs/hardware-checklist.md` | Task 10: spec amendments, the dated entry, the real-ZIM run |

---

### Task 1: Promote Gutenberg and Survivor Library to core; update the hardware story

**Files:**
- Modify: `manifest/extended.json` (lines 3 and 6), `manifest/core.json`
- Modify: `README.md` (hardware table rows "Storage" and "External drive"), `docs/superpowers/specs/2026-09-03-operation-sos-design.md` (lines 10, 73, 77)
- Modify: `api/tests/test_manifest_content.py`
- Test: `api/tests/test_manifest_content.py`

**Interfaces:**
- Produces: `gutenberg_en_all` and `survivorlibrary.com_en_all` are `tier: "core"`, `category: "books"` items in `manifest/core.json`; everything else about them unchanged. Later tasks find them through the `library_items` table.

- [ ] **Step 1: Update the tests first**

In `api/tests/test_manifest_content.py`:

1. Add `"gutenberg_en_all", "survivorlibrary.com_en_all",` to `CORE_REQUIRED` under a comment `# books: the two collections the ereader is for (core since the 1 TB standard, 2026-09-17)`.
2. In `test_core_tier_and_categories`, add `"books"` to the allowed category set.
3. Change `test_core_size_near_target` to `assert 600e9 < total < 850e9, total`.
4. Remove the two ids from `EXTENDED_REQUIRED`.
5. Add:

```python
def test_core_has_the_book_collections():
    core = by_id("core.json")
    for book_zim in ("gutenberg_en_all", "survivorlibrary.com_en_all"):
        assert core[book_zim]["category"] == "books", book_zim
        assert core[book_zim]["dest"] == f"zim/{book_zim}.zim", book_zim
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_manifest_content.py -q`
Expected: FAIL on `test_core_required_ids_present`, `test_core_size_near_target`, `test_core_has_the_book_collections`.

- [ ] **Step 3: Move the two manifest lines**

`grep -n '"gutenberg_en_all"\|"survivorlibrary.com_en_all"' manifest/extended.json` gives the two lines. Delete them from `manifest/extended.json` and append them to `manifest/core.json` as the last two object lines (before the closing bracket line), each with `"tier": "extended"` changed to `"tier": "core"` and nothing else touched. Mind the trailing comma on what was the last line of `core.json`.

- [ ] **Step 4: Run the validator and the test**

Run: `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios` then `cd api && .venv/bin/python -m pytest tests/test_manifest_content.py tests/test_manifest.py -q`
Expected: `OK` and PASS.

- [ ] **Step 5: Update the hardware docs**

`README.md` table: Storage row becomes `| Storage | 1 TB NVMe (2280) on a Pimoroni NVMe Base; boot and core drive, including the two book collections; PCIe Gen 2 (`install.sh --pcie-gen3` opts in) |`; External drive row becomes `| External drive | Optional self-powered USB 3 HDD or SSD, ext4, filesystem label `SOS-EXT`, for Khan Academy, media and your own files |`.

`docs/superpowers/specs/2026-09-03-operation-sos-design.md`: line 10 `500GB NVMe` → `1TB NVMe`; line 73 `500GB NVMe, boot and core drive.` → `1TB NVMe, boot and core drive (the core tier is about 680 GB with the two book collections).`; line 77 `2TB minimum for the full extended list.` → `2TB or more for the full extended list (Khan Academy, media, your own files).`

- [ ] **Step 6: Commit**

```bash
git add manifest/core.json manifest/extended.json README.md docs/superpowers/specs/2026-09-03-operation-sos-design.md api/tests/test_manifest_content.py
git commit -m "content: promote Gutenberg and Survivor Library to the 1 TB core tier"
```

---

### Task 2: `books`, `fts_books` and `reading` tables

**Files:**
- Modify: `api/sos/db.py` (`SCHEMA`)
- Test: `api/tests/test_db.py`

**Interfaces:**
- Produces: `books(zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path, PRIMARY KEY (zim, id))`; `fts_books` (FTS5 over `title, author`, external content on `books`); `reading(key PRIMARY KEY, title, author, cover_url, cfi, percent, updated_at)`.

- [ ] **Step 1: Write the failing test**

Add to `api/tests/test_db.py`, and add `"books", "fts_books", "reading"` to the tuple in `test_schema_creates_every_table`:

```python
def test_books_fts_is_external_content_and_reading_round_trips(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) VALUES "
                 "('gutenberg_en_all', 1342, 'Pride and Prejudice', 'Jane Austen', 'PR', 100, "
                 "'Pride and Prejudice.1342.epub', 'Pride and Prejudice.1342.html', 'covers/1342_cover_image.jpg')")
    conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
    hit = conn.execute("SELECT b.title FROM books b JOIN fts_books f ON f.rowid = b.rowid WHERE fts_books MATCH 'austen'").fetchone()
    assert hit["title"] == "Pride and Prejudice"
    conn.execute("INSERT INTO reading (key, title, author, cover_url, cfi, percent, updated_at) VALUES "
                 "('gutenberg:1342', 'Pride and Prejudice', 'Jane Austen', NULL, 'epubcfi(/6/4!/4/2/2)', 12.5, '2026-09-17T10:00:00Z')")
    assert conn.execute("SELECT percent FROM reading WHERE key='gutenberg:1342'").fetchone()["percent"] == 12.5
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_db.py -q`
Expected: FAIL, `no such table: books`.

- [ ] **Step 3: Add the schema**

Append to `SCHEMA` in `api/sos/db.py`, after the `places_meta` line:

```sql
CREATE TABLE IF NOT EXISTS books (zim TEXT NOT NULL, id INTEGER NOT NULL, title TEXT NOT NULL, author TEXT, shelf TEXT,
  popularity INTEGER NOT NULL DEFAULT 0, epub_path TEXT, html_path TEXT, cover_path TEXT, PRIMARY KEY (zim, id));
CREATE INDEX IF NOT EXISTS books_popularity ON books(zim, popularity DESC);
CREATE INDEX IF NOT EXISTS books_shelf ON books(zim, shelf);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_books USING fts5(title, author, content='books', content_rowid='rowid',
  tokenize='porter unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS reading (key TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, cover_url TEXT, cfi TEXT NOT NULL,
  percent REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
```

- [ ] **Step 4: Run the tests**

Run: `cd api && .venv/bin/python -m pytest tests/test_db.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/sos/db.py api/tests/test_db.py
git commit -m "feat(db): books, fts_books and reading tables for the Gutenberg collection"
```

---

### Task 3: The catalogue importer, `index_books`

**Files:**
- Create: `api/sos/books.py`
- Modify: `api/sos/sync.py` (`index()`), `api/pyproject.toml` (`libzim`)
- Create: `api/tests/test_books.py`
- Modify: `api/tests/conftest.py` (the `books_zim` fixture)

**Interfaces:**
- Consumes: `library_items.available` and `library_items.local_path` (set by `library.refresh_items`).
- Produces: `BOOK_ZIMS = ("gutenberg_en_all",)`; `SHELF_NAMES: dict[str, str]`; `parse_catalogue(raw: bytes) -> list[CatalogueEntry]`; `entry_slug(title) -> str`; `index_books(conn, open_zim=open_zim) -> int` returning the number of books indexed; `ZimReader` protocol with `read(path) -> bytes | None` and `has(path) -> bool`.

- [ ] **Step 1: Add the dependency**

In `api/pyproject.toml` `dependencies`, add `"libzim>=3.7",` after `"jsonschema>=4.22",`. It is already installed in this worktree's venv (`api/.venv/bin/python -c "import libzim.reader"` works); on a fresh venv `api/.venv/bin/pip install -e './api[dev]'` picks it up.

- [ ] **Step 2: The fixture ZIM**

Add to `api/tests/conftest.py`:

```python
BOOKS_CATALOGUE = [
    # [title, author, "hep" flags, id, shelf] -- gutenberg2zim 3.0.1's full_by_popularity.js order (most popular first)
    ["Pride and Prejudice", "Jane Austen", "110", 1342, "PR"],
    ["Moby-Dick; Or, The Whale", "Herman Melville", "111", 2701, "PS"],
    ["The Prince", "Niccolo Machiavelli", "110", 1232, "J"],
    ["Aesop's Fables / A New Translation", "Aesop", "100", 11339, "PA"],
    ["Common Sense", "Thomas Paine", "110", 147, "E"],
    ["A Room with a View", "E. M. Forster", "110", 2641, ""],
]


@pytest.fixture(scope="session")
def books_zim(tmp_path_factory) -> Path:
    """A ZIM in gutenberg2zim 3.0.1's layout: the catalogue as JavaScript, `<slug>.<id>.epub` entries, jpg covers.
    Aesop has no EPUB (flags 100); Common Sense claims one but the entry is missing; The Prince has no cover."""
    from libzim.writer import Creator, Hint, Item, StringProvider

    class _Item(Item):
        def __init__(self, path: str, content: str, mimetype: str):
            self._path, self._content, self._mimetype = path, content, mimetype

        def get_path(self): return self._path
        def get_title(self): return self._path
        def get_mimetype(self): return self._mimetype
        def get_contentprovider(self): return StringProvider(self._content)
        def get_hints(self): return {Hint.FRONT_ARTICLE: False}

    path = tmp_path_factory.mktemp("zim") / "gutenberg_en_all.zim"
    with Creator(str(path)).config_indexing(False, "eng") as creator:
        creator.set_mainpath("Home")
        creator.add_item(_Item("Home", "<html><body>Gutenberg</body></html>", "text/html"))
        creator.add_item(_Item("full_by_popularity.js", "var json_data = " + json.dumps(BOOKS_CATALOGUE) + ";", "text/javascript"))
        for title, _author, flags, book_id, _shelf in BOOKS_CATALOGUE:
            slug = title.strip().replace("/", "-")[:230]
            creator.add_item(_Item(f"{slug}.{book_id}.html", f"<html><body>{title}</body></html>", "text/html"))
            if flags[1] == "1" and book_id != 147:
                creator.add_item(_Item(f"{slug}.{book_id}.epub", "PK-not-really-an-epub", "application/epub+zip"))
            if book_id != 1232:
                creator.add_item(_Item(f"covers/{book_id}_cover_image.jpg", "JPEG", "image/jpeg"))
    return path
```

(`import json` and `from pathlib import Path` are already at the top of conftest or need adding; check.)

- [ ] **Step 3: Write the failing tests**

Create `api/tests/test_books.py`:

```python
"""index_books against a ZIM in the real scraper's layout (built by the books_zim fixture), and the catalogue parser."""
import logging
from pathlib import Path

import pytest

from sos import books, db
from sos.books import BOOK_ZIMS, entry_slug, index_books, parse_catalogue


def _conn(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    return conn


def _add_item(conn, zim_path: Path | None, available: int = 1, item_id: str = "gutenberg_en_all"):
    conn.execute(
        "INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
        "VALUES (?, 'Project Gutenberg (English)', 'zim', 'core', 'books', ?, 100, ?, ?)",
        (item_id, f"zim/{item_id}.zim", available, str(zim_path) if zim_path else None))
    conn.commit()


def test_entry_slug_matches_the_scraper():
    assert entry_slug("Aesop's Fables / A New Translation") == "Aesop's Fables - A New Translation"
    assert entry_slug("  Padded  ") == "Padded"
    assert len(entry_slug("x" * 300)) == 230


def test_parse_catalogue_reads_the_javascript_array():
    raw = b'var json_data = [["Pride and Prejudice", "Jane Austen", "110", 1342, "PR"], ["No Shelf", "", "100", 5, ""]];'
    rows = parse_catalogue(raw)
    assert rows[0] == books.CatalogueEntry(title="Pride and Prejudice", author="Jane Austen", flags="110", id=1342, shelf="PR")
    assert rows[1].author == "" and rows[1].shelf == ""


@pytest.mark.parametrize("raw", [b"", b"var json_data = ;", b"var json_data = [[1]];", b"var json_data = {};"])
def test_parse_catalogue_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_catalogue(raw)


def test_index_books_populates_books_and_fts(tmp_path, books_zim):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    assert index_books(conn) == 6
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM books WHERE zim='gutenberg_en_all'")}
    assert rows[1342]["title"] == "Pride and Prejudice" and rows[1342]["author"] == "Jane Austen" and rows[1342]["shelf"] == "PR"
    assert rows[1342]["epub_path"] == "Pride and Prejudice.1342.epub"
    assert rows[1342]["html_path"] == "Pride and Prejudice.1342.html"
    assert rows[1342]["cover_path"] == "covers/1342_cover_image.jpg"
    assert rows[1342]["popularity"] == 6 and rows[2641]["popularity"] == 1   # position in full_by_popularity.js
    assert rows[11339]["epub_path"] is None                                  # flags say html only
    assert rows[11339]["html_path"] == "Aesop's Fables - A New Translation.11339.html"
    assert rows[147]["epub_path"] is None                                    # flagged, but the entry is not in the ZIM
    assert rows[1232]["cover_path"] is None                                  # no cover entry
    assert rows[2641]["shelf"] is None and rows[2641]["author"] == "E. M. Forster"
    hit = conn.execute("SELECT b.title FROM books b JOIN fts_books f ON f.rowid=b.rowid WHERE fts_books MATCH 'austen'").fetchone()
    assert hit["title"] == "Pride and Prejudice"


def test_index_books_is_a_noop_without_the_zim(tmp_path, books_zim):
    conn = _conn(tmp_path)
    assert index_books(conn) == 0                       # not in library_items at all
    _add_item(conn, None, available=0)
    assert index_books(conn) == 0                       # listed, not on the box
    assert conn.execute("SELECT count(*) AS n FROM books").fetchone()["n"] == 0


def test_index_books_warns_and_keeps_the_tables_on_a_bad_catalogue(tmp_path, books_zim, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    index_books(conn)

    class Broken:
        def read(self, path): return b"var json_data = nonsense;"
        def has(self, path): return False

    with caplog.at_level(logging.WARNING):
        assert index_books(conn, open_zim=lambda p: Broken()) == 0
    assert "gutenberg_en_all" in caplog.text
    assert conn.execute("SELECT count(*) AS n FROM books").fetchone()["n"] == 6


def test_index_books_warns_when_the_catalogue_entry_is_missing(tmp_path, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, Path("/nonexistent.zim"))

    class Empty:
        def read(self, path): return None
        def has(self, path): return False

    with caplog.at_level(logging.WARNING):
        assert index_books(conn, open_zim=lambda p: Empty()) == 0
    assert "full_by_popularity.js" in caplog.text


def test_index_books_survives_an_unreadable_file(tmp_path, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, tmp_path / "missing.zim")
    with caplog.at_level(logging.WARNING):
        assert index_books(conn) == 0
    assert "gutenberg_en_all" in caplog.text


def test_index_books_rerun_replaces_rows_and_leaves_no_stale_fts(tmp_path, books_zim):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    index_books(conn)

    class OneBook:
        def read(self, path): return b'var json_data = [["Only Book", "Nobody", "110", 9, ""]];'
        def has(self, path): return False

    assert index_books(conn, open_zim=lambda p: OneBook()) == 1
    assert conn.execute("SELECT count(*) AS n FROM books").fetchone()["n"] == 1
    assert conn.execute("SELECT count(*) AS n FROM fts_books WHERE fts_books MATCH 'austen'").fetchone()["n"] == 0
    assert conn.execute("SELECT b.title FROM books b JOIN fts_books f ON f.rowid=b.rowid WHERE fts_books MATCH 'only'").fetchone()["title"] == "Only Book"


def test_book_zims_is_the_gutenberg_collection():
    assert BOOK_ZIMS == ("gutenberg_en_all",)
```

- [ ] **Step 4: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_books.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'sos.books'`.

- [ ] **Step 5: Write `api/sos/books.py`**

```python
"""The Gutenberg catalogue (spec section 4 as amended 2026-09-17).

`index_books` opens a book ZIM straight from disk with libzim and rewrites the books/fts_books tables from the
scraper's own catalogue entry; the query helpers below are what the /api/books router serves. Read-only against
the ZIM. Every entry-name rule of the scraper's layout is in the constants at the top: a later gutenberg2zim
release that moves to its JSON layout costs a change here, not a redesign.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import quote

log = logging.getLogger(__name__)

BOOK_ZIMS = ("gutenberg_en_all",)

# gutenberg2zim 3.0.1 (the scraper behind the 2025-11 build) writes the catalogue as JavaScript: one array per book,
# [title, author name, "hep" (html/epub/pdf as 0 or 1), Gutenberg id, Library of Congress shelf code], most
# downloaded first. Book entries are named <slug>.<id>.<format>; covers are covers/<id>_cover_image.jpg.
CATALOGUE_ENTRY = "full_by_popularity.js"
COVER_ENTRIES = ("covers/{id}_cover_image.jpg", "covers/{id}_cover_image.webp")
SLUG_MAX = 230

# The scraper's own shelf names (locales/en.json, the "lcc-shelf-*" strings), the dash prefix dropped.
SHELF_NAMES = {
    "A": "General works", "B": "Philosophy, psychology, religion", "C": "Auxiliary sciences of history",
    "D": "World history", "E": "History of the Americas", "F": "History of the Americas (local)",
    "G": "Geography, anthropology, recreation", "H": "Social sciences", "J": "Political science", "K": "Law",
    "L": "Education", "M": "Music", "N": "Fine arts", "P": "Language and literature", "Q": "Science", "R": "Medicine",
    "S": "Agriculture", "T": "Technology", "U": "Military science", "V": "Naval science",
    "Z": "Bibliography and library science",
    "PA": "Greek and Latin literature", "PB": "Modern and Celtic languages", "PC": "Romance languages",
    "PD": "Germanic and Scandinavian languages", "PE": "English language", "PF": "West Germanic languages",
    "PG": "Slavic, Baltic and Albanian languages", "PH": "Uralic and Basque languages",
    "PJ": "Oriental languages and literatures", "PK": "Indo-Iranian languages and literatures",
    "PL": "Languages and literatures of Eastern Asia, Africa and Oceania", "PM": "Indigenous and artificial languages",
    "PN": "Literature (general)", "PQ": "French, Italian, Spanish and Portuguese literature", "PR": "English literature",
    "PS": "American literature", "PT": "German, Dutch and Scandinavian literature",
    "PZ": "Fiction and children's books",
}


@dataclass(frozen=True)
class CatalogueEntry:
    title: str
    author: str
    flags: str
    id: int
    shelf: str

    @property
    def has_html(self) -> bool:
        return self.flags[0:1] == "1"

    @property
    def has_epub(self) -> bool:
        return self.flags[1:2] == "1"


class ZimReader(Protocol):
    def read(self, path: str) -> bytes | None: ...
    def has(self, path: str) -> bool: ...


class LibzimReader:
    """The real thing: libzim's Archive over the file on disk."""

    def __init__(self, path: Path) -> None:
        from libzim.reader import Archive

        self._archive = Archive(str(path))

    def read(self, path: str) -> bytes | None:
        if not self._archive.has_entry_by_path(path):
            return None
        return bytes(self._archive.get_entry_by_path(path).get_item().content)

    def has(self, path: str) -> bool:
        return self._archive.has_entry_by_path(path)


def open_zim(path: Path) -> ZimReader:
    return LibzimReader(path)


def entry_slug(title: str) -> str:
    """The scraper's `book_name_for_fs`: the title with slashes made dashes, cut at 230 characters."""
    return title.strip().replace("/", "-")[:SLUG_MAX]


def parse_catalogue(raw: bytes) -> list[CatalogueEntry]:
    text = raw.decode("utf-8")
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("no JSON array in the catalogue")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("catalogue is not a list")
    out: list[CatalogueEntry] = []
    for entry in data:
        if not isinstance(entry, list) or len(entry) < 4:
            raise ValueError(f"malformed catalogue row: {entry!r}")
        title, author, flags, book_id = entry[0], entry[1], entry[2], entry[3]
        shelf = entry[4] if len(entry) > 4 and entry[4] else ""
        out.append(CatalogueEntry(title=str(title), author=str(author or ""), flags=str(flags), id=int(book_id), shelf=str(shelf)))
    return out


def index_books(conn: sqlite3.Connection, open_zim: Callable[[Path], ZimReader] = open_zim) -> int:
    """Rewrite books/fts_books for every BOOK_ZIMS item that is on the box. Returns the number of books indexed.
    A ZIM that is absent, unreadable or has no usable catalogue is a warning that leaves the tables as they were;
    `sos index` carries on either way."""
    total = 0
    for zim in BOOK_ZIMS:
        row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (zim,)).fetchone()
        if row is None or not row["available"] or not row["local_path"]:
            continue
        try:
            reader = open_zim(Path(row["local_path"]))
            raw = reader.read(CATALOGUE_ENTRY)
            if raw is None:
                log.warning("index_books: %s: no %s entry in the ZIM (a different scraper layout?)", zim, CATALOGUE_ENTRY)
                continue
            entries = parse_catalogue(raw)
        except (OSError, RuntimeError, ValueError, UnicodeDecodeError) as exc:
            log.warning("index_books: %s: could not read the catalogue: %s", zim, exc)
            continue
        count = len(entries)
        rows: list[tuple] = []
        missing_epubs = 0
        for position, entry in enumerate(entries):
            slug = entry_slug(entry.title)
            html_path = f"{slug}.{entry.id}.html" if entry.has_html else None
            epub_path = f"{slug}.{entry.id}.epub" if entry.has_epub else None
            if epub_path and not reader.has(epub_path):
                missing_epubs += 1
                epub_path = None
            cover_path = next((c.format(id=entry.id) for c in COVER_ENTRIES if reader.has(c.format(id=entry.id))), None)
            rows.append((zim, entry.id, entry.title, entry.author or None, entry.shelf or None, count - position,
                         epub_path, html_path, cover_path))
        with conn:
            conn.execute("DELETE FROM books WHERE zim=?", (zim,))
            conn.executemany(
                "INSERT OR REPLACE INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) "
                "VALUES (?,?,?,?,?,?,?,?,?)", rows)
            # External-content FTS5 does not follow deletes on its content table: rebuild the index from `books`.
            conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
        log.info("index: %d books from %s (%d flagged EPUBs missing)", len(rows), zim, missing_epubs)
        total += len(rows)
    return total
```

- [ ] **Step 6: Run the tests**

Run: `cd api && .venv/bin/python -m pytest tests/test_books.py -q`
Expected: PASS.

- [ ] **Step 7: Wire into `sos index`**

In `api/sos/sync.py`, add `from sos import books as books_mod` to the imports (matching the `docs_mod`/`places_mod` style), and in `index()` after the `imported = places_mod.import_places(...)` line add `n_books = books_mod.index_books(conn)`. Extend the `out(...)` line to end `..., places {places_txt}, {n_books} books")` and add `"books": n_books` to the returned dict.

Add a test to `api/tests/test_sync.py` (read it first; it has `index` tests using `env`): 

```python
def test_index_reports_books(env, books_zim):
    """index() counts the Gutenberg books when the ZIM is on the box, and reports 0 without it."""
    from sos import sync
    assert sync.index(env, out=lambda *_: None)["books"] == 0
    conn = db.connect(env.db_path)
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority) VALUES "
                 "('gutenberg_en_all', 'Project Gutenberg', 'zim', 'core', 'books', 'zim/gutenberg_en_all.zim', 100)")
    conn.commit()
    conn.close()
    shutil.copy(books_zim, env.core / "zim" / "gutenberg_en_all.zim")
    ...
```

Stop: `index()` calls `library.upsert_items` from the manifest first, which deletes rows not in the fixture manifest, so the inserted row would vanish. Instead assert only the 0 case in `test_sync.py` (`assert sync.index(env, out=lambda *_: None)["books"] == 0`) and rely on `test_books.py` for the populated path.

- [ ] **Step 8: Run the backend suite and ruff**

Run: `cd api && .venv/bin/python -m pytest -q && .venv/bin/ruff check .`
Expected: all pass, ruff clean.

- [ ] **Step 9: Commit**

```bash
git add api/sos/books.py api/sos/sync.py api/pyproject.toml api/tests/test_books.py api/tests/conftest.py api/tests/test_sync.py
git commit -m "feat(books): index_books reads the Gutenberg catalogue from the ZIM into books/fts_books"
```

---

### Task 4: Query helpers, the books router, the library card

**Files:**
- Modify: `api/sos/books.py` (query helpers)
- Create: `api/sos/routers/books.py`
- Modify: `api/sos/main.py` (register), `api/sos/library.py` (`reader_url`)
- Test: `api/tests/test_books.py` (router tests), `api/tests/test_library.py`

**Interfaces:**
- Produces:
  - `GET /api/books?q=&author=&shelf=&sort=popular|title&limit=40&offset=0` → `{"items": [BookSummary], "total": int, "available": bool}`; `total` counts the filtered set.
  - `GET /api/books/shelves` → `[{"code", "name", "count"}]`, most books first.
  - `GET /api/books/gutenberg/{id}` → BookSummary plus `available` and `position` (`{"cfi", "percent"}` or null); 404 when not catalogued.
  - `GET /api/reading` → `[ReadingEntry]` newest first; `GET /api/reading/{key}` → one or 404; `PUT /api/reading/{key}` body `{title, author, cover_url, cfi, percent}`; `DELETE /api/reading/{key}`.
  - BookSummary = `{id, title, author, shelf, shelf_name, popularity, cover_url, epub_url, html_url}` where `cover_url`/`epub_url` are `/kiwix/content/<zim>/<quoted path>` (kiwix-serve serves non-HTML entries as-is) and `html_url` is the app's reader route `/read/<zim>/<quoted path>`.
  - ReadingEntry = `{key, title, author, cover_url, url, cfi, percent, updated_at}` where `url` is `/book/gutenberg/<id>` for a `gutenberg:<id>` key and `/doc/<id>` for a `doc:<id>` key.
  - `library.reader_url` returns `/books` for an available item whose id is in `BOOK_ZIMS`.

- [ ] **Step 1: Write the failing router tests**

Append to `api/tests/test_books.py`:

```python
@pytest.fixture
def populated(client, env, books_zim):
    """The app's own database, with the Gutenberg item on the box and the fixture catalogue indexed."""
    conn = db.connect(env.db_path)
    _add_item(conn, books_zim)
    index_books(conn)
    conn.close()
    return client


def test_books_lists_by_popularity_and_pages(populated):
    r = populated.get("/api/books")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True and body["total"] == 6
    assert [b["title"] for b in body["items"]][:2] == ["Pride and Prejudice", "Moby-Dick; Or, The Whale"]
    first = body["items"][0]
    assert first["epub_url"] == "/kiwix/content/gutenberg_en_all/Pride%20and%20Prejudice.1342.epub"
    assert first["html_url"] == "/read/gutenberg_en_all/Pride%20and%20Prejudice.1342.html"
    assert first["cover_url"] == "/kiwix/content/gutenberg_en_all/covers/1342_cover_image.jpg"
    assert first["shelf"] == "PR" and first["shelf_name"] == "English literature"
    page = populated.get("/api/books", params={"limit": 2, "offset": 2}).json()
    assert [b["id"] for b in page["items"]] == [1232, 11339] and page["total"] == 6


def test_books_search_ranks_a_title_hit_first_and_counts_the_matches(populated):
    body = populated.get("/api/books", params={"q": "prince"}).json()
    assert body["total"] == 1 and body["items"][0]["title"] == "The Prince"
    body = populated.get("/api/books", params={"q": "austen"}).json()
    assert body["items"][0]["id"] == 1342


def test_books_filters_by_shelf_and_author_and_sorts_by_title(populated):
    assert [b["id"] for b in populated.get("/api/books", params={"shelf": "PR"}).json()["items"]] == [1342]
    assert [b["id"] for b in populated.get("/api/books", params={"author": "Aesop"}).json()["items"]] == [11339]
    titles = [b["title"] for b in populated.get("/api/books", params={"sort": "title"}).json()["items"]]
    assert titles == sorted(titles, key=str.lower)


def test_books_is_empty_and_unavailable_without_the_zim(client):
    assert client.get("/api/books").json() == {"items": [], "total": 0, "available": False}
    assert client.get("/api/books/shelves").json() == []


def test_book_shelves_carry_names_and_counts(populated):
    shelves = populated.get("/api/books/shelves").json()
    assert shelves[0]["count"] == 1 and {s["code"] for s in shelves} == {"PR", "PS", "J", "PA", "E"}
    assert next(s for s in shelves if s["code"] == "J")["name"] == "Political science"


def test_one_book_with_and_without_an_epub(populated):
    r = populated.get("/api/books/gutenberg/1342")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Pride and Prejudice" and body["available"] is True and body["position"] is None
    aesop = populated.get("/api/books/gutenberg/11339").json()
    assert aesop["epub_url"] is None
    assert aesop["html_url"] == "/read/gutenberg_en_all/Aesop%27s%20Fables%20-%20A%20New%20Translation.11339.html"
    assert populated.get("/api/books/gutenberg/999").status_code == 404


def test_one_book_says_unavailable_when_the_zim_has_gone(populated, env):
    conn = db.connect(env.db_path)
    conn.execute("UPDATE library_items SET available=0 WHERE id='gutenberg_en_all'")
    conn.commit()
    conn.close()
    assert populated.get("/api/books/gutenberg/1342").json()["available"] is False


def test_reading_round_trips_newest_first_and_links_each_key(client):
    client.put("/api/reading/gutenberg:1342", json={"title": "Pride and Prejudice", "author": "Jane Austen",
                                                     "cover_url": "/c1.jpg", "cfi": "epubcfi(/6/4)", "percent": 10.0})
    client.put("/api/reading/doc:where-there-is-no-doctor", json={"title": "Where There Is No Doctor", "author": None,
                                                                   "cover_url": None, "cfi": "epubcfi(/6/8)", "percent": 40.0})
    rows = client.get("/api/reading").json()
    assert [r["key"] for r in rows] == ["doc:where-there-is-no-doctor", "gutenberg:1342"]
    assert rows[0]["url"] == "/doc/where-there-is-no-doctor" and rows[1]["url"] == "/book/gutenberg/1342"
    one = client.get("/api/reading/gutenberg:1342")
    assert one.status_code == 200 and one.json()["percent"] == 10.0
    client.put("/api/reading/gutenberg:1342", json={"title": "Pride and Prejudice", "author": "Jane Austen",
                                                     "cover_url": "/c1.jpg", "cfi": "epubcfi(/6/6)", "percent": 20.0})
    assert [r["key"] for r in client.get("/api/reading").json()][0] == "gutenberg:1342"   # an update is a fresh read
    assert client.delete("/api/reading/gutenberg:1342").status_code == 200
    assert client.get("/api/reading/gutenberg:1342").status_code == 404
    assert client.get("/api/reading").json()[0]["key"] == "doc:where-there-is-no-doctor"


def test_one_book_shows_its_saved_position(populated):
    populated.put("/api/reading/gutenberg:1342", json={"title": "Pride and Prejudice", "author": "Jane Austen",
                                                        "cover_url": None, "cfi": "epubcfi(/6/4!/4/2/2)", "percent": 12.5})
    assert populated.get("/api/books/gutenberg/1342").json()["position"] == {"cfi": "epubcfi(/6/4!/4/2/2)", "percent": 12.5}
```

Note: `updated_at` must be strictly increasing across two writes in the same second, so the router orders by `updated_at DESC, rowid DESC` and the reading table's `updated_at` uses microseconds. Also add to `api/tests/test_library.py::test_reader_urls` (after inserting a books row into that test's `conn`):

```python
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available) VALUES "
                 "('gutenberg_en_all', 'Project Gutenberg', 'zim', 'core', 'books', 'zim/gutenberg_en_all.zim', 100, 1)")
    gut = conn.execute("SELECT * FROM library_items WHERE id='gutenberg_en_all'").fetchone()
    assert library.reader_url(gut) == "/books"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_books.py tests/test_library.py -q`
Expected: the new router tests FAIL with 404s; the library test fails on `/books`.

- [ ] **Step 3: Query helpers in `api/sos/books.py`**

Append:

```python
def available_zim(conn: sqlite3.Connection) -> str | None:
    for zim in BOOK_ZIMS:
        row = conn.execute("SELECT available FROM library_items WHERE id=?", (zim,)).fetchone()
        if row is not None and row["available"]:
            return zim
    return None


def content_url(zim: str, path: str | None) -> str | None:
    return f"/kiwix/content/{zim}/{quote(path, safe='/')}" if path else None


def reader_url(zim: str, path: str | None) -> str | None:
    return f"/read/{zim}/{quote(path, safe='/')}" if path else None


def summary(row: sqlite3.Row) -> dict:
    shelf = row["shelf"]
    return {
        "id": row["id"], "title": row["title"], "author": row["author"], "shelf": shelf,
        "shelf_name": SHELF_NAMES.get(shelf) if shelf else None, "popularity": row["popularity"],
        "cover_url": content_url(row["zim"], row["cover_path"]), "epub_url": content_url(row["zim"], row["epub_path"]),
        "html_url": reader_url(row["zim"], row["html_path"]),
    }


def list_books(conn: sqlite3.Connection, zim: str, *, q: str = "", author: str = "", shelf: str = "",
               sort: str = "popular", limit: int = 40, offset: int = 0) -> tuple[list[dict], int]:
    from sos import query as query_mod

    limit = max(1, min(int(limit or 40), 100))
    offset = max(0, int(offset or 0))
    terms = query_mod.reduce_query(q or "").terms
    clauses, params = ["b.zim = ?"], [zim]
    if author:
        clauses.append("b.author = ?"); params.append(author)
    if shelf:
        clauses.append("b.shelf = ?"); params.append(shelf)
    where = " AND ".join(clauses)
    if terms:
        match = query_mod.fts_match(terms, "and")
        sql_from = f"FROM books b JOIN fts_books f ON f.rowid = b.rowid WHERE fts_books MATCH ? AND {where}"
        params = [match, *params]
        order = "bm25(fts_books, 5.0, 3.0), b.popularity DESC"
    else:
        sql_from = f"FROM books b WHERE {where}"
        order = "b.title COLLATE NOCASE ASC" if sort == "title" else "b.popularity DESC"
    total = conn.execute(f"SELECT count(*) AS n {sql_from}", params).fetchone()["n"]
    rows = conn.execute(f"SELECT b.* {sql_from} ORDER BY {order} LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
    return [summary(r) for r in rows], total


def shelves(conn: sqlite3.Connection, zim: str) -> list[dict]:
    rows = conn.execute("SELECT shelf, count(*) AS n FROM books WHERE zim=? AND shelf IS NOT NULL GROUP BY shelf "
                        "ORDER BY n DESC, shelf", (zim,)).fetchall()
    return [{"code": r["shelf"], "name": SHELF_NAMES.get(r["shelf"], r["shelf"]), "count": r["n"]} for r in rows]


def get_book(conn: sqlite3.Connection, zim: str, book_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM books WHERE zim=? AND id=?", (zim, book_id)).fetchone()
    return summary(row) if row else None


def reading_url(key: str) -> str | None:
    kind, _, rest = key.partition(":")
    if kind == "gutenberg" and rest.isdigit():
        return f"/book/gutenberg/{rest}"
    if kind == "doc" and rest:
        return f"/doc/{quote(rest)}"
    return None
```

(`sos.query.reduce_query` and `fts_match` are the existing helpers `search.py` uses.)

- [ ] **Step 4: The router**

Create `api/sos/routers/books.py`:

```python
"""The Gutenberg catalogue and the reading-position table (spec sections 4 and 7)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sos import books
from sos.routers import get_db

router = APIRouter(tags=["books"])


@router.get("/books")
def list_books(q: str = "", author: str = "", shelf: str = "", sort: str = "popular", limit: int = 40, offset: int = 0,
               conn=Depends(get_db)):
    zim = books.available_zim(conn)
    if zim is None:
        return {"items": [], "total": 0, "available": False}
    items, total = books.list_books(conn, zim, q=q, author=author, shelf=shelf, sort=sort, limit=limit, offset=offset)
    return {"items": items, "total": total, "available": True}


@router.get("/books/shelves")
def book_shelves(conn=Depends(get_db)):
    zim = books.available_zim(conn)
    return books.shelves(conn, zim) if zim else []


@router.get("/books/gutenberg/{book_id}")
def get_book(book_id: int, conn=Depends(get_db)):
    zim = books.BOOK_ZIMS[0]
    body = books.get_book(conn, zim, book_id)
    if body is None:
        raise HTTPException(status_code=404, detail="Book not found")
    body["available"] = books.available_zim(conn) == zim
    pos = conn.execute("SELECT cfi, percent FROM reading WHERE key=?", (f"gutenberg:{book_id}",)).fetchone()
    body["position"] = {"cfi": pos["cfi"], "percent": pos["percent"]} if pos else None
    return body


class ReadingBody(BaseModel):
    title: str = Field(min_length=1)
    author: str | None = None
    cover_url: str | None = None
    cfi: str = Field(min_length=1)
    percent: float = Field(ge=0, le=100)


def _entry(row) -> dict:
    return {**dict(row), "url": books.reading_url(row["key"])}


@router.get("/reading")
def list_reading(conn=Depends(get_db)):
    return [_entry(r) for r in conn.execute("SELECT * FROM reading ORDER BY updated_at DESC, rowid DESC").fetchall()]


@router.get("/reading/{key}")
def get_reading(key: str, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM reading WHERE key=?", (key,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Nothing saved for this book")
    return _entry(row)


@router.put("/reading/{key}")
def put_reading(key: str, body: ReadingBody, conn=Depends(get_db)):
    conn.execute(
        "INSERT INTO reading (key, title, author, cover_url, cfi, percent, updated_at) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET title=excluded.title, author=excluded.author, cover_url=excluded.cover_url, "
        "cfi=excluded.cfi, percent=excluded.percent, updated_at=excluded.updated_at",
        (key, body.title, body.author, body.cover_url, body.cfi, body.percent, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return {"ok": True}


@router.delete("/reading/{key}")
def delete_reading(key: str, conn=Depends(get_db)):
    conn.execute("DELETE FROM reading WHERE key=?", (key,))
    conn.commit()
    return {"ok": True}
```

Register in `api/sos/main.py`: add `from sos.routers import books as books_router` beside the other `as` imports and `books_router.router` to the tuple in the `include_router` loop.

In `api/sos/library.py`, import `from sos.books import BOOK_ZIMS` and make `reader_url` return `"/books"` when `row["kind"] == "zim" and row["id"] in BOOK_ZIMS` (before the generic zim branch).

- [ ] **Step 5: Run, then the whole suite**

Run: `cd api && .venv/bin/python -m pytest tests/test_books.py tests/test_library.py -q && .venv/bin/python -m pytest -q && .venv/bin/ruff check .`
Expected: PASS, clean.

- [ ] **Step 6: Commit**

```bash
git add api/sos/books.py api/sos/routers/books.py api/sos/main.py api/sos/library.py api/tests/test_books.py api/tests/test_library.py
git commit -m "feat(api): the books catalogue, one-book and reading-position endpoints"
```

---

### Task 5: Search integration

**Files:**
- Modify: `api/sos/search.py`, `web/src/api/results.ts`, `web/src/api/types.ts`
- Test: `api/tests/test_search.py`

**Interfaces:**
- Produces: results with `source: "books"`, `badge: "Books"`, `kind: "book"`, `url: /book/gutenberg/<id>`, `snippet: "<author> · <shelf name>"`, `score: score(BOOK_WEIGHT=0.6, rank)`; `CLASS_TITLES["books"] = "Books"`; `classify()` returns `"books"` for a core item in category `books`; the Kiwix fan-out never includes an id in `BOOK_ZIMS`; `suggest()` adds up to 3 catalogue titles. Frontend `ORDER` gets `'books'` after `'reference'`.

Honest note on scores: `score = w/(5+rank)`, so a book at rank 1 (0.1) sits above a guide at rank 5 or worse in the flat list. The Books group renders below the guidance groups because `results.ts` orders groups by `ORDER`, not by score. The AI answerer (`ai.py` `run_search`) takes the flat list, so the low weight still matters there.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_search.py` (its `conn` fixture already seeds fts_docs and Kiwix items):

```python
def _seed_books(conn):
    conn.execute("INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, fts) VALUES "
                 "('gutenberg_en_all', 'Project Gutenberg', 'zim', 'core', 'books', 'zim/gutenberg_en_all.zim', 100, 1, 1)")
    conn.executemany("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) VALUES "
                     "('gutenberg_en_all', ?, ?, ?, ?, ?, ?, ?, NULL)", [
        (1232, "The Prince", "Niccolo Machiavelli", "J", 4, "The Prince.1232.epub", "The Prince.1232.html"),
        (2701, "Water Babies", "Charles Kingsley", "PR", 3, "Water Babies.2701.epub", "Water Babies.2701.html"),
    ])
    conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
    conn.commit()


@respx.mock(base_url=BASE)
def test_books_group_sits_in_the_results_with_its_own_badge_and_url(respx_mock, conn, env):
    _seed_books(conn)
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    hits = [r for r in resp["results"] if r["source"] == "books"]
    assert hits and hits[0]["title"] == "Water Babies" and hits[0]["url"] == "/book/gutenberg/2701"
    assert hits[0]["badge"] == "Books" and hits[0]["kind"] == "book" and hits[0]["snippet"] == "Charles Kingsley · English literature"
    assert hits[0]["score"] == pytest.approx(search.score(search.BOOK_WEIGHT, 1))
    assert {"source": "books", "badge": "Books", "count": 1} in resp["groups"]
    # the Gutenberg ZIM is flagged fts=1 above, but the box never fans a Kiwix search out to it
    assert route.call_count == 2
    assert all("gutenberg_en_all" not in str(call.request.url) for call in route.calls)


def test_classify_puts_core_book_zims_in_their_own_class():
    assert search.classify({"tier": "core", "category": "books", "id": "survivorlibrary.com_en_all"}) == "books"


@respx.mock(base_url=BASE, assert_all_called=False)
def test_suggest_offers_catalogue_titles(respx_mock, conn, env):
    _seed_books(conn)
    out = _run(search.suggest(conn, env, KiwixClient(BASE), "prin"))
    assert {"value": "The Prince", "label": "The Prince — Niccolo Machiavelli", "url": "/book/gutenberg/1232", "source": "Book"} in out
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && .venv/bin/python -m pytest tests/test_search.py -q`
Expected: the three new tests FAIL.

- [ ] **Step 3: Implement**

In `api/sos/search.py`:

1. `from sos.books import BOOK_ZIMS, SHELF_NAMES` and `BOOK_WEIGHT = 0.6` beside `PLACE_WEIGHT`.
2. `CLASS_TITLES["books"] = "Books"` (add `"books": "Books",` to the dict) and `KIND_BADGES["book"] = "Book"`.
3. In `classify`, before the `reference/practical/survival` line: `if cat == "books": return "books"`.
4. In `search()`'s fan-out loop, skip book ZIMs: right after `for row in conn.execute("SELECT * FROM library_items WHERE kind='zim' AND available=1 AND fts=1 ...")` add `if row["id"] in BOOK_ZIMS: continue  # the catalogue below is the Gutenberg search; its ZIM has no article text worth an HTTP round trip`.
5. After the `fts_docs` loop (before the places loop) add:

```python
    book_rows = conn.execute(
        "SELECT b.id, b.title, b.author, b.shelf FROM books b JOIN fts_books f ON f.rowid = b.rowid "
        "WHERE fts_books MATCH ? ORDER BY bm25(fts_books, 5.0, 3.0), b.popularity DESC LIMIT 10",
        (query_mod.fts_match(reduced.terms, fts_mode),)).fetchall()
    for rank, row in enumerate(book_rows, 1):
        shelf = SHELF_NAMES.get(row["shelf"] or "")
        results.append({
            "source": "books", "badge": "Books", "title": row["title"],
            "snippet": " · ".join(filter(None, [row["author"], shelf])),
            "url": f"/book/gutenberg/{row['id']}", "score": score(BOOK_WEIGHT, rank), "kind": "book", "_cat": "books",
        })
```

6. In `suggest()`, after the `fts_docs` loop inside `if tokens:` add:

```python
        for r in conn.execute(
            "SELECT b.id, b.title, b.author FROM books b JOIN fts_books f ON f.rowid = b.rowid "
            "WHERE fts_books MATCH ? ORDER BY bm25(fts_books, 5.0, 3.0), b.popularity DESC LIMIT 3", (match,)).fetchall():
            label = f"{r['title']} — {r['author']}" if r["author"] else r["title"]
            out.append({"value": r["title"], "label": label, "url": f"/book/gutenberg/{r['id']}", "source": "Book"})
```

The `books` search results are filtered by the `sources` parameter like any other source, so nothing else changes.

7. `web/src/api/results.ts`: `ORDER` becomes `['places', 'docs', 'nhs', 'medical', 'library', 'practical', 'survival', 'reference', 'books', 'uk-official', 'extended']`.
8. `web/src/api/types.ts`: add `'book'` to `SearchResult['kind']`.

- [ ] **Step 4: Run**

Run: `cd api && .venv/bin/python -m pytest tests/test_search.py tests/test_api.py -q && .venv/bin/ruff check . && pnpm --dir web exec tsc --noEmit && pnpm --dir web vitest run tests/api`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/sos/search.py api/tests/test_search.py web/src/api/results.ts web/src/api/types.ts
git commit -m "feat(search): a Books group from the catalogue, ranked below guidance, never fanning out to the ZIM"
```

---

### Task 6: Position memory in the EPUB reader

**Files:**
- Create: `web/src/reader/position.ts`, `web/tests/reader/position.test.ts`
- Modify: `web/src/api/types.ts`, `web/src/api/client.ts`, `web/src/screens/Doc.tsx`
- Test: `web/tests/screens/doc.test.tsx`

**Interfaces:**
- Produces: types `BookSummary`, `BookDetail`, `BooksResponse`, `BookShelf`, `ReadingEntry`, `EpubMemory`; client methods `books`, `bookShelves`, `book`, `reading`, `getReading` (404 → `null`), `putReading`, `deleteReading`; `readingPercent(loc, spineLength)`; `EpubReader` exported with a new optional prop `memory?: EpubMemory` = `{ key, title, author, coverUrl, startCfi }`; `SAVE_DELAY_MS = 2000`.

- [ ] **Step 1: Types and client**

In `web/src/api/types.ts` add:

```typescript
export type BookSummary = {
  id: number; title: string; author: string | null; shelf: string | null; shelf_name: string | null; popularity: number;
  cover_url: string | null; epub_url: string | null; html_url: string | null;
};
export type BookDetail = BookSummary & { available: boolean; position: { cfi: string; percent: number } | null };
export type BooksResponse = { items: BookSummary[]; total: number; available: boolean };
export type BookShelf = { code: string; name: string; count: number };
export type ReadingEntry = {
  key: string; title: string; author: string | null; cover_url: string | null; url: string | null;
  cfi: string; percent: number; updated_at: string;
};
```

In `web/src/api/client.ts` add to the `api` object (the `qs` and `enc` helpers exist):

```typescript
  books: (params: { q?: string; author?: string; shelf?: string; sort?: 'popular' | 'title'; limit?: number; offset?: number } = {}) =>
    request<BooksResponse>('GET', `/books${qs(params)}`),
  bookShelves: () => request<BookShelf[]>('GET', '/books/shelves'),
  book: (id: string | number) => request<BookDetail>('GET', `/books/gutenberg/${enc(String(id))}`),
  reading: () => request<ReadingEntry[]>('GET', '/reading'),
  getReading: async (key: string): Promise<ReadingEntry | null> => {
    try {
      return await request<ReadingEntry>('GET', `/reading/${enc(key)}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },
  putReading: (key: string, body: { title: string; author: string | null; cover_url: string | null; cfi: string; percent: number }) =>
    request<{ ok: true }>('PUT', `/reading/${enc(key)}`, body),
  deleteReading: (key: string) => request<{ ok: true }>('DELETE', `/reading/${enc(key)}`),
```

Import the new types from `./types`.

- [ ] **Step 2: `readingPercent`, test first**

Create `web/tests/reader/position.test.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { readingPercent } from '../../src/reader/position';

const loc = (index: number, page: number, total: number, atEnd = false) =>
  ({ start: { index, cfi: 'x', href: '', location: 0, percentage: 0, displayed: { page, total } }, end: { index, cfi: 'x', href: '', location: 0, percentage: 0, displayed: { page, total } }, atStart: false, atEnd });

describe('readingPercent', () => {
  it('walks the spine and the pages inside the current section', () => {
    expect(readingPercent(loc(0, 1, 10), 4)).toBe(0);
    expect(readingPercent(loc(1, 1, 10), 4)).toBe(25);
    expect(readingPercent(loc(1, 6, 10), 4)).toBe(37.5);
  });
  it('is the page share alone when the whole book is one section', () => {
    expect(readingPercent(loc(0, 51, 100), 1)).toBe(50);
  });
  it('is 100 at the end and never above it or below 0', () => {
    expect(readingPercent(loc(3, 10, 10, true), 4)).toBe(100);
    expect(readingPercent(loc(9, 1, 1), 4)).toBe(100);
  });
  it('copes with a spine length epub.js has not filled in yet', () => {
    expect(readingPercent(loc(0, 3, 4), undefined)).toBe(50);
  });
});
```

Create `web/src/reader/position.ts`:

```typescript
import type { Location } from 'epubjs/types/rendition';

/** How often the reader tells the box where you are: one write per two seconds of page turning. */
export const SAVE_DELAY_MS = 2000;

/** What the reader remembers a book by. `startCfi` is where it opens; the rest is what the shelf shows. */
export type EpubMemory = { key: string; title: string; author: string | null; coverUrl: string | null; startCfi: string | null };

/** A whole-book percentage without epub.js's `locations` pass (which reads the entire book to count
 * characters and takes seconds on a phone): the section's share of the spine plus the page's share of
 * the section. Coarse between chapters, exact enough for "42% read" on a shelf. */
export function readingPercent(loc: Location, spineLength: number | undefined): number {
  if (loc.atEnd) return 100;
  const sections = spineLength && spineLength > 0 ? spineLength : 1;
  const page = Math.max(1, loc.start.displayed?.page ?? 1);
  const total = Math.max(1, loc.start.displayed?.total ?? 1);
  const within = (page - 1) / total;
  const value = ((loc.start.index ?? 0) + within) / sections * 100;
  return Math.max(0, Math.min(100, Math.round(value * 10) / 10));
}
```

Run: `pnpm --dir web vitest run tests/reader`
Expected: PASS (write the test, see it fail on the missing module, then the implementation).

- [ ] **Step 3: The `EpubReader` `memory` prop, test first**

In `web/tests/screens/doc.test.tsx`, the hoisted mock's `rendition` gains `on`/`off` that record the relocated handler, and every test that renders `epubItem` gets `vi.spyOn(api, 'getReading').mockResolvedValue(null)` (there are nine `epubItem` mentions; add the spy next to each `libraryItem` mock that returns `epubItem`, or once in a `beforeEach`). Update the mock:

```typescript
const mocks = vi.hoisted(() => {
  const handlers: Record<string, (loc: unknown) => void> = {};
  const rendition = {
    display: vi.fn(async () => undefined), next: vi.fn(), prev: vi.fn(),
    on: vi.fn((event: string, cb: (loc: unknown) => void) => { handlers[event] = cb; }),
    off: vi.fn((event: string) => { delete handlers[event]; }),
    themes: { register: vi.fn(), select: vi.fn(), fontSize: vi.fn() },
  };
  const book = { renderTo: vi.fn(() => rendition), destroy: vi.fn(), spine: { length: 4 } };
  return { rendition, book, handlers, ePub: vi.fn(() => book) };
});
```

Add two tests:

```typescript
  it('opens a Library EPUB where it was left and saves the position once per pause', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    vi.spyOn(api, 'getReading').mockResolvedValue({
      key: 'doc:where-there-is-no-doctor', title: epubItem.title, author: null, cover_url: null, url: '/doc/where-there-is-no-doctor',
      cfi: 'epubcfi(/6/8!/4/2)', percent: 30, updated_at: '2026-09-17T10:00:00Z',
    });
    const put = vi.spyOn(api, 'putReading').mockResolvedValue({ ok: true });
    renderRoute('/doc/where-there-is-no-doctor');
    await screen.findByRole('button', { name: 'Next' });
    expect(mocks.rendition.display).toHaveBeenCalledWith('epubcfi(/6/8!/4/2)');
    const loc = (index: number, page: number) => ({ start: { index, cfi: `epubcfi(/6/${index})`, displayed: { page, total: 10 } }, end: {}, atStart: false, atEnd: false });
    mocks.handlers.relocated(loc(1, 1));
    mocks.handlers.relocated(loc(1, 6));
    expect(put).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(2000);
    expect(put).toHaveBeenCalledTimes(1);
    expect(put).toHaveBeenCalledWith('doc:where-there-is-no-doctor', { title: epubItem.title, author: null, cover_url: null, cfi: 'epubcfi(/6/1)', percent: 37.5 });
    vi.useRealTimers();
  });

  it('starts at the beginning when the saved place no longer resolves', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    vi.spyOn(api, 'getReading').mockResolvedValue({
      key: 'doc:where-there-is-no-doctor', title: epubItem.title, author: null, cover_url: null, url: null,
      cfi: 'epubcfi(/6/999)', percent: 30, updated_at: '2026-09-17T10:00:00Z',
    });
    mocks.rendition.display.mockRejectedValueOnce(new Error('No Section Found'));
    renderRoute('/doc/where-there-is-no-doctor');
    await screen.findByRole('button', { name: 'Next' });
    await waitFor(() => expect(mocks.rendition.display).toHaveBeenCalledTimes(2));
    expect(mocks.rendition.display).toHaveBeenLastCalledWith(undefined);
    expect(screen.queryByText(/Could not open/)).not.toBeInTheDocument();
  });
```

(`waitFor` from `@testing-library/react`; check the file's existing imports.)

- [ ] **Step 4: Implement in `Doc.tsx`**

Imports: add `import { readingPercent, SAVE_DELAY_MS, type EpubMemory } from '../reader/position';` and `import type { Location } from 'epubjs/types/rendition';`.

`EpubReader` becomes `export function EpubReader({ url, theme, leading, memory }: { url: string; theme: Theme; leading?: ReactNode; memory?: EpubMemory })`, with a `memoryRef` mirroring `memory` the way `themeRef` mirrors `theme`, and the first effect replaced by:

```typescript
  const memoryRef = useRef(memory);
  memoryRef.current = memory;

  useEffect(() => {
    if (!hostRef.current) return;
    const book = ePub(url);
    const rendition = book.renderTo(hostRef.current, { width: '100%', height: '100%', flow: 'paginated' });
    renditionRef.current = rendition;
    const start = memoryRef.current?.startCfi || undefined;
    // A remembered place that no longer resolves (the file was rebuilt) is not an error: open at the start.
    const opening = start ? rendition.display(start).catch(() => rendition.display()) : rendition.display();
    opening.catch((e: unknown) => setError(errorMessage(e)));
    let timer: ReturnType<typeof setTimeout> | undefined;
    const onRelocated = (loc: Location) => {
      const m = memoryRef.current;
      if (!m) return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        void api.putReading(m.key, {
          title: m.title, author: m.author, cover_url: m.coverUrl,
          cfi: loc.start.cfi, percent: readingPercent(loc, book.spine.length),
        }).catch(() => undefined); // the page turned either way; a missed save costs nothing but the bookmark
      }, SAVE_DELAY_MS);
    };
    rendition.on('relocated', onRelocated);
    return () => {
      clearTimeout(timer);
      rendition.off('relocated', onRelocated);
      book.destroy();
      renditionRef.current = null;
    };
  }, [url]);
```

`book.spine.length` is typed in epubjs; if `tsc` objects, use `(book.spine as { length?: number }).length`.

In `Doc()`, fetch the saved place before drawing the reader:

```typescript
  const memoryQ = useQuery<ReadingEntry | null>(
    () => (item && item.kind === 'epub' ? api.getReading(`doc:${item.id}`) : Promise.resolve(null)),
    [item?.id, item?.kind],
  );
  const memory: EpubMemory | undefined = item && item.kind === 'epub'
    ? { key: `doc:${item.id}`, title: item.title, author: null, coverUrl: null, startCfi: memoryQ.data?.cfi ?? null }
    : undefined;
```

and the EPUB line becomes `{item && !gone && file && item.kind === 'epub' && !showOriginal && !memoryQ.loading && <EpubReader url={file} theme={theme} leading={originalToggle} memory={memory} />}`. (`ReadingEntry` joins the type import.) A failed lookup (`memoryQ.error`) still draws the reader from the start.

- [ ] **Step 5: Run**

Run: `pnpm --dir web vitest run tests/screens/doc.test.tsx tests/reader && pnpm --dir web exec tsc --noEmit`
Expected: PASS, including every pre-existing Doc test.

- [ ] **Step 6: Commit**

```bash
git add web/src/reader/position.ts web/tests/reader/position.test.ts web/src/api/types.ts web/src/api/client.ts web/src/screens/Doc.tsx web/tests/screens/doc.test.tsx
git commit -m "feat(reader): the EPUB reader remembers where you were, on the box"
```

---

### Task 7: The Book screen

**Files:**
- Create: `web/src/screens/Book.tsx`, `web/tests/screens/book.test.tsx`
- Modify: `web/src/router.tsx`

**Interfaces:**
- Consumes: `api.book(id)`, `EpubReader` with `memory`.
- Produces: route `/book/gutenberg/:id`.

- [ ] **Step 1: Write the failing test**

```typescript
import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { BookDetail } from '../../src/api/types';

const mocks = vi.hoisted(() => {
  const rendition = { display: vi.fn(async () => undefined), next: vi.fn(), prev: vi.fn(), on: vi.fn(), off: vi.fn(), themes: { register: vi.fn(), select: vi.fn(), fontSize: vi.fn() } };
  const book = { renderTo: vi.fn(() => rendition), destroy: vi.fn(), spine: { length: 3 } };
  return { rendition, book, ePub: vi.fn(() => book) };
});
vi.mock('epubjs', () => ({ default: mocks.ePub }));

const pride: BookDetail = {
  id: 1342, title: 'Pride and Prejudice', author: 'Jane Austen', shelf: 'PR', shelf_name: 'English literature', popularity: 100,
  cover_url: '/kiwix/content/gutenberg_en_all/covers/1342_cover_image.jpg',
  epub_url: '/kiwix/content/gutenberg_en_all/Pride%20and%20Prejudice.1342.epub',
  html_url: '/read/gutenberg_en_all/Pride%20and%20Prejudice.1342.html',
  available: true, position: { cfi: 'epubcfi(/6/4!/4/2/2)', percent: 12.5 },
};

describe('Book', () => {
  it('opens the EPUB from the ZIM at the remembered place, with the author beside the controls', async () => {
    vi.spyOn(api, 'book').mockResolvedValue(pride);
    renderRoute('/book/gutenberg/1342');
    await screen.findByRole('button', { name: 'Next' });
    expect(mocks.ePub).toHaveBeenCalledWith(pride.epub_url);
    expect(mocks.rendition.display).toHaveBeenCalledWith('epubcfi(/6/4!/4/2/2)');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Pride and Prejudice');
    expect(screen.getByText('Jane Austen')).toBeInTheDocument();
  });

  it('sends a book with no EPUB to the Kiwix reader page', async () => {
    vi.spyOn(api, 'book').mockResolvedValue({ ...pride, id: 11339, epub_url: null, html_url: '/read/gutenberg_en_all/Aesop.11339.html', position: null });
    const { router } = renderRoute('/book/gutenberg/11339');
    await waitFor(() => expect(router.state.location.pathname).toBe('/read/gutenberg_en_all/Aesop.11339.html'));
  });

  it('says so when the collection is not on the box', async () => {
    vi.spyOn(api, 'book').mockResolvedValue({ ...pride, available: false });
    renderRoute('/book/gutenberg/1342');
    await screen.findByText(/Project Gutenberg is not on this box/);
    expect(mocks.ePub).not.toHaveBeenCalled();
  });

  it('reports a book that is not in the catalogue', async () => {
    vi.spyOn(api, 'book').mockRejectedValue(new Error('Book not found'));
    renderRoute('/book/gutenberg/999');
    await screen.findByText(/Could not open this book: Book not found/);
  });
});
```

Add `import { ApiError } ...` only if used. Check how other tests reset `vi.spyOn` between cases (`web/tests/setup.ts` restores mocks, or use `vi.restoreAllMocks()` in `afterEach`); `mocks.ePub` needs `mockClear()` in a `beforeEach` because the third test asserts it was not called.

- [ ] **Step 2: Run to verify failure**

Run: `pnpm --dir web vitest run tests/screens/book.test.tsx`
Expected: FAIL (the route renders "Not found").

- [ ] **Step 3: `Book.tsx` and the route**

```typescript
import { Navigate, useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { useTheme } from '../theme/ThemeProvider';
import { EpubReader } from './Doc';

/** One Gutenberg book, read in the app's own EPUB reader straight out of the ZIM. A book the scraper
 * shipped without an EPUB (a few hundred, mostly scans and music) goes to the Kiwix page instead. */
export function Book() {
  const { id = '' } = useParams();
  const { theme } = useTheme();
  const { data, error, loading } = useQuery(() => api.book(id), [id]);
  if (loading) return <Screen title="Book" search={false} backTo="/books"><Body><p className="muted">Opening…</p></Body></Screen>;
  if (error || !data) {
    return <Screen title="Book" search={false} backTo="/books"><Body><p className="warning">Could not open this book: {error ?? 'not found'}</p></Body></Screen>;
  }
  if (!data.available) {
    return <Screen title={data.title} search={false} backTo="/books"><Body><p className="warning">Project Gutenberg is not on this box yet.</p></Body></Screen>;
  }
  if (!data.epub_url) return <Navigate to={data.html_url ?? '/books'} replace />;
  return (
    <Screen title={data.title} search={false} fill backTo="/books">
      <EpubReader
        url={data.epub_url}
        theme={theme}
        leading={data.author ? <span className="muted">{data.author}</span> : undefined}
        memory={{ key: `gutenberg:${data.id}`, title: data.title, author: data.author, coverUrl: data.cover_url, startCfi: data.position?.cfi ?? null }}
      />
    </Screen>
  );
}
```

In `web/src/router.tsx`: `const Book = lazy(() => import('./screens/Book').then((m) => ({ default: m.Book })));` beside the other lazy screens, and `{ path: 'book/gutenberg/:id', element: <Later title="Book"><Book /></Later> },` after the `doc/:id` route.

- [ ] **Step 4: Run**

Run: `pnpm --dir web vitest run tests/screens/book.test.tsx && pnpm --dir web exec tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/screens/Book.tsx web/tests/screens/book.test.tsx web/src/router.tsx
git commit -m "feat(books): the Gutenberg book screen"
```

---

### Task 8: The Books browsing screen

**Files:**
- Create: `web/src/screens/Books.tsx`, `web/tests/screens/books.test.tsx`
- Modify: `web/src/router.tsx`

**Interfaces:**
- Consumes: `api.books(params)`, `api.bookShelves()`.
- Produces: `/books`: a search box (debounced 300 ms), shelf chips, the popular list, "Show more" paging by 40, "not on this box yet" when unavailable. The Library's Gutenberg card already opens `/books` (Task 4).

- [ ] **Step 1: Write the failing test**

```typescript
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { BookSummary } from '../../src/api/types';

const book = (id: number, title: string, author: string, shelf: string | null = 'PR'): BookSummary =>
  ({ id, title, author, shelf, shelf_name: shelf ? 'English literature' : null, popularity: 1, cover_url: null, epub_url: '/e', html_url: '/h' });

describe('Books', () => {
  it('lists the popular books, then searches as you type, then filters by shelf', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([{ code: 'PR', name: 'English literature', count: 2 }, { code: 'Q', name: 'Science', count: 1 }]);
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen'), book(2701, 'Moby-Dick', 'Herman Melville')], total: 2, available: true })
      .mockResolvedValueOnce({ items: [book(1232, 'The Prince', 'Niccolo Machiavelli', 'J')], total: 1, available: true })
      .mockResolvedValueOnce({ items: [book(1342, 'Pride and Prejudice', 'Jane Austen')], total: 1, available: true });
    const user = userEvent.setup();
    renderRoute('/books');
    await screen.findByText('Pride and Prejudice');
    expect(screen.getByRole('link', { name: /Pride and Prejudice/ })).toHaveAttribute('href', '/book/gutenberg/1342');
    expect(books).toHaveBeenCalledTimes(1);
    await user.type(screen.getByRole('searchbox', { name: 'Search the books' }), 'prince');
    await screen.findByText('The Prince');
    expect(books).toHaveBeenCalledTimes(2);   // one call for the whole word, not one per letter
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'prince', offset: 0 }));
    await user.clear(screen.getByRole('searchbox', { name: 'Search the books' }));
    await user.click(within(screen.getByRole('group', { name: 'Shelves' })).getByRole('button', { name: /English literature/ }));
    await waitFor(() => expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ shelf: 'PR' })));
  });

  it('pages with Show more', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    const first = Array.from({ length: 40 }, (_, i) => book(i + 1, `Book ${i + 1}`, 'A'));
    const books = vi.spyOn(api, 'books')
      .mockResolvedValueOnce({ items: first, total: 41, available: true })
      .mockResolvedValueOnce({ items: [book(41, 'Book 41', 'A')], total: 41, available: true });
    const user = userEvent.setup();
    renderRoute('/books');
    await screen.findByText('Book 40');
    expect(screen.getByText('41 books')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show more' }));
    await screen.findByText('Book 41');
    expect(books).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 40 }));
    expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument();
  });

  it('says the collection is not on the box yet', async () => {
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    renderRoute('/books');
    await screen.findByText(/Project Gutenberg is not on this box yet/);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `pnpm --dir web vitest run tests/screens/books.test.tsx`
Expected: FAIL.

- [ ] **Step 3: `Books.tsx` and the route**

```typescript
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import type { BookSummary } from '../api/types';
import { Screen, Body } from '../shell/Screen';

const PAGE = 40;

function useDebounced<T>(value: T, ms: number): T {
  const [slow, setSlow] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setSlow(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return slow;
}

/** The Gutenberg catalogue: the most-read books first, a search over titles and authors, and the
 * Library of Congress shelves as chips. Every card opens the book in the app's reader. */
export function Books() {
  const [typed, setTyped] = useState('');
  const q = useDebounced(typed.trim(), 300);
  const [shelf, setShelf] = useState<string | null>(null);
  const [more, setMore] = useState<BookSummary[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const shelves = useQuery(() => api.bookShelves(), []);
  const { data, error, loading } = useQuery(
    () => api.books({ q: q || undefined, shelf: shelf ?? undefined, limit: PAGE, offset: 0 }),
    [q, shelf],
  );
  useEffect(() => { setMore([]); }, [q, shelf]);

  const items = [...(data?.items ?? []), ...more];
  const total = data?.total ?? 0;
  const showMore = async () => {
    setLoadingMore(true);
    try {
      const page = await api.books({ q: q || undefined, shelf: shelf ?? undefined, limit: PAGE, offset: items.length });
      setMore((m) => [...m, ...page.items]);
    } finally {
      setLoadingMore(false);
    }
  };

  if (data && !data.available) {
    return (
      <Screen title="Books">
        <Body><p className="warning">Project Gutenberg is not on this box yet. It arrives with the core content; until then the Library lists what is here.</p></Body>
      </Screen>
    );
  }
  return (
    <Screen title="Books">
      <Body>
        <input type="search" className="input" aria-label="Search the books" placeholder="Title or author" value={typed} onChange={(e) => setTyped(e.target.value)} />
        {shelves.data && shelves.data.length > 0 && (
          <div className="chips" role="group" aria-label="Shelves">
            {shelves.data.map((s) => (
              <button key={s.code} type="button" className={shelf === s.code ? 'chip active' : 'chip'} aria-pressed={shelf === s.code}
                      onClick={() => setShelf(shelf === s.code ? null : s.code)}>
                {s.name} ({s.count})
              </button>
            ))}
          </div>
        )}
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Could not load the books: {error}</p>}
        {data && <p className="muted">{total === 1 ? '1 book' : `${total.toLocaleString('en-GB')} books`}{q ? ` for “${q}”` : ''}</p>}
        <ul className="list items" aria-label="Books">
          {items.map((b) => (
            <li key={b.id} className="item-card">
              <Link to={`/book/gutenberg/${b.id}`} className="row">
                {b.cover_url && <img src={b.cover_url} alt="" width={40} height={60} loading="lazy" />}
                <span>
                  <strong>{b.title}</strong>
                  {b.author && <span className="muted"> — {b.author}</span>}
                  {b.shelf_name && <span className="muted"> · {b.shelf_name}</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {items.length < total && (
          <button type="button" className="btn" onClick={() => void showMore()} disabled={loadingMore}>Show more</button>
        )}
      </Body>
    </Screen>
  );
}
```

Check the class name the app uses for text inputs (`grep -rn 'type="search"' web/src` and `className="input"` usage) and match it. Route: `const Books = lazy(() => import('./screens/Books').then((m) => ({ default: m.Books })));` and `{ path: 'books', element: <Later title="Books"><Books /></Later> },` before `book/gutenberg/:id`.

- [ ] **Step 4: Run**

Run: `pnpm --dir web vitest run tests/screens/books.test.tsx && pnpm --dir web exec tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/screens/Books.tsx web/tests/screens/books.test.tsx web/src/router.tsx
git commit -m "feat(books): the /books catalogue screen"
```

---

### Task 9: The "My books" shelf

**Files:**
- Modify: `web/src/screens/Library.tsx`, `web/tests/screens/library.test.tsx`

**Interfaces:**
- Consumes: `api.reading()`, `api.deleteReading(key)`.
- Produces: a "My books" section at the top of the Library when there is at least one reading entry.

- [ ] **Step 1: Write the failing test**

In `web/tests/screens/library.test.tsx`, the existing tests must mock `api.reading` too (add `vi.spyOn(api, 'reading').mockResolvedValue([])` beside each `api.library` mock, or in a `beforeEach`), then add:

```typescript
  it('shows My books first, newest first, and forgets a book on request', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const reading = vi.spyOn(api, 'reading')
      .mockResolvedValueOnce([
        { key: 'gutenberg:2701', title: 'Moby-Dick', author: 'Herman Melville', cover_url: null, url: '/book/gutenberg/2701', cfi: 'x', percent: 40.4, updated_at: '2026-09-17T10:00:00Z' },
        { key: 'doc:where-there-is-no-doctor', title: 'Where There Is No Doctor', author: null, cover_url: null, url: '/doc/where-there-is-no-doctor', cfi: 'y', percent: 10, updated_at: '2026-09-17T09:00:00Z' },
      ])
      .mockResolvedValueOnce([]);
    const del = vi.spyOn(api, 'deleteReading').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/library');
    const shelf = await screen.findByRole('region', { name: 'My books' });
    const items = within(shelf).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Moby-Dick');
    expect(items[0]).toHaveTextContent('40% read');
    expect(within(items[0]).getByRole('link', { name: /Moby-Dick/ })).toHaveAttribute('href', '/book/gutenberg/2701');
    expect(within(items[1]).getByRole('link', { name: /Where There Is No Doctor/ })).toHaveAttribute('href', '/doc/where-there-is-no-doctor');
    await user.click(within(items[0]).getByRole('button', { name: 'Forget Moby-Dick' }));
    expect(del).toHaveBeenCalledWith('gutenberg:2701');
    await waitFor(() => expect(screen.queryByRole('region', { name: 'My books' })).not.toBeInTheDocument());
    expect(reading).toHaveBeenCalledTimes(2);
  });
```

- [ ] **Step 2: Run to verify failure**

Run: `pnpm --dir web vitest run tests/screens/library.test.tsx`
Expected: the new test FAILS.

- [ ] **Step 3: Implement**

In `Library.tsx`: import `Link` from `react-router` and `Icon` from `../icons`; add `const shelf = useQuery(() => api.reading(), []);` and, inside the `{data && (<> ... </>)}` block before the categories `chips` div:

```typescript
            {shelf.data && shelf.data.length > 0 && (
              <section aria-label="My books">
                <h2>My books</h2>
                <ul className="list items" aria-label="My books">
                  {shelf.data.map((r) => (
                    <li key={r.key} className="item-card">
                      <div className="row">
                        {r.cover_url && <img src={r.cover_url} alt="" width={40} height={60} loading="lazy" />}
                        {r.url ? <Link to={r.url}><strong>{r.title}</strong></Link> : <strong>{r.title}</strong>}
                        {r.author && <span className="muted">{r.author}</span>}
                        <span className="muted">{Math.round(r.percent)}% read</span>
                        <button type="button" className="btn btn-small" aria-label={`Forget ${r.title}`}
                                onClick={() => void api.deleteReading(r.key).then(() => shelf.refetch())}>
                          <Icon name="close" size={16} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}
```

- [ ] **Step 4: Run the whole web suite**

Run: `pnpm --dir web vitest run && pnpm --dir web exec tsc --noEmit && pnpm --dir web run lint` (if a lint script exists; check `web/package.json`).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/screens/Library.tsx web/tests/screens/library.test.tsx
git commit -m "feat(library): a My books shelf that opens each book where it was left"
```

---

### Task 10: Spec amendments, records, and the real-ZIM run

**Files:**
- Modify: `docs/superpowers/specs/2026-09-14-gutenberg-library-design.md`, `docs/app-completion.md`, `docs/hardware-checklist.md`
- Test: the real file, once its checksum matches

- [ ] **Step 1: Amend the spec**

Insert after the spec's status line a section `## Amendments (2026-09-17)` recording, in prose: the real layout (as in this plan's "What the real ZIM contains"); that the importer reads the file with libzim rather than through kiwix-serve, and why (`install.sh` runs `sos index` before kiwix-serve is enabled; `index()` is synchronous); that the memory constraint is met by the catalogue being a 4 MB JavaScript array rather than by streaming; no subjects (LCC shelves instead), no author years; popularity is the catalogue position; EPUB and cover presence checked per book; the percentage read is the spine-and-page approximation, not epub.js `locations`; the Books group sits below guidance because of the frontend's group order, while the flat score is what the AI answerer sees; the PC now holds the ZIM (section 1's "cannot hold it" is superseded); the "scanned" badge for Survivor Library is not built (its description already says scans); `/api/books/subjects` became `/api/books/shelves`.

- [ ] **Step 2: Record in `docs/app-completion.md`**

Append a dated section `## 2026-09-17: the Gutenberg collection reads like books` in the file's existing style: the 1 TB standard and the two items moved to core, what was built (tasks 2 to 9 in one paragraph each), the verification line (API and web suite counts, `tsc`, ruff, validator), and "Phase 2 (semantic search, spec section 8) is deliberately unbuilt."

- [ ] **Step 3: Hardware checklist rows**

Append two rows after row 26: `| 27 | Open a Gutenberg book on the touchscreen, page forward, reopen it from a phone and land on the same page | | | |` and `| 28 | Search "Robinson Crusoe": the Books group appears below the guides and opens in the reader | | | |`.

- [ ] **Step 4: The real ZIM, when it has finished downloading**

```bash
ls -la /home/dan/sos-content/zim/gutenberg_en_all.zim*        # no .aria2 file, and no aria2c process
sha256sum /home/dan/sos-content/zim/gutenberg_en_all.zim       # must equal 01677c8d...faf28 (about 15 minutes)
zimdump list /home/dan/sos-content/zim/gutenberg_en_all.zim | grep -v '\.html$\|\.epub$\|\.pdf$\|^covers/' | head -40
zimdump show --url full_by_popularity.js /home/dan/sos-content/zim/gutenberg_en_all.zim | head -c 600
```

Expected: `full_by_popularity.js` present with the five-field rows. If the file shows a different layout, edit the constants at the top of `api/sos/books.py` (and `parse_catalogue` if the row shape differs) and re-run Task 3's tests with a fixture updated to match; record what was found in `docs/app-completion.md` either way.

Then index for real against a throwaway state dir (the dev stack's `.dev/full-manifest` includes the repo manifest; Task 1 made the item core):

```bash
mkdir -p /tmp/claude-1000/-home-dan/ccd63c4f-1f30-41f8-a37d-1e0c40e71bc4/scratchpad/state
SOS_CORE=/home/dan/sos-content SOS_STATE=/tmp/claude-1000/-home-dan/ccd63c4f-1f30-41f8-a37d-1e0c40e71bc4/scratchpad/state \
  SOS_MANIFEST_DIR=manifest SOS_PLAYBOOKS_DIR=playbooks SOS_DEV=1 api/.venv/bin/sos index
```

Expected: the `index:` line ends `..., <N> books` with N in the tens of thousands. Then, with `SOS_STATE` pointing at that dir, start `sos-api` alone (`SOS_DEV=1 ... api/.venv/bin/uvicorn sos.main:app --port 8000`) and check:

```bash
curl -s "http://127.0.0.1:8000/api/books?q=robinson+crusoe" | python3 -m json.tool | head -40
curl -s "http://127.0.0.1:8000/api/search?q=robinson+crusoe" | python3 -c "import json,sys; d=json.load(sys.stdin); print([(r['source'], r['title']) for r in d['results'] if r['source']=='books'][:3])"
```

Record N, the top "Robinson Crusoe" hit, and the count of flagged-but-missing EPUBs from the log line in `docs/app-completion.md`.

- [ ] **Step 5: Final full check and commit**

Run: `cd api && .venv/bin/python -m pytest -q && .venv/bin/ruff check . && cd .. && pnpm --dir web vitest run && pnpm --dir web exec tsc --noEmit && SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios`

```bash
git add docs/superpowers/specs/2026-09-14-gutenberg-library-design.md docs/app-completion.md docs/hardware-checklist.md docs/superpowers/plans/2026-09-17-gutenberg-books.md
git commit -m "docs: the Gutenberg collection amendments, record and hardware checks"
```

---

## Self-review

**Spec coverage:** Section 1 (1 TB, manifest) → Task 1. Section 2 (layout) → the facts block above and Task 10's amendment; the constants table at the top of `books.py`. Section 3 (reader, position memory, HTML-only redirect to the Kiwix reader) → Tasks 6 and 7. Section 4 (catalogue, API) → Tasks 2 to 4, with shelves replacing subjects. Section 5 (search, no fan-out, suggest) → Task 5. Section 6 (browsing, Library card) → Task 8 and Task 4's `reader_url`. Section 7 (shelf) → Task 9. Section 8 → out of scope, recorded in Task 10. Section 9 (errors: ZIM absent, bad catalogue, EPUB fetch failure, stale CFI) → Tasks 3, 4, 6, 7. Section 11 (tests) → every task.

**Placeholder scan:** none; the one dead end (a `test_sync.py` populated-index test) is explained and replaced inline.

**Type consistency:** `BookSummary`/`BookDetail`/`BooksResponse`/`BookShelf`/`ReadingEntry` (Task 6 types) match the router's dicts (Task 4) and are what `Book.tsx`, `Books.tsx` and the shelf consume. `EpubMemory` (Task 6) is what `Book.tsx` (Task 7) and `Doc.tsx` build. Keys are `gutenberg:<id>` and `doc:<id>` everywhere; `reading_url` (Task 4) is the only place that turns a key into a route.
