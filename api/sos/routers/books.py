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
