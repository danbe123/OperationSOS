"""The street list (spec section 8): who lives nearby, what they need and what they can do.

The register is deliberately the same shape as the household one, because in a long emergency the street is the
household that matters. The rules read `needs` to say who to knock on first and `skills` to say who to fetch;
`street_list` prints the whole thing on one sheet of paper, because the printed copy is the one that survives
a flat battery."""
from __future__ import annotations

import sqlite3
from typing import Iterable, Optional

from sos.db import now_iso

FIELDS = ("name", "address", "needs", "skills", "contacts", "notes")


def row(r) -> dict:
    """One neighbour, as the API returns it."""
    return {"id": r["id"], "name": r["name"], "address": r["address"] or "", "needs": r["needs"] or "",
            "skills": r["skills"] or "", "contacts": r["contacts"] or "", "notes": r["notes"] or "",
            "updated_at": r["updated_at"]}


def listing(conn: sqlite3.Connection) -> list[dict]:
    return [row(r) for r in conn.execute("SELECT * FROM neighbours ORDER BY name COLLATE NOCASE, id")]


def get(conn: sqlite3.Connection, neighbour_id: int) -> Optional[dict]:
    found = conn.execute("SELECT * FROM neighbours WHERE id=?", (neighbour_id,)).fetchone()
    return row(found) if found is not None else None


def add(conn: sqlite3.Connection, values: dict, updated_at: Optional[str] = None) -> dict:
    fields = {k: (values.get(k) or "") for k in FIELDS}
    cur = conn.execute(
        "INSERT INTO neighbours(name, address, needs, skills, contacts, notes, updated_at) VALUES (?,?,?,?,?,?,?)",
        (fields["name"].strip(), fields["address"], fields["needs"], fields["skills"], fields["contacts"],
         fields["notes"], updated_at or now_iso()))
    conn.commit()
    return get(conn, cur.lastrowid) or {}


def update(conn: sqlite3.Connection, neighbour_id: int, values: dict, updated_at: Optional[str] = None) -> dict:
    current = get(conn, neighbour_id) or {}
    merged = {k: (values[k] if values.get(k) is not None else current.get(k, "")) for k in FIELDS}
    conn.execute("UPDATE neighbours SET name=?, address=?, needs=?, skills=?, contacts=?, notes=?, updated_at=? WHERE id=?",
                 (merged["name"].strip(), merged["address"], merged["needs"], merged["skills"], merged["contacts"],
                  merged["notes"], updated_at or now_iso(), neighbour_id))
    conn.commit()
    return get(conn, neighbour_id) or {}


def remove(conn: sqlite3.Connection, neighbour_id: int) -> None:
    conn.execute("DELETE FROM neighbours WHERE id=?", (neighbour_id,))
    conn.commit()


def label(person: dict) -> str:
    """"Mrs Khan at 12 Elm Road", or just the name when nobody wrote the address down."""
    address = (person.get("address") or "").strip()
    return f"{person.get('name', '')} at {address}" if address else str(person.get("name", ""))


def _cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip() or "—"


def street_list(rows: Iterable[dict], now: str) -> str:
    """The printable street list: one table, then anything anyone wrote in the notes."""
    rows = list(rows)
    count = len(rows)
    lines = ["# Street list", "", f"Printed {now}. "
             + (f"{count} neighbour{'s' if count != 1 else ''}." if count else "Nobody is on the street list yet."), ""]
    if not rows:
        return "\n".join(lines).rstrip() + "\n"
    lines += ["| Name | Address | Needs | Skills | Contacts |", "|---|---|---|---|---|"]
    for person in rows:
        lines.append("| " + " | ".join(_cell(person.get(k, "")) for k in
                                       ("name", "address", "needs", "skills", "contacts")) + " |")
    notes = [p for p in rows if (p.get("notes") or "").strip()]
    if notes:
        lines += ["", "## Notes", ""]
        lines += [f"- **{label(p)}**: {(p.get('notes') or '').strip()}" for p in notes]
    return "\n".join(lines).rstrip() + "\n"
