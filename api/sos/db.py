"""SQLite access: connection factory, schema and the settings key/value table."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS library_items (
  id TEXT PRIMARY KEY, title, kind, tier, category, scenarios_json, dest, size_bytes INTEGER, as_at, licence,
  priority INTEGER, reader_home, description, search_weight REAL NOT NULL DEFAULT 1.0, suggest INTEGER NOT NULL DEFAULT 0,
  overlay_json, available INTEGER NOT NULL DEFAULT 0, local_path, fts INTEGER NOT NULL DEFAULT 0,
  resolved_name, resolved_size INTEGER, resolved_as_at);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_docs USING fts5(
  title, body, doc_id UNINDEXED, kind UNINDEXED, category UNINDEXED, scenarios UNINDEXED, page UNINDEXED, url UNINDEXED,
  tokenize='porter unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS fts_places USING fts5(
  name, kind UNINDEXED, lat UNINDEXED, lon UNINDEXED, region UNINDEXED, postcode UNINDEXED,
  tokenize='unicode61 remove_diacritics 2', prefix='2 3 4');
CREATE TABLE IF NOT EXISTS checklist_state (playbook TEXT, item_id TEXT, checked INTEGER NOT NULL, updated_at TEXT, PRIMARY KEY (playbook, item_id));
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL DEFAULT 'note', title TEXT, body TEXT, lat REAL, lon REAL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS household (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER, needs TEXT,
  medications TEXT, contacts TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
  quantity REAL NOT NULL, unit TEXT NOT NULL, per_person_day REAL, expires TEXT, notes TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS search_cache (q TEXT PRIMARY KEY, results_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS places_meta (key TEXT PRIMARY KEY, value TEXT);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
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
