"""The Gutenberg catalogue (spec section 4 as amended 2026-09-17).

`index_books` opens a book ZIM straight from disk with libzim and rewrites the books/fts_books tables from the
scraper's own catalogue entry; the query helpers below are what the /api/books router serves. Read-only against
the ZIM. Every entry-name rule of the scraper's layout is in the constants at the top: a later gutenberg2zim
release that moves to its JSON layout costs a change here, not a redesign.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Protocol
from urllib.parse import quote

from sos.db import get_setting, set_setting

log = logging.getLogger(__name__)

BOOK_ZIMS = ("gutenberg_en_all",)

# gutenberg2zim 3.0.1 (the scraper behind the 2025-11 build) writes the catalogue as JavaScript: one array per book,
# [title, author name, "hep" (html/epub/pdf as 0 or 1), Gutenberg id, Library of Congress shelf code], most
# downloaded first. The HTML article is <slug>.<id> (no extension), the EPUB and PDF are <slug>.<id>.<format>;
# covers are covers/<id>_cover_image.jpg.
CATALOGUE_ENTRY = "full_by_popularity.js"
COVER_ENTRIES = ("covers/{id}_cover_image.jpg", "covers/{id}_cover_image.webp")
SLUG_MAX = 230

# The scraper's own shelf names (locales/en.json, the "lcc-shelf-*" strings), the code prefix dropped.
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
        out.append(CatalogueEntry(title=str(title), author=str(author or ""), flags=str(flags), id=int(book_id),
                                  shelf=str(shelf)))
    return out


def _file_stamp(path: Path) -> str | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return f"{st.st_size}:{st.st_mtime_ns}"


def index_books(conn: sqlite3.Connection, open_zim: Callable[[Path], ZimReader] = open_zim) -> int:
    """Rewrite books/fts_books for every BOOK_ZIMS item that is on the box. Returns the number of books indexed.
    A ZIM that is absent, unreadable or has no usable catalogue is a warning that leaves the tables as they were;
    `sos index` carries on either way. A ZIM whose size and mtime have not changed since the last import is
    skipped: walking the archive for 70,000 EPUBs and covers takes a minute on the Pi."""
    total = 0
    for zim in BOOK_ZIMS:
        row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (zim,)).fetchone()
        if row is None or not row["available"] or not row["local_path"]:
            continue
        path = Path(row["local_path"])
        stamp = _file_stamp(path)
        have = conn.execute("SELECT count(*) AS n FROM books WHERE zim=?", (zim,)).fetchone()["n"]
        if stamp and have and get_setting(conn, f"books_stamp:{zim}") == stamp:
            log.info("index: %d books from %s (unchanged)", have, zim)
            total += have
            continue
        try:
            reader = open_zim(path)
            raw = reader.read(CATALOGUE_ENTRY)
            if raw is None:
                log.warning("index_books: %s: no %s entry in the ZIM (a different scraper layout?)", zim, CATALOGUE_ENTRY)
                continue
            entries = parse_catalogue(raw)
            count = len(entries)
            rows: list[tuple] = []
            missing_epubs = 0
            for position, entry in enumerate(entries):
                slug = entry_slug(entry.title)
                html_path = f"{slug}.{entry.id}" if entry.has_html and reader.has(f"{slug}.{entry.id}") else None
                epub_path = f"{slug}.{entry.id}.epub" if entry.has_epub else None
                if epub_path and not reader.has(epub_path):
                    missing_epubs += 1
                    epub_path = None
                cover_path = next((c.format(id=entry.id) for c in COVER_ENTRIES if reader.has(c.format(id=entry.id))), None)
                rows.append((zim, entry.id, entry.title, entry.author or None, entry.shelf or None, count - position,
                             epub_path, html_path, cover_path))
        except (OSError, RuntimeError, ValueError, TypeError, ImportError, UnicodeDecodeError) as exc:
            log.warning("index_books: %s: could not read the catalogue: %s", zim, exc)
            continue
        with conn:
            conn.execute("DELETE FROM books WHERE zim=?", (zim,))
            conn.executemany(
                "INSERT OR REPLACE INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) "
                "VALUES (?,?,?,?,?,?,?,?,?)", rows)
            # External-content FTS5 does not follow deletes on its content table: rebuild the index from `books`.
            conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
        if stamp:
            set_setting(conn, f"books_stamp:{zim}", stamp)
        log.info("index: %d books from %s (%d flagged EPUBs missing)", len(rows), zim, missing_epubs)
        total += len(rows)
    return total


# --- what the API serves ---------------------------------------------------------------------------------------


def available_zim(conn: sqlite3.Connection) -> str | None:
    for zim in BOOK_ZIMS:
        row = conn.execute("SELECT available FROM library_items WHERE id=?", (zim,)).fetchone()
        if row is not None and row["available"]:
            return zim
    return None


def content_url(zim: str, path: str | None) -> str | None:
    """Where kiwix-serve hands the entry out as-is (an EPUB, a cover), through Caddy on the same origin."""
    return f"/kiwix/content/{zim}/{quote(path, safe='/')}" if path else None


def reader_url(zim: str, path: str | None) -> str | None:
    """The app's Kiwix reader route for the book's HTML page."""
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
        clauses.append("b.author = ?")
        params.append(author)
    if shelf:
        clauses.append("b.shelf = ?")
        params.append(shelf)
    where = " AND ".join(clauses)
    if terms:
        # CROSS JOIN pins the plan to the FTS index first; left to itself SQLite starts from books_shelf and runs
        # the MATCH once per row, which is seconds per keystroke on a 70,000-row catalogue.
        sql_from = f"FROM fts_books f CROSS JOIN books b ON b.rowid = f.rowid WHERE fts_books MATCH ? AND {where}"
        params = [query_mod.fts_match(terms, "and"), *params]
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
    """The app route a shelf entry opens: keys are `gutenberg:<id>` for a collection book, `doc:<id>` for a Library EPUB."""
    kind, _, rest = key.partition(":")
    if kind == "gutenberg" and rest.isdigit():
        return f"/book/gutenberg/{rest}"
    if kind == "doc" and rest:
        return f"/doc/{quote(rest)}"
    return None
