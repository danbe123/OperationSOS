"""fts_places: import from places.csv(.gz) when the file changes; prefix queries for the map; exact lookups for search."""
from __future__ import annotations

import csv
import gzip
import sqlite3
from pathlib import Path

from sos.config import Settings
from sos.query import fts5_match, tokenise

KIND_RANK = {"city": 0, "town": 1, "village": 2, "suburb": 3, "hamlet": 4, "locality": 5, "road": 6, "postcode": 7}
_KIND_CASE = "CASE kind " + " ".join(f"WHEN '{k}' THEN {v}" for k, v in KIND_RANK.items()) + " ELSE 8 END"


def places_path(settings: Settings) -> Path:
    return settings.core / "maps" / "places.csv.gz"


def _signature(path: Path) -> str:
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")


def import_places(conn: sqlite3.Connection, path: Path, force: bool = False) -> int | None:
    path = Path(path)
    if not path.exists():
        return 0
    sig = _signature(path)
    row = conn.execute("SELECT value FROM places_meta WHERE key='signature'").fetchone()
    if not force and row is not None and row["value"] == sig:
        return None
    conn.execute("DELETE FROM fts_places")
    count = 0
    with _open_text(path) as fh:
        batch: list[tuple] = []
        for rec in csv.DictReader(fh):
            try:
                lat, lon = float(rec["lat"]), float(rec["lon"])
            except (TypeError, ValueError, KeyError):
                continue
            batch.append((rec.get("name", "").strip(), rec.get("kind", "").strip(), lat, lon,
                          rec.get("region", "").strip(), (rec.get("postcode") or "").strip() or None))
            if len(batch) >= 5000:
                conn.executemany("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)", batch)
                count += len(batch)
                batch = []
        if batch:
            conn.executemany("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)", batch)
            count += len(batch)
    conn.execute("INSERT INTO places_meta(key, value) VALUES ('signature', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (sig,))
    conn.commit()
    return count


def _row(r: sqlite3.Row) -> dict:
    return {"name": r["name"], "kind": r["kind"], "lat": float(r["lat"]), "lon": float(r["lon"]),
            "region": r["region"], "postcode": r["postcode"] or None}


def query_places(conn: sqlite3.Connection, q: str, limit: int = 10) -> list[dict]:
    q = (q or "").strip()
    if len(q) < 3:
        return []
    tokens = tokenise(q)
    if not tokens:
        return []
    limit = max(1, min(int(limit or 10), 25))
    match = " ".join(f'"{t}"*' for t in tokens)
    rows = conn.execute(
        f"SELECT name, kind, lat, lon, region, postcode FROM fts_places WHERE fts_places MATCH ? "
        f"ORDER BY {_KIND_CASE}, length(name), name LIMIT ?",
        (match, limit),
    ).fetchall()
    return [_row(r) for r in rows]


def exact_place(conn: sqlite3.Connection, name: str) -> dict | None:
    norm = " ".join((name or "").split()).lower()
    tokens = tokenise(norm)
    if not tokens:
        return None
    squashed = norm.replace(" ", "")
    rows = conn.execute(
        f"SELECT name, kind, lat, lon, region, postcode FROM fts_places WHERE fts_places MATCH ? ORDER BY {_KIND_CASE} LIMIT 50",
        (fts5_match(tokens),),
    ).fetchall()
    for r in rows:
        candidate = r["name"].lower()
        if candidate == norm or candidate.replace(" ", "") == squashed:
            return _row(r)
    # A squashed lookup like "sw1a1aa" tokenises to a single token that never matches the
    # space-separated tokens the index stores, so fall back to a full scan on the small table.
    rows = conn.execute(
        "SELECT name, kind, lat, lon, region, postcode FROM fts_places WHERE REPLACE(lower(name), ' ', '') = ?",
        (squashed,),
    ).fetchall()
    return _row(rows[0]) if rows else None
