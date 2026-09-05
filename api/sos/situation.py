"""The situation clock: one active scenario per box, started by a tap, with the current phase from elapsed time."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from sos.db import get_setting, now_iso, set_setting

HOUR = 3600
# (upper bound in seconds, section id); the last entry is open-ended
PHASES: tuple[tuple[Optional[int], str], ...] = (
    (12 * HOUR, "right-now"),
    (72 * HOUR, "first-72-hours"),
    (30 * 24 * HOUR, "first-month"),
    (None, "long-term"),
)


def phase_for(elapsed_s: float) -> str:
    for limit, phase in PHASES:
        if limit is None or elapsed_s < limit:
            return phase
    return PHASES[-1][1]


def start(conn: sqlite3.Connection, slug: str, started_at: Optional[str] = None) -> None:
    set_setting(conn, "situation_slug", slug)
    set_setting(conn, "situation_started_at", started_at or now_iso())
    conn.commit()


def clear(conn: sqlite3.Connection) -> None:
    set_setting(conn, "situation_slug", None)
    set_setting(conn, "situation_started_at", None)
    conn.commit()


def brief(conn: sqlite3.Connection) -> Optional[dict]:
    """The `/status` field: {slug, started_at} or None."""
    slug = get_setting(conn, "situation_slug")
    started = get_setting(conn, "situation_started_at")
    if not slug or not started:
        return None
    return {"slug": slug, "started_at": started}


def snapshot(conn: sqlite3.Connection, title: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    b = brief(conn)
    if b is None:
        return {"slug": None}
    started = datetime.fromisoformat(b["started_at"])
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = max(0.0, ((now or datetime.now(timezone.utc)) - started).total_seconds())
    return {"slug": b["slug"], "title": title, "started_at": b["started_at"], "elapsed_s": int(elapsed),
            "phase": phase_for(elapsed)}
