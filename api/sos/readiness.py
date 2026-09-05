"""The readiness score (spec section 7), kept in the settings table so `/status` is a cheap read.

It is recomputed whenever anything it counts changes — a stock item, a person in the household, the home on the
map, the end of a drill — and once a night for the parts that only time moves (the six-month practice window and
the days left in the stock cupboard)."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from sos import engine
from sos.config import Settings
from sos.db import get_setting, now_iso, set_setting

log = logging.getLogger(__name__)
KEY = "readiness_score"
AT_KEY = "readiness_at"
NIGHTLY_CHECK_S = 900.0        # look every quarter of an hour; recompute once a day, in the small hours
NIGHTLY_HOUR = 3


def store(content, settings: Settings, conn: sqlite3.Connection) -> int:
    """Recompute the score from the current model and write it to `settings.readiness_score`."""
    from sos.routers.situation import build_model_for, ruleset_for   # deferred: the router imports this module

    view = engine.compute(build_model_for(content, settings, conn), ruleset_for(settings))
    score = int(view["readiness"]["score"])
    set_setting(conn, KEY, str(score))
    set_setting(conn, AT_KEY, now_iso())
    return score


def stored(conn: sqlite3.Connection) -> Optional[int]:
    raw = get_setting(conn, KEY)
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def refresh(request, conn: sqlite3.Connection) -> Optional[int]:
    """The hook the routers call after a change. Never lets a scoring problem fail the write that caused it."""
    try:
        return store(request.app.state.content, request.app.state.settings, conn)
    except Exception:
        log.exception("readiness recompute failed")
        return None


def _due(conn: sqlite3.Connection, now: datetime) -> bool:
    """Once past the nightly hour, if today's recompute has not happened yet."""
    if now.hour < NIGHTLY_HOUR:
        return False
    last = get_setting(conn, AT_KEY)
    return not (last or "").startswith(now.date().isoformat())


async def nightly(settings: Settings, content, db_path) -> None:
    from sos.db import connect

    conn = connect(db_path)
    try:
        while True:
            try:
                if _due(conn, datetime.now(timezone.utc)):
                    await asyncio.to_thread(store, content, settings, conn)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("nightly readiness recompute failed")
            await asyncio.sleep(NIGHTLY_CHECK_S)
    finally:
        conn.close()
