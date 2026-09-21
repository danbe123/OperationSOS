"""Every route that writes to the database says which kind of connection it uses, and the user-state ones are
durable (`synchronous=FULL`, see tests/test_crash_safety.py for why). Adding a write route means choosing: the
table below fails until it is either on `get_db_durable` or given a reason here."""
from __future__ import annotations

import asyncio
import importlib
import pkgutil
import time

import pytest
from fastapi.routing import APIRoute

import sos.routers as routers_pkg
from sos import db

READ_ONLY = {"GET", "HEAD", "OPTIONS"}

# Routes that touch the database on the ordinary (NORMAL) connection ON PURPOSE. Each is a bulk or derived write:
# what it stores can be made again from the manifest, the files on the disk or the network, so losing the last
# few seconds of it in a power cut costs nothing, and FULL would slow it down.
NORMAL_ON_PURPOSE = {
    ("system", "/system/rescan"): "rebuilds library availability, library.xml and the fts flags from the disk, and flushes the search cache",
    ("system", "/system/update"): "starts a download job; what it records (library availability) is re-derived from the disk",
}

# Routes that write nothing to the database at all (in-memory state, a device, a file, a stream). They must
# not gain a get_db* dependency without moving to the table above or to the durable path.
NO_DATABASE = {
    ("ai", "/ai/ask"): "streams an answer; nothing is stored",
    ("kiosk", "/kiosk/backlight"): "sets the panel backlight; in memory and on the device only",
    ("kiosk", "/kiosk/idle"): "in-memory idle flag and the backlight",
    ("sensors", "/speak"): "returns audio",
    ("system", "/system/backlight"): "sets the panel backlight; in memory and on the device only",
    ("kiosk", "/kiosk/alive"): "records the time of the last heartbeat from the kiosk page, in memory only",
}


# Routes whose only per-request connection is the PIN check's read; what they store goes through the shared
# `app.state.conn`, which is durable (asserted below).
VIA_SHARED_CONNECTION = {
    ("ai", "/ai/enable"): "stores ai_state, ai_message and ai_enabled through app.state.conn",
    ("ai", "/ai/disable"): "stores ai_state, ai_message and ai_enabled through app.state.conn",
}


def dependency_names(dependant) -> list[str]:
    names: list[str] = []
    for sub in dependant.dependencies:
        names.append(getattr(sub.call, "__name__", str(sub.call)))
        names.extend(dependency_names(sub))
    return names


def write_routes() -> list[tuple[str, str, str, list[str]]]:
    found = []
    for info in pkgutil.iter_modules(routers_pkg.__path__):
        router = getattr(importlib.import_module(f"sos.routers.{info.name}"), "router", None)
        if router is None:
            continue
        for route in router.routes:
            if isinstance(route, APIRoute) and set(route.methods) - READ_ONLY:
                found.append((info.name, route.path, ",".join(sorted(set(route.methods) - READ_ONLY)), dependency_names(route.dependant)))
    return found


ROUTES = write_routes()


def test_the_walk_finds_the_routes():
    assert len(ROUTES) >= 30, "the router walk found too few routes; has the router layout changed?"


@pytest.mark.parametrize(("module", "path", "methods", "deps"), ROUTES, ids=[f"{m} {ms} {p}" for m, p, ms, _ in ROUTES])
def test_every_write_route_is_durable_or_has_a_stated_reason(module, path, methods, deps):
    dbs = {d for d in deps if d.startswith("get_db")}
    key = (module, path)
    if "get_db_durable" in dbs:
        assert key not in NORMAL_ON_PURPOSE and key not in NO_DATABASE, f"{key} is durable now: drop it from the allow-lists"
        return
    if key in VIA_SHARED_CONNECTION:
        return
    if not dbs:
        assert key in NO_DATABASE, f"{methods} {path} has no database dependency and is not listed in NO_DATABASE: does it write?"
        return
    assert key in NORMAL_ON_PURPOSE, (
        f"{methods} {path} writes on the NORMAL connection: a power cut can lose what it stored. Use get_db_durable, "
        "or add it to NORMAL_ON_PURPOSE with the reason it is safe to lose.")


def test_the_allow_lists_name_routes_that_exist():
    real = {(m, p) for m, p, _, _ in ROUTES}
    for key, reason in {**NORMAL_ON_PURPOSE, **NO_DATABASE, **VIA_SHARED_CONNECTION}.items():
        assert reason.strip(), key
        assert key in real, f"{key} is in an allow-list but is not a write route any more"


# --- the connections that are not per-request ---------------------------------------------------------------

def test_the_shared_app_connection_is_durable(client):
    """It carries the assistant's on/off state and message (ai_state, ai_message, ai_enabled)."""
    assert client.app.state.conn.execute("PRAGMA synchronous").fetchone()[0] == 2


def test_the_thermal_watchdog_writes_on_a_durable_connection(env, monkeypatch):
    from sos import system

    opened: list[bool] = []
    real = system.connect

    def spy(path, *, durable=False):
        opened.append(durable)
        return real(path, durable=durable)

    class Stop(Exception):
        pass

    async def stop(_):
        raise Stop

    monkeypatch.setattr(system, "connect", spy)
    monkeypatch.setattr(system.asyncio, "sleep", stop)
    with pytest.raises(Stop):
        asyncio.run(system.ThermalWatchdog(env, env.db_path).run())
    assert opened == [True]


# --- the bulk paths stay on NORMAL, and stay fast ---------------------------------------------------------------

def test_search_cache_and_the_index_rebuild_stay_on_the_normal_connection(client, env, monkeypatch):
    from sos import sync

    opened: list[bool] = []
    real = db.connect

    def spy(path, *, durable=False):
        opened.append(durable)
        return real(path, durable=durable)

    monkeypatch.setattr(db, "connect", spy)
    assert client.get("/api/search", params={"q": "water"}).status_code == 200
    assert set(opened) == {False}, "a search (which writes the cache) must not pay for FULL"
    opened.clear()
    sync.index(env, out=lambda *_: None)
    assert opened and set(opened) == {False}, "the index rebuild must not pay for FULL"


def test_a_bulk_write_is_as_fast_on_the_bulk_connection_as_before(tmp_path):
    """One transaction of 20,000 cache rows: the cost of FULL is one fsync per commit, so a bulk write in one
    transaction is the same on both, and the per-row commits that would hurt are exactly what the bulk paths do
    not have. Measured here so a change to db.connect that slows the default connection fails."""
    def bulk(conn) -> float:
        began = time.perf_counter()
        conn.execute("BEGIN")
        for i in range(20_000):
            conn.execute("INSERT INTO search_cache(q, results_json, created_at) VALUES (?, ?, ?)", (str(i), "x" * 200, "x"))
        conn.commit()
        return time.perf_counter() - began

    normal = db.connect(tmp_path / "n.db")
    db.init_schema(normal)
    assert normal.execute("PRAGMA synchronous").fetchone()[0] == 1
    assert bulk(normal) < 2.0
