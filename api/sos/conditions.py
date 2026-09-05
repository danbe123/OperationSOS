"""The situation model's conditions: ten services with three states, a since time, a source and an audit trail."""
from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sos.db import now_iso

CONDITIONS: tuple[tuple[str, str], ...] = (
    ("power", "Mains power"), ("water", "Water supply"), ("mobile", "Mobile network"), ("landline", "Landline and 999"),
    ("internet", "Internet"), ("gas", "Gas"), ("heating", "Heating"), ("roads", "Roads and transport"),
    ("shops", "Shops and cash"), ("sewage", "Sewage and drains"),
)
IDS = tuple(c for c, _ in CONDITIONS)
TITLES = dict(CONDITIONS)
HOME_IDS = ("power", "water", "mobile", "landline", "internet")
STATES = ("working", "degraded", "off")
SOURCES = ("manual", "detected", "inferred", "drill")
STALE_AFTER = timedelta(hours=24)


@dataclass
class Condition:
    id: str
    state: str = "working"
    since: Optional[str] = None
    source: str = "manual"
    confidence: float = 1.0
    note: str = ""
    set_by: str = ""
    updated_at: Optional[str] = None
    confirmed_at: Optional[str] = None

    @property
    def title(self) -> str:
        return TITLES[self.id]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["title"] = self.title
        return d


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def load(conn: sqlite3.Connection) -> dict[str, Condition]:
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM conditions")}
    out: dict[str, Condition] = {}
    for cid in IDS:
        r = rows.get(cid)
        out[cid] = Condition(cid, r["state"], r["since"], r["source"], float(r["confidence"] or 1.0), r["note"] or "",
                             r["set_by"] or "", r["updated_at"], r["confirmed_at"]) if r else Condition(cid)
    return out


def set_state(conn: sqlite3.Connection, cid: str, state: str, *, since: Optional[str] = None, note: str = "",
              source: str = "manual", confidence: float = 1.0, set_by: str = "", expected_updated_at: Optional[str] = None) -> Condition:
    if cid not in IDS:
        raise KeyError(cid)
    if state not in STATES:
        raise ValueError(f"state must be one of {STATES}")
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    current = conn.execute("SELECT updated_at, state FROM conditions WHERE id=?", (cid,)).fetchone()
    if expected_updated_at is not None and current is not None and current["updated_at"] != expected_updated_at:
        raise ConflictError(load(conn)[cid])
    now = now_iso()
    since = since or (None if state == "working" else now)
    if state == "working":
        since = None
    conn.execute(
        "INSERT INTO conditions(id, state, since, source, confidence, note, set_by, updated_at, confirmed_at) "
        "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state, since=excluded.since, "
        "source=excluded.source, confidence=excluded.confidence, note=excluded.note, set_by=excluded.set_by, "
        "updated_at=excluded.updated_at, confirmed_at=excluded.confirmed_at",
        (cid, state, since, source, confidence, note, set_by, now, now))
    conn.commit()
    return load(conn)[cid]


def confirm(conn: sqlite3.Connection, cid: str) -> Condition:
    if cid not in IDS:
        raise KeyError(cid)
    conn.execute("UPDATE conditions SET confirmed_at=? WHERE id=?", (now_iso(), cid))
    conn.commit()
    return load(conn)[cid]


def is_stale(c: Condition, now: datetime) -> bool:
    if c.state == "working":
        return False
    last = parse_iso(c.confirmed_at) or parse_iso(c.updated_at)
    return last is not None and now - last > STALE_AFTER


def duration_s(c: Condition, now: datetime) -> int:
    since = parse_iso(c.since)
    return 0 if since is None or c.state == "working" else max(0, int((now - since).total_seconds()))


class ConflictError(Exception):
    def __init__(self, current: Condition):
        super().__init__("condition changed since it was read")
        self.current = current
