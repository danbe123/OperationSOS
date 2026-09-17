"""library_items: the manifest mirrored into SQLite plus runtime columns (availability, local path,
full-text flag, resolved download metadata), library.xml generation and the /api/library shapes."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from sos.books import BOOK_ZIMS
from sos.config import Settings
from sos.manifest import Item

log = logging.getLogger(__name__)
KIWIX_MANAGE = "kiwix-manage"

CATEGORY_ORDER = ["playbooks", "uk-official", "medical", "survival", "reference", "practical", "maps", "education", "books", "media", "ai"]
CATEGORY_TITLES = {
    "playbooks": "Playbooks", "uk-official": "UK official guidance", "medical": "Medical", "survival": "Survival",
    "reference": "Reference", "practical": "Practical and repair", "maps": "Maps", "education": "Education",
    "books": "Books", "media": "Media", "ai": "AI models",
}
EMPTY_LIBRARY = '<?xml version="1.0" encoding="UTF-8"?>\n<library version="20110515">\n</library>\n'


def upsert_items(conn: sqlite3.Connection, items: list[Item]) -> None:
    ids = [i.id for i in items]
    for it in items:
        conn.execute(
            """INSERT INTO library_items(id, title, kind, tier, category, scenarios_json, dest, pdf_dest, size_bytes, as_at, licence,
                 priority, reader_home, description, search_weight, suggest, overlay_json, source_type, source_tool)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title, kind=excluded.kind, tier=excluded.tier,
                 category=excluded.category, scenarios_json=excluded.scenarios_json, dest=excluded.dest, pdf_dest=excluded.pdf_dest,
                 size_bytes=excluded.size_bytes, as_at=excluded.as_at, licence=excluded.licence, priority=excluded.priority,
                 reader_home=excluded.reader_home, description=excluded.description, search_weight=excluded.search_weight,
                 suggest=excluded.suggest, overlay_json=excluded.overlay_json, source_type=excluded.source_type,
                 source_tool=excluded.source_tool""",
            (it.id, it.title, it.kind, it.tier, it.category, json.dumps(it.scenarios), it.dest, it.pdf_dest, it.size_bytes, it.as_at,
             it.licence, it.priority, it.reader_home, it.description, it.search_weight, int(it.suggest),
             json.dumps(it.overlay.model_dump()) if it.overlay else None, it.source.type, it.source.tool),
        )
    if ids:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(f"DELETE FROM library_items WHERE id NOT IN ({placeholders})", ids)
    else:
        conn.execute("DELETE FROM library_items")
    conn.commit()


def ext_mounted(settings: Settings) -> bool:
    if not settings.ext.is_dir():
        return False
    return True if settings.dev else os.path.ismount(settings.ext)


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


def zim_rows(conn: sqlite3.Connection, available_only: bool = True) -> list[sqlite3.Row]:
    sql = "SELECT * FROM library_items WHERE kind='zim'"
    if available_only:
        sql += " AND available=1"
    return conn.execute(sql + " ORDER BY priority, id").fetchall()


def write_library_xml(conn: sqlite3.Connection, settings: Settings, include_ext: bool = True) -> Path:
    """Regenerate library.xml from scratch with `kiwix-manage add`, one call per file so
    --zimPathToSave keeps absolute paths. Missing files are skipped (the item stays unavailable)."""
    path = settings.library_xml
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".xml.tmp")
    if tmp.exists():
        tmp.unlink()
    tmp.write_text(EMPTY_LIBRARY, encoding="utf-8")
    for row in zim_rows(conn):
        if row["tier"] == "extended" and not include_ext:
            continue
        zim = Path(row["local_path"] or "")
        if not zim.exists():
            continue
        proc = subprocess.run([KIWIX_MANAGE, str(tmp), "add", f"--zimPathToSave={zim}", str(zim)],
                              capture_output=True, text=True, check=False)
        if proc.returncode != 0:  # a corrupt or partial ZIM must not take the whole library down
            log.warning("kiwix-manage rejected %s: %s", zim.name, (proc.stderr or proc.stdout).strip())
            conn.execute("UPDATE library_items SET available=0, local_path=NULL WHERE id=?", (row["id"],))
            conn.commit()
    os.replace(tmp, path)
    return path


def parse_library_xml(path: Path) -> dict[str, dict]:
    """{book id (filename stem): {fts, language, title}} from kiwix-manage's XML."""
    if not Path(path).exists():
        return {}
    root = ET.parse(path).getroot()
    info: dict[str, dict] = {}
    for book in root.iter("book"):
        book_path = book.get("path") or ""
        book_id = Path(book_path).stem
        tags = book.get("tags") or ""
        info[book_id] = {
            "fts": "_ftindex:yes" in tags.split(";"),
            "language": (book.get("language") or "eng").split(",")[0],
            "title": book.get("title") or book_id,
        }
    return info


def apply_library_flags(conn: sqlite3.Connection, info: dict[str, dict]) -> None:
    conn.execute("UPDATE library_items SET fts=0 WHERE kind='zim'")
    for book_id, meta in info.items():
        conn.execute("UPDATE library_items SET fts=? WHERE id=?", (int(meta["fts"]), book_id))
    conn.commit()


def rescan(conn: sqlite3.Connection, settings: Settings) -> dict:
    """Seconds, never touches fts_docs or fts_places: availability, library.xml, fts flags, cache flush."""
    from sos.db import set_setting

    total, available = refresh_items(conn, settings)
    xml = write_library_xml(conn, settings)
    info = parse_library_xml(xml)
    apply_library_flags(conn, info)
    set_setting(conn, "zim_languages", json.dumps({k: v["language"] for k, v in info.items()}))
    conn.execute("DELETE FROM search_cache")
    conn.commit()
    return {"items": total, "available": available}


def drive_label(row: sqlite3.Row, ext_ok: bool) -> str:
    if row["tier"] != "extended":
        return "Core"
    return "External drive" if ext_ok else "On external drive (not connected)"


def reader_url(row: sqlite3.Row) -> str | None:
    if not row["available"]:
        return None
    if row["kind"] == "zim" and row["id"] in BOOK_ZIMS:
        return "/library/books"  # the catalogue screen, not the ZIM's own front page
    if row["kind"] == "zim":
        home = (row["reader_home"] or "").lstrip("/")
        return f"/read/{row['id']}/{home}"
    if row["kind"] in ("pdf", "epub"):
        return f"/doc/{row['id']}"
    return None


def file_url(row: sqlite3.Row) -> str | None:
    """Where the PDF or EPUB itself is served (Caddy maps /docs/<tier>/ to the tier's docs folder); the reader route
    is `reader_url`. Viewers must load this, never the app route."""
    if not row["available"] or row["kind"] not in ("pdf", "epub"):
        return None
    dest = str(row["dest"] or "")
    # The kind picks the viewer, so the file must match it: a `pdf` row whose dest is the EPUB it was
    # converted to (the manifest mid-conversion) hands the PDF viewer its PDF, not a blank page.
    if row["kind"] == "pdf" and dest.endswith(".epub") and row["pdf_dest"]:
        dest = str(row["pdf_dest"])
    name = dest.rsplit("/", 1)[-1]
    return f"/docs/{'extended' if row['tier'] == 'extended' else 'core'}/{name}" if name else None


def pdf_fallback_url(row: sqlite3.Row) -> str | None:
    """Where a converted book's original PDF sits, for the reader's one-tap fallback (spec section 6).
    None for a book that was never a PDF, and None until the fallback file is confirmed on this box —
    never a link to a file that might not be there."""
    if row["kind"] != "epub" or not row["pdf_dest"] or not row["pdf_available"]:
        return None
    name = str(row["pdf_dest"]).rsplit("/", 1)[-1]
    return f"/docs/{'extended' if row['tier'] == 'extended' else 'core'}/{name}" if name else None


def fetch_state(row: sqlite3.Row, ext_ok: bool) -> str | None:
    """How an item that is not on the box gets here, for the card to say and offer:
    `download` (the box can fetch it itself), `drive` (it lives on the external drive, not plugged in),
    `build` (made on a PC with a `sos build-…` tool and copied over), `own` (the owner's own files).
    None when it is here already."""
    if row["available"]:
        return None
    if row["kind"] == "dir":
        return "own"
    if row["source_type"] == "build":
        return "build"
    if row["tier"] == "extended" and not ext_ok:
        return "drive"
    if row["source_type"] in ("kiwix", "url"):
        return "download"
    return None


def item_dict(row: sqlite3.Row, ext_ok: bool) -> dict:
    return {
        "source_type": row["source_type"], "build_tool": row["source_tool"] if row["source_type"] == "build" else None,
        "fetch": fetch_state(row, ext_ok),
        "id": row["id"], "title": row["title"], "kind": row["kind"], "tier": row["tier"], "category": row["category"],
        "scenarios": json.loads(row["scenarios_json"] or "[]"), "size_bytes": row["size_bytes"] or 0,
        "as_at": row["resolved_as_at"] or row["as_at"], "licence": row["licence"], "available": bool(row["available"]),
        "url": reader_url(row), "file_url": file_url(row), "pdf_fallback_url": pdf_fallback_url(row), "description": row["description"],
        "drive_label": drive_label(row, ext_ok),
    }


def get_item(conn: sqlite3.Connection, item_id: str) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM library_items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        row = conn.execute("SELECT * FROM library_items WHERE resolved_name=? ORDER BY available DESC, priority LIMIT 1", (item_id,)).fetchone()
    return row


def library_response(conn: sqlite3.Connection, settings: Settings) -> dict:
    ext_ok = ext_mounted(settings)
    groups: dict[str, list[dict]] = {}
    for row in conn.execute("SELECT * FROM library_items ORDER BY priority, title").fetchall():
        groups.setdefault(row["category"], []).append(item_dict(row, ext_ok))
    return {"categories": [{"id": c, "title": CATEGORY_TITLES[c], "items": groups[c]} for c in CATEGORY_ORDER if c in groups]}
