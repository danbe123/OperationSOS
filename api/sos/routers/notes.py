from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sos.db import now_iso
from sos.routers import get_db

router = APIRouter(tags=["notes"])


class NoteIn(BaseModel):
    kind: Literal["note", "pin"] = "note"
    title: str = ""
    body: str = ""
    lat: float | None = None
    lon: float | None = None


class NotePatch(BaseModel):
    kind: Literal["note", "pin"] | None = None
    title: str | None = None
    body: str | None = None
    lat: float | None = None
    lon: float | None = None


def _row(r) -> dict:
    return {"id": r["id"], "kind": r["kind"], "title": r["title"] or "", "body": r["body"] or "",
            "lat": r["lat"], "lon": r["lon"], "updated_at": r["updated_at"]}


def _get(conn, note_id: int):
    row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return row


def _check_pin(kind: str, lat, lon) -> None:
    if kind == "pin" and (lat is None or lon is None):
        raise HTTPException(status_code=400, detail="Pins need lat and lon")


@router.get("/notes")
def list_notes(kind: str | None = None, conn=Depends(get_db)):
    if kind:
        rows = conn.execute("SELECT * FROM notes WHERE kind=? ORDER BY id", (kind,))
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY id")
    return [_row(r) for r in rows]


@router.post("/notes")
def create_note(body: NoteIn, conn=Depends(get_db)):
    _check_pin(body.kind, body.lat, body.lon)
    cur = conn.execute("INSERT INTO notes(kind, title, body, lat, lon, updated_at) VALUES (?,?,?,?,?,?)",
                       (body.kind, body.title, body.body, body.lat, body.lon, now_iso()))
    conn.commit()
    return _row(_get(conn, cur.lastrowid))


@router.put("/notes/{note_id}")
def update_note(note_id: int, body: NotePatch, conn=Depends(get_db)):
    current = _get(conn, note_id)
    merged = {k: (getattr(body, k) if getattr(body, k) is not None else current[k]) for k in ("kind", "title", "body", "lat", "lon")}
    _check_pin(merged["kind"], merged["lat"], merged["lon"])
    conn.execute("UPDATE notes SET kind=?, title=?, body=?, lat=?, lon=?, updated_at=? WHERE id=?",
                 (merged["kind"], merged["title"], merged["body"], merged["lat"], merged["lon"], now_iso(), note_id))
    conn.commit()
    return _row(_get(conn, note_id))


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, conn=Depends(get_db)):
    _get(conn, note_id)
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    return {"ok": True}
