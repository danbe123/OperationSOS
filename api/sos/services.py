"""What is working right now: power, water, gas, internet, phones. Set by hand on the box, shared by every
device, and used by the app to swap advice that no longer applies (999 when the phones are down)."""
from __future__ import annotations

import sqlite3

from sos.db import get_setting, set_setting

SERVICES: tuple[str, ...] = ("power", "water", "gas", "internet", "phones")


def state(conn: sqlite3.Connection) -> dict[str, bool]:
    return {s: get_setting(conn, f"service_{s}", "on") != "off" for s in SERVICES}


def set_service(conn: sqlite3.Connection, service: str, on: bool) -> dict[str, bool]:
    if service not in SERVICES:
        raise ValueError(f"unknown service {service}")
    set_setting(conn, f"service_{service}", "on" if on else "off")
    conn.commit()
    return state(conn)
