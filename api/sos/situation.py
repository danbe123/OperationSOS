"""The situation clock: one active scenario per box, started by a tap, with the current phase from elapsed time."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
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


# --- drills (spec section 7) ---------------------------------------------------------------------------------

DRILL_KEY = "drill"
LAST_DRILL_KEY = "last_drill_at"


def _condition_rows(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM conditions")]


def _checklist_rows(conn: sqlite3.Connection, slug: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM checklist_state WHERE playbook=?", (slug,))]


def drill(conn: sqlite3.Connection) -> Optional[dict]:
    """The running drill, with everything it has to put back afterwards, or None."""
    raw = get_setting(conn, DRILL_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def is_drill(conn: sqlite3.Connection) -> bool:
    return drill(conn) is not None


def start_drill(conn: sqlite3.Connection, slug: str, states: dict[str, str], hours_ago: float = 0.0,
                now: Optional[datetime] = None) -> dict:
    """Save the real situation, then set the drill's conditions and start its clock in the past."""
    from sos import conditions as cond

    if is_drill(conn):
        end_drill(conn)
    now = now or datetime.now(timezone.utc)
    started = (now - timedelta(hours=max(0.0, float(hours_ago)))).replace(microsecond=0).isoformat()
    saved = {"scenario": slug, "started_at": started, "conditions": _condition_rows(conn),
             "checklist": _checklist_rows(conn, slug), "previous": brief(conn)}
    set_setting(conn, DRILL_KEY, json.dumps(saved))
    for cid, state in states.items():
        cond.set_state(conn, cid, state, since=started if state != "working" else None, source="drill", set_by="drill",
                       note="Drill")
    start(conn, slug, started_at=started)
    conn.commit()
    return saved


def end_drill(conn: sqlite3.Connection, now: Optional[datetime] = None) -> dict:
    """Put the real conditions, clock and checklist back, and report what the drill got through."""
    running = drill(conn)
    if running is None:
        return {"drill": False}
    now = now or datetime.now(timezone.utc)
    conn.execute("DELETE FROM conditions")
    for row in running.get("conditions") or []:
        conn.execute("INSERT INTO conditions(id, state, since, source, confidence, note, set_by, updated_at, confirmed_at) "
                     "VALUES (:id, :state, :since, :source, :confidence, :note, :set_by, :updated_at, :confirmed_at)", row)
    slug = running.get("scenario")
    if slug:
        conn.execute("DELETE FROM checklist_state WHERE playbook=?", (slug,))
        for row in running.get("checklist") or []:
            conn.execute("INSERT INTO checklist_state(playbook, item_id, checked, updated_at) "
                         "VALUES (:playbook, :item_id, :checked, :updated_at)", row)
    done = conn.execute("SELECT COUNT(*) FROM task_state WHERE drill=1 AND done=1").fetchone()[0]
    conn.execute("DELETE FROM task_state WHERE drill=1")
    previous = running.get("previous")
    if previous:
        start(conn, previous["slug"], started_at=previous["started_at"])
    else:
        clear(conn)
    set_setting(conn, DRILL_KEY, None)
    set_setting(conn, LAST_DRILL_KEY, now.replace(microsecond=0).isoformat())
    conn.commit()
    started = datetime.fromisoformat(running["started_at"])
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return {"drill": True, "scenario": slug, "tasks_done": int(done),
            "elapsed_s": int(max(0.0, (now - started).total_seconds()))}
