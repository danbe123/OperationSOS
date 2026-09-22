"""SQLite access: connection factory, schema and the settings key/value table."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

FTS_DOCS_DDL = """fts5(
  title, body, doc_id UNINDEXED, kind UNINDEXED, category UNINDEXED, scenarios UNINDEXED, page UNINDEXED, url UNINDEXED,
  aliases, tokenize='porter unicode61 remove_diacritics 2')"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS library_items (
  id TEXT PRIMARY KEY, title, kind, tier, category, scenarios_json, dest, pdf_dest, size_bytes INTEGER, as_at, licence,
  priority INTEGER, reader_home, description, search_weight REAL NOT NULL DEFAULT 1.0, suggest INTEGER NOT NULL DEFAULT 0,
  overlay_json, available INTEGER NOT NULL DEFAULT 0, local_path, fts INTEGER NOT NULL DEFAULT 0,
  resolved_name, resolved_size INTEGER, resolved_as_at, pdf_available INTEGER NOT NULL DEFAULT 0, source_type, source_tool);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_docs USING {fts_docs};
CREATE TABLE IF NOT EXISTS card_subjects (page TEXT PRIMARY KEY, title TEXT NOT NULL, conditions TEXT NOT NULL DEFAULT '[]',
  aliases TEXT NOT NULL DEFAULT '[]');
CREATE VIRTUAL TABLE IF NOT EXISTS fts_places USING fts5(
  name, kind UNINDEXED, lat UNINDEXED, lon UNINDEXED, region UNINDEXED, postcode UNINDEXED,
  tokenize='unicode61 remove_diacritics 2', prefix='2 3 4');
CREATE TABLE IF NOT EXISTS checklist_state (playbook TEXT, item_id TEXT, checked INTEGER NOT NULL, updated_at TEXT, PRIMARY KEY (playbook, item_id));
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL DEFAULT 'note', title TEXT, body TEXT, lat REAL, lon REAL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS household (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER, needs TEXT,
  medications TEXT, contacts TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
  quantity REAL NOT NULL, unit TEXT NOT NULL, per_person_day REAL, expires TEXT, notes TEXT, kit_item TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS conditions (id TEXT PRIMARY KEY, state TEXT NOT NULL, since TEXT, source TEXT NOT NULL DEFAULT 'manual',
  confidence REAL NOT NULL DEFAULT 1.0, note TEXT, set_by TEXT, updated_at TEXT, confirmed_at TEXT);
CREATE TABLE IF NOT EXISTS task_state (task_id TEXT PRIMARY KEY, done INTEGER NOT NULL DEFAULT 0, done_at TEXT, person TEXT,
  updated_at TEXT, drill INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sensor_readings (id INTEGER PRIMARY KEY AUTOINCREMENT, sensor TEXT NOT NULL, value REAL, unit TEXT, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS sensor_readings_at ON sensor_readings(sensor, at);
CREATE TABLE IF NOT EXISTS neighbours (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT, needs TEXT, skills TEXT,
  contacts TEXT, notes TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS search_cache (q TEXT PRIMARY KEY, results_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS places_meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS books (zim TEXT NOT NULL, id INTEGER NOT NULL, title TEXT NOT NULL, author TEXT, shelf TEXT,
  popularity INTEGER NOT NULL DEFAULT 0, epub_path TEXT, html_path TEXT, cover_path TEXT, PRIMARY KEY (zim, id));
CREATE INDEX IF NOT EXISTS books_popularity ON books(zim, popularity DESC);
CREATE INDEX IF NOT EXISTS books_shelf ON books(zim, shelf);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_books USING fts5(title, author, content='books', content_rowid='rowid',
  tokenize='porter unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS reading (key TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, cover_url TEXT, cfi TEXT NOT NULL,
  percent REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recent (key TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL, cover_url TEXT,
  viewed_at TEXT NOT NULL);
""".replace("{fts_docs}", FTS_DOCS_DDL)


# The keyword index's columns, and bm25's weight for each: a title counts five times a body word, a card's aliases
# (task 25: other ways a household words the card's subject, `playbooks/cards/*.md` front matter) as much as its
# title, the unindexed bookkeeping columns nothing. `aliases` is appended so the body stays column 1 for snippet().
FTS_DOCS_COLUMNS = ("title", "body", "doc_id", "kind", "category", "scenarios", "page", "url", "aliases")
FTS_DOCS_BM25 = "bm25(fts_docs, 5.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0)"


def connect(path: Path | str, *, durable: bool = False) -> sqlite3.Connection:
    """A connection to the box's database, in WAL mode.

    `durable=False` is `synchronous=NORMAL`: the WAL is synced only when it is checkpointed, so a power cut
    can lose the last few commits (never corrupt the file). That is right for the search cache and the index
    rebuild, which are fast bulk writes of things that can be made again. `durable=True` is
    `synchronous=FULL`: the WAL is synced before a commit returns, so what the household was told is saved
    survives a power cut. Use it for what people enter: ticks, notes, pins, conditions, settings."""
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA synchronous={'FULL' if durable else 'NORMAL'}")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """Add a column to a table created by an older schema. SQLite has no ADD COLUMN IF NOT EXISTS."""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _migrate_fts_docs(conn: sqlite3.Connection) -> None:
    """An index made before the `aliases` column (task 25) is rebuilt with it, its rows carried over: an FTS5 table
    cannot gain a column. Once, on the first start after the upgrade; `sos index` fills the aliases."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(fts_docs)")]
    if not cols or "aliases" in cols:
        return
    old = ", ".join(c for c in FTS_DOCS_COLUMNS if c != "aliases")
    conn.execute("DROP TABLE IF EXISTS fts_docs_upgrade")
    conn.execute(f"CREATE VIRTUAL TABLE fts_docs_upgrade USING {FTS_DOCS_DDL}")
    conn.execute(f"INSERT INTO fts_docs_upgrade({old}) SELECT {old} FROM fts_docs ORDER BY rowid")
    conn.execute("DROP TABLE fts_docs")
    conn.execute("ALTER TABLE fts_docs_upgrade RENAME TO fts_docs")
    conn.commit()


def init_schema(conn: sqlite3.Connection) -> None:
    _migrate_fts_docs(conn)
    conn.executescript(SCHEMA)
    _ensure_column(conn, "stock", "kit_item", "TEXT")
    _ensure_column(conn, "library_items", "pdf_dest", "TEXT")
    _ensure_column(conn, "library_items", "pdf_available", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "library_items", "source_type", "TEXT")
    _ensure_column(conn, "library_items", "source_tool", "TEXT")
    conn.commit()


def fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.__fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE temp.__fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None or row["value"] is None:
        return default
    return row["value"]


def set_setting(conn: sqlite3.Connection, key: str, value: str | None) -> None:
    if value is None:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
    else:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
    conn.commit()
