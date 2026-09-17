"""The Gutenberg catalogue and the reading-position table (spec sections 4 and 7)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

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


# --- last viewed: one list across the whole Library --------------------------------------------
# What the household opened last, whatever it was — a book, a guide, an article, a page, a card — for
# the Library's front. Shared by everyone on the box, as the ticks and the reading places are. The
# list is kept to the last sixty; the front shows a dozen.
RECENT_KEEP = 60
RECENT_KINDS = ("book", "doc", "article", "page", "module", "guide", "card")


class RecentBody(BaseModel):
    kind: Literal["book", "doc", "article", "page", "module", "guide", "card"]
    title: str = Field(min_length=1)
    url: str = Field(min_length=1, pattern=r"^/")
    cover_url: str | None = None


@router.get("/recent")
def list_recent(limit: int = 12, conn=Depends(get_db)):
    limit = max(1, min(RECENT_KEEP, limit))
    return [dict(r) for r in conn.execute("SELECT * FROM recent ORDER BY viewed_at DESC, rowid DESC LIMIT ?", (limit,)).fetchall()]


@router.put("/recent/{key:path}")   # an article's key carries its path, slashes and all
def put_recent(key: str, body: RecentBody, conn=Depends(get_db)):
    conn.execute(
        "INSERT INTO recent (key, kind, title, url, cover_url, viewed_at) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET kind=excluded.kind, title=excluded.title, url=excluded.url, cover_url=excluded.cover_url, "
        "viewed_at=excluded.viewed_at",
        (key, body.kind, body.title, body.url, body.cover_url, datetime.now(timezone.utc).isoformat()))
    conn.execute("DELETE FROM recent WHERE key NOT IN (SELECT key FROM recent ORDER BY viewed_at DESC, rowid DESC LIMIT ?)", (RECENT_KEEP,))
    conn.commit()
    return {"ok": True}


@router.delete("/recent/{key:path}")
def delete_recent(key: str, conn=Depends(get_db)):
    conn.execute("DELETE FROM recent WHERE key=?", (key,))
    conn.commit()
    return {"ok": True}
