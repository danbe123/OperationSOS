"""Dependencies shared by the routers: a per-request SQLite connection, the localhost guard and the PIN guard."""
from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import Depends, HTTPException, Request

from sos import db
from sos import system as system_mod
from sos.config import Settings

LOCALHOSTS = {"127.0.0.1", "::1", "localhost"}


def settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_db_durable(request: Request) -> Iterator[sqlite3.Connection]:
    """The connection for routes that write what people entered (ticks, notes, pins, conditions, settings): a
    commit here has reached the disk before the response says it is saved."""
    conn = db.connect(request.app.state.settings.db_path, durable=True)
    try:
        yield conn
    finally:
        conn.close()


def require_localhost(request: Request) -> None:
    host = request.client.host if request.client else None
    if host not in LOCALHOSTS:
        raise HTTPException(status_code=403, detail="Only allowed from the box itself")


def require_pin(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> None:
    if not system_mod.pin_required(conn):
        return
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else None
    if not request.app.state.tokens.valid(token):
        raise HTTPException(status_code=401, detail="PIN required")
