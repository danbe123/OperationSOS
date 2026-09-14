# Books Reflow (PDF-to-EPUB) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every library book a single, reflowable, Kindle-like reading experience by converting the library's PDF books to EPUB at content-build time, reusing the existing EPUB reader, with the original PDF one tap away as a fallback.

**Architecture:** A new manifest field (`pdf_dest`) marks a converted book and points at its kept-around original PDF. A new PC-only CLI tool (`sos build-books`) runs Calibre's `ebook-convert` to produce the EPUB. The backend exposes the fallback file's URL the same way it already exposes the primary file's URL. The frontend's existing `Doc.tsx` reader gets one small toggle between the existing `EpubReader` and the existing `PdfChrome` components — no new viewer code.

**Tech Stack:** Python (FastAPI backend, pydantic, jsonschema, sqlite3, httpx), Calibre's `ebook-convert`, TypeScript/React (Vite, vitest, epub.js, PDF.js).

**Spec:** [docs/superpowers/specs/2026-09-14-books-reflow-design.md](../specs/2026-09-14-books-reflow-design.md)

## Global Constraints

- Conversion happens once, at content-build time, on the PC. It never runs on the Pi and never runs at request time (spec section 2).
- A failed conversion is reported and skipped; the source item's manifest entry is left exactly as it was (`kind: "pdf"`, unchanged) rather than partially migrated (spec section 4).
- The fallback PDF link is shown only when the file is actually confirmed present on this box's drive — never a link to a file that might not be there (spec section 6, mirroring the existing `available` pattern in `api/sos/library.py`).
- A converted book is one manifest row, not two — the Library screen must never show the same book twice (spec section 3).
- Calibre installs user-local, no sudo: `wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin install_dir=$HOME/.local/opt/calibre isolated=y`, matching every other tool already in `~/.local/bin`.

---

### Task 1: Manifest schema and `Item` model gain `pdf_dest`

**Files:**
- Modify: `manifest/schema.json`
- Modify: `api/tests/fixtures/manifest/schema.json` (must stay byte-identical to the repo schema — `test_schema_and_fixture_schema_identical` enforces this)
- Modify: `api/sos/manifest.py`
- Test: `api/tests/test_manifest.py`

**Interfaces:**
- Produces: `Item.pdf_dest: str | None` (default `None`) — the dest-relative path (same pattern as `dest`) of a converted book's original PDF. `validate_manifests()` rejects a `pdf_dest` that collides with any other item's `dest` or `pdf_dest`, and rejects a `source.tool == "pdf2epub"` build item that has no `pdf_dest`. Later tasks read `item.pdf_dest` and `item.source.tool`.

- [ ] **Step 1: Write the failing schema/model tests**

Add to `api/tests/test_manifest.py`:

```python
def test_pdf_dest_collision_with_another_items_dest_is_reported(tmp_path):
    a = _zim("a", kind="epub", dest="docs/a.epub",
             source={"type": "build", "tool": "pdf2epub", "artifact": "docs/a.epub", "url": "https://example.invalid/a.pdf"},
             pdf_dest="docs/shared.pdf")
    b = _zim("b", kind="pdf", dest="docs/shared.pdf", source={"type": "url", "url": "https://example.invalid/b.pdf"})
    d = _tree(tmp_path, [a, b])
    errors = validate_manifests(d)
    assert any("duplicate dest 'docs/shared.pdf'" in e for e in errors)


def test_pdf2epub_tool_requires_pdf_dest(tmp_path):
    item = _zim("a", kind="epub", dest="docs/a.epub",
               source={"type": "build", "tool": "pdf2epub", "artifact": "docs/a.epub", "url": "https://example.invalid/a.pdf"})
    d = _tree(tmp_path, [item])
    errors = validate_manifests(d)
    assert any("pdf2epub build items need pdf_dest" in e for e in errors)


def test_converted_epub_item_is_valid_and_loads_pdf_dest_and_source_url(tmp_path):
    item = _zim("a", kind="epub", dest="docs/a.epub",
               source={"type": "build", "tool": "pdf2epub", "artifact": "docs/a.epub", "url": "https://example.invalid/a.pdf"},
               pdf_dest="docs/a.pdf")
    d = _tree(tmp_path, [item])
    assert validate_manifests(d) == []
    loaded = load_manifests(d)[0]
    assert loaded.pdf_dest == "docs/a.pdf"
    assert loaded.source.url == "https://example.invalid/a.pdf"


def test_pdf_dest_defaults_to_none():
    items = load_manifests(FIXTURES / "manifest")
    assert next(i for i in items if i.id == "sos-test-pdf").pdf_dest is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_manifest.py -q -k "pdf_dest or pdf2epub or converted_epub"`
Expected: FAIL — `pdf_dest` is not a recognized schema property / `Item` has no field `pdf_dest`.

- [ ] **Step 3: Add `pdf_dest` to the schema**

In `manifest/schema.json`, in `$defs/item/properties`, immediately after the `"dest"` property, add:

```json
        "pdf_dest": { "type": ["string", "null"], "pattern": "^[A-Za-z0-9._-]+(/[A-Za-z0-9._ -]+)*$" },
```

Copy `manifest/schema.json` over `api/tests/fixtures/manifest/schema.json` verbatim (`cp manifest/schema.json api/tests/fixtures/manifest/schema.json`) so the two stay identical.

- [ ] **Step 4: Add `pdf_dest` to the `Item` model**

In `api/sos/manifest.py`, in `class Item`, immediately after the `dest: str` line, add:

```python
    pdf_dest: str | None = None
```

- [ ] **Step 5: Extend `validate_manifests` with the two new checks**

In `api/sos/manifest.py`, inside `validate_manifests`'s per-item loop, replace:

```python
            if dest in seen_dests:
                errors.append(f"{path.name}: duplicate dest '{dest}' (also in {seen_dests[dest]})")
            else:
                seen_dests[dest] = path.name
            if raw.get("kind") == "zim" and dest != f"zim/{iid}.zim":
                errors.append(f"{path.name}: {iid}: zim dest must be 'zim/{iid}.zim', got '{dest}'")
            if source.get("type") == "build" and not source.get("artifact"):
                errors.append(f"{path.name}: {iid}: build items need source.artifact")
```

with:

```python
            if dest in seen_dests:
                errors.append(f"{path.name}: duplicate dest '{dest}' (also in {seen_dests[dest]})")
            else:
                seen_dests[dest] = path.name
            pdf_dest = raw.get("pdf_dest")
            if pdf_dest:
                if pdf_dest in seen_dests:
                    errors.append(f"{path.name}: duplicate dest '{pdf_dest}' (also in {seen_dests[pdf_dest]})")
                else:
                    seen_dests[pdf_dest] = path.name
            if raw.get("kind") == "zim" and dest != f"zim/{iid}.zim":
                errors.append(f"{path.name}: {iid}: zim dest must be 'zim/{iid}.zim', got '{dest}'")
            if source.get("type") == "build" and not source.get("artifact"):
                errors.append(f"{path.name}: {iid}: build items need source.artifact")
            if source.get("tool") == "pdf2epub" and not pdf_dest:
                errors.append(f"{path.name}: {iid}: pdf2epub build items need pdf_dest")
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd api && .venv/bin/pytest tests/test_manifest.py -q`
Expected: PASS, all tests including the four new ones.

- [ ] **Step 7: Commit**

```bash
git add manifest/schema.json api/tests/fixtures/manifest/schema.json api/sos/manifest.py api/tests/test_manifest.py
git commit -m "$(cat <<'EOF'
manifest: add pdf_dest for a book converted from PDF to EPUB

A converted book keeps its original PDF as a fallback file, named by
this new field. validate_manifests rejects a pdf_dest that collides
with another item's dest, and a pdf2epub build item with none.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend serves the fallback PDF's URL

**Files:**
- Modify: `api/sos/db.py`
- Modify: `api/sos/library.py`
- Modify: `api/tests/fixtures/manifest/core.json`
- Modify: `api/tests/test_library.py`
- Modify: `api/tests/test_api.py`

**Interfaces:**
- Consumes: `Item.pdf_dest` (Task 1).
- Produces: `library.pdf_fallback_url(row: sqlite3.Row) -> str | None`, and `item_dict()` output gains the key `"pdf_fallback_url"`. Task 3's `sos build-books` and Task 4's frontend both key off this — Task 4 reads `pdf_fallback_url` from `/api/library/<id>` exactly as it already reads `file_url`.
- Adds a fixture manifest item `sos-test-epub` (kind `epub`, `pdf_dest: "docs/sos-test-original.pdf"`) that Task 3's tests also use.

- [ ] **Step 1: Add the fixture item**

In `api/tests/fixtures/manifest/core.json`, add a fifth items array entry (after `nrr-2025`, before `gemma-4-E2B-it-Q4_K_M`):

```json
    {
      "id": "sos-test-epub",
      "title": "SOS test converted book",
      "kind": "epub", "tier": "core", "category": "books", "scenarios": [],
      "source": { "type": "build", "tool": "pdf2epub", "artifact": "docs/sos-test-converted.epub",
                  "url": "https://example.invalid/sos-test-original.pdf" },
      "dest": "docs/sos-test-converted.epub",
      "pdf_dest": "docs/sos-test-original.pdf",
      "size_bytes": 900, "as_at": "2026-09", "licence": "CC0", "priority": 50,
      "description": "Two-page fixture book, converted from PDF.", "search_weight": 1.0
    },
```

- [ ] **Step 2: Write the failing tests**

In `api/tests/test_library.py`, change line 55's assertion from `assert total == 26 and available == 3` to `assert total == 27 and available == 3` (the new fixture item's files are not installed by this test, so `available` is unchanged).

Add a new test in `api/tests/test_library.py`:

```python
def test_pdf_fallback_url_only_appears_once_the_fallback_file_is_present(conn, env):
    total, available = library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-test-epub'").fetchone()
    assert library.pdf_fallback_url(row) is None  # neither file exists yet

    (env.core / "docs" / "sos-test-converted.epub").write_bytes(b"EPUB")
    library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-test-epub'").fetchone()
    assert library.file_url(row) == "/docs/core/sos-test-converted.epub"
    assert library.pdf_fallback_url(row) is None  # epub present, but not the fallback PDF yet

    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF-1.4\n")
    library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-test-epub'").fetchone()
    assert library.pdf_fallback_url(row) == "/docs/core/sos-test-original.pdf"


def test_pdf_fallback_url_is_none_for_a_book_that_was_never_a_pdf(conn, env):
    library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='wikipedia_en_100_mini_2026-01'").fetchone()
    assert row["pdf_dest"] is None
    assert library.pdf_fallback_url(row) is None
```

In `api/tests/test_library.py`, update `test_library_response_groups_by_category_in_order`'s key-set assertion (currently around line 96-97) from:

```python
                assert set(item) == {"id", "title", "kind", "tier", "category", "scenarios", "size_bytes", "as_at", "licence",
                                     "available", "url", "file_url", "description", "drive_label"}
```

to:

```python
                assert set(item) == {"id", "title", "kind", "tier", "category", "scenarios", "size_bytes", "as_at", "licence",
                                     "available", "url", "file_url", "pdf_fallback_url", "description", "drive_label"}
```

In `api/tests/test_api.py`, update line 52's assertion from `assert r.status_code == 200 and r.json() == {"items": 26, "available": 2}` to `assert r.status_code == 200 and r.json() == {"items": 27, "available": 2}`.

- [ ] **Step 3: Run the new/changed tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_library.py tests/test_api.py -q -k "pdf_fallback or groups_by_category or rescan"`
Expected: FAIL — `library.pdf_fallback_url` doesn't exist yet; counts and key sets don't match yet.

- [ ] **Step 4: Add the `pdf_dest`/`pdf_available` columns**

In `api/sos/db.py`, in the `library_items` `CREATE TABLE`, add `pdf_dest` and `pdf_available` after `dest`:

```python
CREATE TABLE IF NOT EXISTS library_items (
  id TEXT PRIMARY KEY, title, kind, tier, category, scenarios_json, dest, pdf_dest, size_bytes INTEGER, as_at, licence,
  priority INTEGER, reader_home, description, search_weight REAL NOT NULL DEFAULT 1.0, suggest INTEGER NOT NULL DEFAULT 0,
  overlay_json, available INTEGER NOT NULL DEFAULT 0, local_path, fts INTEGER NOT NULL DEFAULT 0,
  resolved_name, resolved_size INTEGER, resolved_as_at, pdf_available INTEGER NOT NULL DEFAULT 0);
```

In `init_schema`, next to the existing `_ensure_column(conn, "stock", "kit_item", "TEXT")` line, add the same upgrade path for a box built before this field existed:

```python
    _ensure_column(conn, "library_items", "pdf_dest", "TEXT")
    _ensure_column(conn, "library_items", "pdf_available", "INTEGER NOT NULL DEFAULT 0")
```

- [ ] **Step 5: Mirror `pdf_dest` into `upsert_items`**

In `api/sos/library.py`, `upsert_items`'s `INSERT` statement, add `pdf_dest` to the column list, the `?` placeholders, the `ON CONFLICT` update clause, and the values tuple:

```python
    for it in items:
        conn.execute(
            """INSERT INTO library_items(id, title, kind, tier, category, scenarios_json, dest, pdf_dest, size_bytes, as_at, licence,
                 priority, reader_home, description, search_weight, suggest, overlay_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title, kind=excluded.kind, tier=excluded.tier,
                 category=excluded.category, scenarios_json=excluded.scenarios_json, dest=excluded.dest, pdf_dest=excluded.pdf_dest,
                 size_bytes=excluded.size_bytes, as_at=excluded.as_at, licence=excluded.licence, priority=excluded.priority,
                 reader_home=excluded.reader_home, description=excluded.description, search_weight=excluded.search_weight,
                 suggest=excluded.suggest, overlay_json=excluded.overlay_json""",
            (it.id, it.title, it.kind, it.tier, it.category, json.dumps(it.scenarios), it.dest, it.pdf_dest, it.size_bytes, it.as_at,
             it.licence, it.priority, it.reader_home, it.description, it.search_weight, int(it.suggest),
             json.dumps(it.overlay.model_dump()) if it.overlay else None),
        )
```

- [ ] **Step 6: Track fallback-file availability in `refresh_items`**

In `api/sos/library.py`, replace `refresh_items`:

```python
def refresh_items(conn: sqlite3.Connection, settings: Settings) -> tuple[int, int]:
    ext_ok = ext_mounted(settings)
    total = available = 0
    for row in conn.execute("SELECT id, tier, dest, pdf_dest FROM library_items").fetchall():
        total += 1
        root = settings.tier_root(row["tier"])
        path = root / row["dest"]
        ok = path.exists() and (row["tier"] == "core" or ext_ok)
        if ok:
            available += 1
        pdf_ok = 0
        if row["pdf_dest"]:
            pdf_path = root / row["pdf_dest"]
            pdf_ok = int(pdf_path.exists() and (row["tier"] == "core" or ext_ok))
        conn.execute("UPDATE library_items SET available=?, local_path=?, pdf_available=? WHERE id=?",
                     (int(ok), str(path) if ok else None, pdf_ok, row["id"]))
    conn.commit()
    return total, available
```

- [ ] **Step 7: Add `pdf_fallback_url` and wire it into `item_dict`**

In `api/sos/library.py`, immediately after `file_url`, add:

```python
def pdf_fallback_url(row: sqlite3.Row) -> str | None:
    """Where a converted book's original PDF sits, for the reader's one-tap fallback (spec section 6).
    None for a book that was never a PDF, and None until the fallback file is confirmed on this box —
    never a link to a file that might not be there."""
    if row["kind"] != "epub" or not row["pdf_dest"] or not row["pdf_available"]:
        return None
    name = str(row["pdf_dest"]).rsplit("/", 1)[-1]
    return f"/docs/{'extended' if row['tier'] == 'extended' else 'core'}/{name}" if name else None
```

In `item_dict`, add `"pdf_fallback_url": pdf_fallback_url(row),` after the `"file_url": file_url(row),` line.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd api && .venv/bin/pytest tests/test_library.py tests/test_api.py -q`
Expected: PASS.

- [ ] **Step 9: Run the full backend test suite**

Run: `cd api && .venv/bin/pytest -q`
Expected: PASS (confirms nothing else assumed the old 26-item / old key-set shape).

- [ ] **Step 10: Commit**

```bash
git add api/sos/db.py api/sos/library.py api/tests/fixtures/manifest/core.json api/tests/test_library.py api/tests/test_api.py
git commit -m "$(cat <<'EOF'
library: serve a converted book's original PDF as a fallback URL

pdf_fallback_url mirrors file_url's shape but only resolves once the
fallback file itself is confirmed present, tracked the same way
available already is.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `sos build-books` converts a PDF item to EPUB with Calibre

**Files:**
- Create: `api/sos/buildbooks.py`
- Modify: `api/sos/cli.py`
- Test: `api/tests/test_buildbooks.py`

**Interfaces:**
- Consumes: `Item.pdf_dest`, `Item.source.tool` (Task 1); the `sos-test-epub` fixture item (Task 2); `sos.sync.download` and `sos.sync.SyncError` (existing).
- Produces: `buildbooks.convert_one(item: Item, settings: Settings, run: Callable = subprocess.run, client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which, use_aria2: bool | None = None) -> tuple[bool, str]` and `buildbooks.main(settings: Settings, only: list[str] | None = None, run=..., client=..., which=..., use_aria2=...) -> int`. `cli.py`'s `build-books` subcommand calls `buildbooks.main`.

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_buildbooks.py`:

```python
import subprocess
from pathlib import Path

import httpx

from sos import buildbooks
from sos.manifest import load_manifests


class FakeRun:
    """Records every command; simulates ebook-convert writing the EPUB, instead of running it."""

    def __init__(self, ok: bool = True):
        self.calls: list[list[str]] = []
        self.ok = ok

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        if cmd[0] == "ebook-convert" and self.ok:
            Path(cmd[2]).write_bytes(b"EPUB fake")
        return subprocess.CompletedProcess(cmd, 0 if self.ok else 1, stdout="",
                                           stderr="" if self.ok else "conversion failed")


def _which_installed(name: str) -> str | None:
    return f"/usr/bin/{name}" if name == "ebook-convert" else None


def _item(env):
    return next(i for i in load_manifests(env.manifests) if i.id == "sos-test-epub")


def test_convert_one_runs_ebook_convert_with_the_items_title_and_writes_the_epub(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert ok, message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert epub_path.read_bytes() == b"EPUB fake"
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    assert run.calls == [["ebook-convert", str(pdf_path), str(epub_path), "--title", item.title]]


def test_convert_one_reports_failure_and_leaves_no_partial_epub(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=False)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "ebook-convert failed" in message
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()


def test_convert_one_fails_without_calling_run_when_calibre_is_not_installed(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=lambda name: None)
    assert not ok and "Calibre" in message
    assert run.calls == []


def test_convert_one_requires_pdf_dest(env):
    item = _item(env).model_copy(update={"pdf_dest": None})
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "pdf_dest" in message
    assert run.calls == []


def test_convert_one_fetches_the_source_pdf_when_not_already_on_disk(env):
    item = _item(env)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == item.source.url
        return httpx.Response(200, content=b"%PDF fetched")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, client=client, which=_which_installed, use_aria2=False)
    assert ok, message
    assert (env.core / "docs" / "sos-test-original.pdf").read_bytes() == b"%PDF fetched"


def test_main_reports_ok_and_returns_zero(env):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    code = buildbooks.main(env, run=run, which=_which_installed)
    assert code == 0
    assert (env.core / "docs" / "sos-test-converted.epub").exists()


def test_main_returns_nonzero_when_a_conversion_fails(env):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=False)
    code = buildbooks.main(env, run=run, which=_which_installed)
    assert code == 1


def test_main_only_filters_to_the_named_ids(env):
    run = FakeRun(ok=True)
    code = buildbooks.main(env, only=["does-not-exist"], run=run, which=_which_installed)
    assert code == 0
    assert run.calls == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_buildbooks.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sos.buildbooks'`.

- [ ] **Step 3: Write `api/sos/buildbooks.py`**

```python
"""`sos build-books [--only ID...]`: convert every manifest item whose source.tool is "pdf2epub" from
its original PDF into a reflowable EPUB with Calibre's ebook-convert (spec
docs/superpowers/specs/2026-09-14-books-reflow-design.md section 4).

PC only: Calibre is not installed on the Pi, and conversion never happens at request time. A failed
conversion is reported and skipped — that item's manifest entry is simply left as `kind: "pdf"` until
it is fixed and retried; nothing elsewhere needs to know about a partially migrated library.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Callable

import httpx

from sos.config import Settings
from sos.manifest import Item, load_manifests
from sos.sync import SyncError, download


def convert_one(item: Item, settings: Settings, run: Callable = subprocess.run,
                client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which,
                use_aria2: bool | None = None) -> tuple[bool, str]:
    """Produce `item.dest` (the EPUB) under the item's tier root, fetching `item.pdf_dest` (the
    original) from `item.source.url` first if it is not already on disk. Returns (ok, message)."""
    if item.source.tool != "pdf2epub":
        return False, f"{item.id}: source.tool is {item.source.tool!r}, not pdf2epub"
    if not item.pdf_dest:
        return False, f"{item.id}: manifest entry has no pdf_dest"
    if not which("ebook-convert"):
        return False, f"{item.id}: ebook-convert is not on PATH (install Calibre)"
    root = settings.tier_root(item.tier)
    pdf_path = root / item.pdf_dest
    epub_path = root / item.dest
    if not pdf_path.exists():
        if not item.source.url:
            return False, f"{item.id}: no PDF at {pdf_path} and source has no url to fetch it from"
        try:
            download(item.source.url, pdf_path, item.source.sha256, item.source.mirrors,
                     use_aria2=use_aria2, run=run, client=client)
        except (SyncError, httpx.HTTPError) as exc:
            return False, f"{item.id}: could not fetch {item.source.url}: {exc}"
    epub_path.parent.mkdir(parents=True, exist_ok=True)
    proc = run(["ebook-convert", str(pdf_path), str(epub_path), "--title", item.title],
              capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not epub_path.exists():
        message = (proc.stderr or proc.stdout or "").strip()[:200]
        return False, f"{item.id}: ebook-convert failed: {message}"
    return True, f"{item.id}: {epub_path}"


def main(settings: Settings, only: list[str] | None = None, run: Callable = subprocess.run,
        client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which,
        use_aria2: bool | None = None) -> int:
    items = [i for i in load_manifests(settings.manifests) if i.source.tool == "pdf2epub"]
    if only:
        wanted = set(only)
        items = [i for i in items if i.id in wanted]
    failures = 0
    for item in items:
        ok, message = convert_one(item, settings, run=run, client=client, which=which, use_aria2=use_aria2)
        print(("OK   " if ok else "FAIL ") + message)
        if not ok:
            failures += 1
    return 1 if failures else 0
```

- [ ] **Step 4: Register the `build-books` subcommand**

In `api/sos/cli.py`, add a command function next to `cmd_build_crawl`:

```python
def cmd_build_books(settings: Settings, args) -> int:
    from sos import buildbooks

    only = [s for s in (args.only or "").split(",") if s] or None
    return buildbooks.main(settings, only=only)
```

In `build_parser`, next to the `build-crawl` subparser, add:

```python
    p = sub.add_parser("build-books", help="PC only: convert PDF library items to EPUB with Calibre")
    p.add_argument("--only", help="comma-separated item ids")
    p.set_defaults(func=cmd_build_books)
```

Also update the module docstring at the top of `cli.py` to mention `build-books`, matching how the others are listed:

```python
"""`sos` command line: sync, index, storage-event, validate-playbooks, build-maps, build-crawl, build-books, eval, pin, status."""
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd api && .venv/bin/pytest tests/test_buildbooks.py -q`
Expected: PASS.

- [ ] **Step 6: Run the full backend test suite**

Run: `cd api && .venv/bin/pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add api/sos/buildbooks.py api/sos/cli.py api/tests/test_buildbooks.py
git commit -m "$(cat <<'EOF'
cli: add sos build-books, converting a PDF library item to EPUB

PC-only, mirroring build-crawl and build-maps: for every manifest item
tooled pdf2epub, fetch the source PDF if needed and run Calibre's
ebook-convert. A failure is reported and the item is left untouched.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: The reader offers the original PDF layout for a converted book

**Files:**
- Modify: `web/src/api/types.ts`
- Modify: `web/src/screens/Doc.tsx`
- Test: `web/tests/screens/doc.test.tsx`

**Interfaces:**
- Consumes: `pdf_fallback_url` on the `/api/library/<id>` response (Task 2).
- Produces: `LibraryItem.pdf_fallback_url?: string | null`. No other file reads this in this plan, but it is the field the rest of the frontend (e.g. a future Library card badge) would read.

- [ ] **Step 1: Write the failing tests**

In `web/tests/screens/doc.test.tsx`, add two tests inside the `describe('Doc', ...)` block:

```tsx
  it('offers the original PDF layout for a converted book, and switches between the two viewers', async () => {
    const converted = { ...epubItem, pdf_fallback_url: '/docs/core/where-there-is-no-doctor.pdf' };
    vi.spyOn(api, 'libraryItem').mockResolvedValue(converted);
    const user = userEvent.setup();
    renderRoute('/doc/where-there-is-no-doctor');
    await screen.findByRole('button', { name: 'Next' });
    expect(screen.queryByTitle('Document')).toBeNull();

    await user.click(screen.getByRole('button', { name: 'Original PDF layout' }));
    const frame = (await screen.findByTitle('Document')) as HTMLIFrameElement;
    expect(frame).toHaveAttribute('src', expect.stringContaining('file=%2Fdocs%2Fcore%2Fwhere-there-is-no-doctor.pdf'));

    await user.click(screen.getByRole('button', { name: 'Reflowed text' }));
    expect(await screen.findByRole('button', { name: 'Next' })).toBeInTheDocument();
    expect(screen.queryByTitle('Document')).toBeNull();
  });

  it('shows no original-layout toggle for a book that was never converted from a PDF', async () => {
    vi.spyOn(api, 'libraryItem').mockResolvedValue(epubItem);
    renderRoute('/doc/where-there-is-no-doctor');
    await screen.findByRole('button', { name: 'Next' });
    expect(screen.queryByRole('button', { name: /Original PDF layout/ })).toBeNull();
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd web && npx vitest run tests/screens/doc.test.tsx`
Expected: FAIL — no "Original PDF layout" button exists yet.

- [ ] **Step 3: Add the field to `LibraryItem`**

In `web/src/api/types.ts`, in `LibraryItem`, immediately after the `file_url?: string | null;` line (and its comment), add:

```ts
  /** Where a converted book's original PDF sits, for the reader's one-tap fallback (spec section 6).
   * Absent for a book that was never a PDF, and absent until the fallback file is confirmed on this
   * box — never a link to a file that might not be there. */
  pdf_fallback_url?: string | null;
```

- [ ] **Step 4: Add the toggle to `Doc.tsx`**

In `web/src/screens/Doc.tsx`, in the `Doc()` function, add a `showOriginal` state next to `missing` and reset it when the document id changes:

```tsx
  const [showOriginal, setShowOriginal] = useState(false);
  useEffect(() => { setShowOriginal(false); }, [id]);
```

Replace the render block's final lines (from `const isDocument = ...` to the end of the return) with:

```tsx
  const isDocument = item?.kind === 'pdf' || item?.kind === 'epub';
  const gone = Boolean(item) && isDocument && (missing || !item!.available || !file);
  const hasOriginal = item?.kind === 'epub' && Boolean(item.pdf_fallback_url);
  return (
    <Screen title={item ? documentTitle(item.title) : 'Document'} fill={Boolean(item) && isDocument && !gone} search={false}>
      {loading && <p className="screen-body muted">Loading…</p>}
      {error && <p className="screen-body warning">Could not load this document: {error}</p>}
      {item && gone && <DocumentMissing item={item} />}
      {item && !gone && hasOriginal && (
        <div className="row no-print screen-body doc-original-toggle">
          <button type="button" className="btn btn-small" onClick={() => setShowOriginal((v) => !v)}>
            <Icon name={showOriginal ? 'book' : 'pdf'} size={18} />
            <span>{showOriginal ? 'Reflowed text' : 'Original PDF layout'}</span>
          </button>
        </div>
      )}
      {item && !gone && file && item.kind === 'pdf' && <PdfFrame url={file} theme={theme} hash={location.hash} onMissing={() => setMissing(true)} />}
      {item && !gone && file && item.kind === 'epub' && !showOriginal && <EpubReader url={file} theme={theme} />}
      {item && !gone && hasOriginal && showOriginal && <PdfFrame url={item!.pdf_fallback_url!} theme={theme} hash="" />}
      {item && !isDocument && <p className="screen-body warning">{documentTitle(item.title)} is not a PDF or EPUB.</p>}
    </Screen>
  );
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd web && npx vitest run tests/screens/doc.test.tsx`
Expected: PASS.

- [ ] **Step 6: Run the full frontend test suite**

Run: `cd web && npm test`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/api/types.ts web/src/screens/Doc.tsx web/tests/screens/doc.test.tsx
git commit -m "$(cat <<'EOF'
reader: offer the original PDF layout for a converted book

A small toggle in Doc.tsx switches between the existing EpubReader and
PdfChrome for a book that was converted from PDF, using the pdf_fallback_url
the API now serves. No new viewer code.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Install Calibre and convert one real book end to end

This task proves the mechanism on real content, using `nrpb-stable-iodine` (a small, already-downloaded real PDF at `/home/dan/sos-content/docs/nrpb-stable-iodine.pdf`, category `uk-official`) as the example. It is not TDD (it is a one-off content migration plus a manual verification), so it has no test-first step, but it ends by running every automated test the earlier tasks added.

**Files:**
- Modify: `manifest/core.json` (the `nrpb-stable-iodine` item)

- [ ] **Step 1: Install Calibre user-local**

```bash
wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin install_dir=$HOME/.local/opt/calibre isolated=y
ln -sf "$HOME/.local/opt/calibre/ebook-convert" "$HOME/.local/bin/ebook-convert"
ebook-convert --version
```

Expected: `ebook-convert --version` prints a Calibre version string. If `~/.local/bin` is not already on `PATH` in this shell, add it (it should already be, per the existing tool setup) before the last command.

- [ ] **Step 2: Edit the `nrpb-stable-iodine` manifest entry**

In `manifest/core.json`, the `nrpb-stable-iodine` item currently reads:

```json
    {
      "id": "nrpb-stable-iodine",
      "title": "Stable iodine prophylaxis: recommendations of the 2nd UK Working Group (NRPB 2001)",
      "kind": "pdf",
      "tier": "core",
      "category": "uk-official",
      "scenarios": ["nuclear-accident", "nuclear-war"],
      "source": {
        "type": "url",
        "url": "https://assets.publishing.service.gov.uk/media/5a81648ded915d74e623203a/Documents_of_the_NRPB_Volume_12_Number_3.pdf",
        "sha256": "eddfed6f927539dffe70f2a44d96df6d58c902ba408b7bbaf69b344f9561de99"
      },
      "dest": "docs/nrpb-stable-iodine.pdf",
      "size_bytes": 145428,
      "as_at": "2001-01",
      "licence": "OGL v3",
      "priority": 4,
      "description": "The UK dosing and age-group recommendations for potassium iodate tablets after a radioiodine release (Documents of the NRPB volume 12 number 3, 34 pages).",
      "search_weight": 1.4,
      "suggest": false
    },
```

Change it to (the `sha256` stays, so `sos build-books` verifies the fetched PDF before converting it; `size_bytes` is corrected in Step 3a below once the real EPUB exists):

```json
    {
      "id": "nrpb-stable-iodine",
      "title": "Stable iodine prophylaxis: recommendations of the 2nd UK Working Group (NRPB 2001)",
      "kind": "epub",
      "tier": "core",
      "category": "uk-official",
      "scenarios": ["nuclear-accident", "nuclear-war"],
      "source": {
        "type": "build",
        "tool": "pdf2epub",
        "artifact": "docs/nrpb-stable-iodine.epub",
        "url": "https://assets.publishing.service.gov.uk/media/5a81648ded915d74e623203a/Documents_of_the_NRPB_Volume_12_Number_3.pdf",
        "sha256": "eddfed6f927539dffe70f2a44d96df6d58c902ba408b7bbaf69b344f9561de99"
      },
      "dest": "docs/nrpb-stable-iodine.epub",
      "pdf_dest": "docs/nrpb-stable-iodine.pdf",
      "size_bytes": 145428,
      "as_at": "2001-01",
      "licence": "OGL v3",
      "priority": 4,
      "description": "The UK dosing and age-group recommendations for potassium iodate tablets after a radioiodine release (Documents of the NRPB volume 12 number 3, 34 pages).",
      "search_weight": 1.4,
      "suggest": false
    },
```

- [ ] **Step 3: Run `sos build-books` against the real PDF**

```bash
SOS_CORE=/home/dan/sos-content SOS_MANIFEST_DIR=manifest api/.venv/bin/sos build-books --only nrpb-stable-iodine
```

Expected: a line starting `OK   nrpb-stable-iodine: /home/dan/sos-content/docs/nrpb-stable-iodine.epub`, and that file now exists and is a valid EPUB (`file /home/dan/sos-content/docs/nrpb-stable-iodine.epub` reports `EPUB document`).

- [ ] **Step 3a: Correct `size_bytes` to the real EPUB's size**

```bash
stat -c%s /home/dan/sos-content/docs/nrpb-stable-iodine.epub
```

Edit `manifest/core.json`'s `nrpb-stable-iodine` item, setting `size_bytes` to that number.

- [ ] **Step 4: Verify the manifest and schema still validate**

Run: `cd api && .venv/bin/pytest tests/test_manifest.py tests/test_manifest_content.py -q`
Expected: PASS (confirms the hand-edited entry is well-formed and the content-pinning tests in `test_manifest_content.py` still find `nrpb-stable-iodine` by id).

- [ ] **Step 5: Run the full backend and frontend test suites**

```bash
cd api && .venv/bin/pytest -q
cd ../web && npm test
```

Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add manifest/core.json
git commit -m "$(cat <<'EOF'
content: convert nrpb-stable-iodine to EPUB, proving the pdf2epub pipeline

First real book through sos build-books, with its original PDF kept as
the reader's fallback. The remaining PDF library items convert the same
way: edit kind/source/dest/pdf_dest, then sos build-books --only <id>.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## After this plan

Every other `kind: "pdf"` item in `manifest/core.json` (roughly 80 books — the Hesperian guides, US/UK field manuals, the OpenStax textbook set, the Building Regulations Approved Documents) converts the same way Task 5 converted `nrpb-stable-iodine`: edit that item's `kind`/`source`/`dest`/`pdf_dest`, then run `sos build-books --only <id>` (or with no `--only`, to convert everything still pending in one pass once every entry is edited). The `scmg-*` chapter PDFs stay one manifest item per chapter, each becoming its own small EPUB, per the spec's scope decision (section 3). That bulk migration is content curation, not further coding, and is intentionally left out of this plan's tasks.
