"""Export and import of the whole situation (spec section 8): hand one box's picture to another.

The export is one JSON document with a version and a checksum. Two boxes on the same street have no network
between them, so the same document is also offered as a sequence of short strings, each small enough to be a QR
code on a phone screen: gzip, base64, then cut into pieces of at most 800 characters. Importing merges rather
than overwrites, because both boxes have been watching different halves of the same emergency: a condition is
taken from whichever box saw it more recently, people and stock match by name, and events simply join the log."""
from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from sos import conditions as cond
from sos import neighbours as nb
from sos import situation
from sos.db import get_setting, now_iso, set_setting

VERSION = 1
KIND = "sos-situation-export"
EVENT_LIMIT = 50               # the last fifty entries: enough to hand over, small enough to scan
MAX_CHUNK = 800                # characters in one QR chunk, including the {"i","n","d"} wrapper
CHUNK_PAYLOAD = 740
PARTS = ("conditions", "scenario", "tasks", "checklist", "household", "stock", "neighbours", "home", "events")
_PERSON_FIELDS = ("name", "age", "needs", "medications", "contacts", "updated_at")
_STOCK_FIELDS = ("name", "category", "quantity", "unit", "per_person_day", "expires", "notes", "updated_at")
_NEIGHBOUR_FIELDS = ("name", "address", "needs", "skills", "contacts", "notes", "updated_at")
_TASK_FIELDS = ("task_id", "done", "done_at", "person", "updated_at", "drill")


class TransferError(ValueError):
    """An export that cannot be read: the wrong version, a broken checksum or a missing QR chunk."""


def canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checksum(data: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(data).encode("utf-8")).hexdigest()


# --- export ---------------------------------------------------------------------------------------------

def _rows(conn: sqlite3.Connection, sql: str, fields: tuple[str, ...], params: tuple = ()) -> list[dict]:
    return [{k: r[k] for k in fields} for r in conn.execute(sql, params)]


def data_for(conn: sqlite3.Connection) -> dict:
    """The whole situation as plain data, in a fixed order so the checksum is stable."""
    scenario = situation.brief(conn) or {}
    home_lat, home_lon = get_setting(conn, "home_lat"), get_setting(conn, "home_lon")
    events = list(reversed(_rows(conn, "SELECT title, body, updated_at FROM notes WHERE kind='event' "
                                       "ORDER BY updated_at DESC, id DESC LIMIT ?",
                                 ("title", "body", "updated_at"), (EVENT_LIMIT,))))
    return {
        "conditions": {cid: c.as_dict() for cid, c in cond.load(conn).items()},
        "scenario": {"slug": scenario.get("slug"), "started_at": scenario.get("started_at"),
                     "drill": situation.is_drill(conn)},
        "tasks": _rows(conn, "SELECT * FROM task_state ORDER BY task_id", _TASK_FIELDS),
        "checklist": _rows(conn, "SELECT * FROM checklist_state ORDER BY playbook, item_id",
                           ("playbook", "item_id", "checked", "updated_at")),
        "household": _rows(conn, "SELECT * FROM household ORDER BY id", _PERSON_FIELDS),
        "stock": _rows(conn, "SELECT * FROM stock ORDER BY id", _STOCK_FIELDS),
        "neighbours": _rows(conn, "SELECT * FROM neighbours ORDER BY id", _NEIGHBOUR_FIELDS),
        "home": {"lat": float(home_lat) if home_lat else None, "lon": float(home_lon) if home_lon else None,
                 "label": get_setting(conn, "home_label", "Home"), "flood_zone": get_setting(conn, "home_flood_zone")},
        "events": events,
    }


def export(conn: sqlite3.Connection, now: Optional[str] = None) -> dict:
    data = data_for(conn)
    return {"kind": KIND, "version": VERSION, "exported_at": now or now_iso(), "checksum": checksum(data),
            "data": data}


# --- the QR sequence ------------------------------------------------------------------------------------

def chunks(payload: dict) -> list[str]:
    """The export gzipped, base64'd and cut into QR-sized pieces, each one a `{"i","n","d"}` document."""
    raw = base64.b64encode(gzip.compress(canonical(payload).encode("utf-8"), mtime=0)).decode("ascii")
    total = max(1, -(-len(raw) // CHUNK_PAYLOAD))
    size = -(-len(raw) // total)
    pieces = [raw[i:i + size] for i in range(0, len(raw), size)] or [""]
    out = [json.dumps({"i": i, "n": len(pieces), "d": piece}, separators=(",", ":")) for i, piece in enumerate(pieces)]
    over = [c for c in out if len(c) > MAX_CHUNK]
    if over:                                    # a wrapper longer than the allowance means the maths above is wrong
        raise TransferError(f"chunk of {len(over[0])} characters is longer than the {MAX_CHUNK} allowed")
    return out


def join(items: list) -> dict:
    """The chunks a phone scanned, in any order, back into the export they came from."""
    parsed: dict[int, str] = {}
    total: Optional[int] = None
    for item in items:
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                raise TransferError("a scanned chunk is not a QR chunk: expected {\"i\", \"n\", \"d\"}") from None
        if not isinstance(item, dict) or not {"i", "n", "d"} <= set(item):
            raise TransferError("a scanned chunk is not a QR chunk: expected {\"i\", \"n\", \"d\"}")
        index, count = int(item["i"]), int(item["n"])
        if total is None:
            total = count
        elif total != count:
            raise TransferError(f"the chunks are from two different exports ({total} and {count} parts)")
        parsed[index] = str(item["d"])
    if total is None:
        raise TransferError("no chunks were given")
    missing = [i for i in range(total) if i not in parsed]
    if missing:
        plural = "s" if len(missing) > 1 else ""
        raise TransferError(f"chunk{plural} {', '.join(str(i + 1) for i in missing)} of {total} missing: scan the rest")
    raw = "".join(parsed[i] for i in range(total))
    try:
        text = gzip.decompress(base64.b64decode(raw, validate=True)).decode("utf-8")
        payload = json.loads(text)
    except (binascii.Error, OSError, UnicodeDecodeError, ValueError):
        raise TransferError("the scanned chunks do not decode: scan them all again") from None
    if not isinstance(payload, dict):
        raise TransferError("the scanned chunks are not a situation export")
    return payload


def decode(body: Any) -> dict:
    """Either the export itself or the QR chunks it was shown as."""
    payload = join(body) if isinstance(body, list) else body
    if not isinstance(payload, dict) or payload.get("kind") != KIND:
        raise TransferError("that is not a situation export")
    if int(payload.get("version") or 0) != VERSION:
        raise TransferError(f"this box reads version {VERSION} exports, not version {payload.get('version')}")
    data = payload.get("data")
    if not isinstance(data, dict) or not set(PARTS) <= set(data):
        raise TransferError("the export is incomplete: " + ", ".join(sorted(set(PARTS) - set(data or {}))))
    if payload.get("checksum") != checksum(data):
        raise TransferError("the checksum does not match: the export was changed or arrived incomplete")
    return payload


# --- the merge ------------------------------------------------------------------------------------------

def _when(value) -> datetime:
    return cond.parse_iso(value) or datetime.min.replace(tzinfo=timezone.utc)


def _newer(incoming, mine) -> bool:
    return _when(incoming) > _when(mine)


def _key(name) -> str:
    return str(name or "").strip().lower()


def _merge_conditions(conn: sqlite3.Connection, rows: dict, changes: list[str]) -> dict:
    counts = {"updated": 0, "kept": 0}
    mine = cond.load(conn)
    for cid, row in sorted(rows.items()):
        if cid not in cond.IDS or not isinstance(row, dict):
            continue
        current = mine.get(cid)
        if current is not None and not _newer(row.get("updated_at"), current.updated_at):
            counts["kept"] += 1
            continue
        conn.execute("INSERT INTO conditions(id, state, since, source, confidence, note, set_by, updated_at, confirmed_at) "
                     "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state, since=excluded.since, "
                     "source=excluded.source, confidence=excluded.confidence, note=excluded.note, set_by=excluded.set_by, "
                     "updated_at=excluded.updated_at, confirmed_at=excluded.confirmed_at",
                     (cid, row.get("state", "working"), row.get("since"), row.get("source", "manual"),
                      float(row.get("confidence") or 1.0), row.get("note") or "", row.get("set_by") or "",
                      row.get("updated_at"), row.get("confirmed_at")))
        counts["updated"] += 1
        changes.append(f"{cond.TITLES[cid]} {row.get('state')} from the other box")
    conn.commit()
    return counts


def _merge_people(conn: sqlite3.Connection, table: str, fields: tuple[str, ...], rows: list, label: str,
                  changes: list[str]) -> dict:
    counts = {"added": 0, "updated": 0, "kept": 0}
    mine = {_key(r["name"]): r for r in conn.execute(f"SELECT * FROM {table}")}
    columns = [f for f in fields if f != "updated_at"]
    for row in rows or []:
        if not isinstance(row, dict) or not _key(row.get("name")):
            continue
        current = mine.get(_key(row.get("name")))
        values = [row.get(f) for f in columns]
        if current is None:
            conn.execute(f"INSERT INTO {table}({', '.join(columns)}, updated_at) "
                         f"VALUES ({', '.join('?' * len(columns))}, ?)", (*values, row.get("updated_at") or now_iso()))
            counts["added"] += 1
            changes.append(f"{label} added: {row.get('name')}")
        elif _newer(row.get("updated_at"), current["updated_at"]):
            conn.execute(f"UPDATE {table} SET {', '.join(f'{c}=?' for c in columns)}, updated_at=? WHERE id=?",
                         (*values, row.get("updated_at"), current["id"]))
            counts["updated"] += 1
            changes.append(f"{label} updated: {row.get('name')}")
        else:
            counts["kept"] += 1
    conn.commit()
    return counts


def _merge_tasks(conn: sqlite3.Connection, rows: list) -> dict:
    counts = {"updated": 0, "kept": 0}
    mine = {r["task_id"]: r["updated_at"] for r in conn.execute("SELECT task_id, updated_at FROM task_state")}
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("task_id"):
            continue
        if row["task_id"] in mine and not _newer(row.get("updated_at"), mine[row["task_id"]]):
            counts["kept"] += 1
            continue
        conn.execute("INSERT INTO task_state(task_id, done, done_at, person, updated_at, drill) VALUES (?,?,?,?,?,?) "
                     "ON CONFLICT(task_id) DO UPDATE SET done=excluded.done, done_at=excluded.done_at, "
                     "person=excluded.person, updated_at=excluded.updated_at, drill=excluded.drill",
                     (row["task_id"], int(bool(row.get("done"))), row.get("done_at"), row.get("person"),
                      row.get("updated_at") or now_iso(), int(bool(row.get("drill")))))
        counts["updated"] += 1
    conn.commit()
    return counts


def _merge_checklist(conn: sqlite3.Connection, rows: list) -> dict:
    counts = {"updated": 0, "kept": 0}
    mine = {(r["playbook"], r["item_id"]): r["updated_at"]
            for r in conn.execute("SELECT playbook, item_id, updated_at FROM checklist_state")}
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("playbook") or not row.get("item_id"):
            continue
        key = (row["playbook"], row["item_id"])
        if key in mine and not _newer(row.get("updated_at"), mine[key]):
            counts["kept"] += 1
            continue
        conn.execute("INSERT INTO checklist_state(playbook, item_id, checked, updated_at) VALUES (?,?,?,?) "
                     "ON CONFLICT(playbook, item_id) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at",
                     (row["playbook"], row["item_id"], int(bool(row.get("checked"))), row.get("updated_at") or now_iso()))
        counts["updated"] += 1
    conn.commit()
    return counts


def _merge_events(conn: sqlite3.Connection, rows: list) -> dict:
    counts = {"added": 0, "skipped": 0}
    mine = {(r["updated_at"], r["title"]) for r in conn.execute("SELECT updated_at, title FROM notes WHERE kind='event'")}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        key = (row.get("updated_at"), row.get("title"))
        if key in mine:
            counts["skipped"] += 1
            continue
        mine.add(key)
        conn.execute("INSERT INTO notes(kind, title, body, updated_at) VALUES ('event', ?, ?, ?)",
                     (row.get("title") or "", row.get("body") or "", row.get("updated_at") or now_iso()))
        counts["added"] += 1
    conn.commit()
    return counts


def merge(conn: sqlite3.Connection, body: Any) -> dict:
    """Take everything the other box knew more recently than this one, and report what moved."""
    payload = decode(body)
    data = payload["data"]
    changes: list[str] = []
    counts = {
        "conditions": _merge_conditions(conn, data.get("conditions") or {}, changes),
        "household": _merge_people(conn, "household", _PERSON_FIELDS, data.get("household"), "Person", changes),
        "stock": _merge_people(conn, "stock", _STOCK_FIELDS, data.get("stock"), "Stock", changes),
        "neighbours": _merge_people(conn, "neighbours", _NEIGHBOUR_FIELDS, data.get("neighbours"), "Neighbour", changes),
        "tasks": _merge_tasks(conn, data.get("tasks")),
        "checklist": _merge_checklist(conn, data.get("checklist")),
        "events": _merge_events(conn, data.get("events")),
    }

    home = data.get("home") or {}
    home_state = "kept"
    if get_setting(conn, "home_lat") is None and home.get("lat") is not None and home.get("lon") is not None:
        set_setting(conn, "home_lat", f"{float(home['lat']):.6f}")
        set_setting(conn, "home_lon", f"{float(home['lon']):.6f}")
        set_setting(conn, "home_label", home.get("label") or "Home")
        set_setting(conn, "home_flood_zone", home.get("flood_zone"))
        home_state = "set"
        changes.append(f"Home set to {home.get('label') or 'Home'} from the other box")

    scenario = data.get("scenario") or {}
    scenario_state = "kept"
    if scenario.get("slug") and not situation.brief(conn):
        situation.start(conn, scenario["slug"], started_at=scenario.get("started_at"))
        scenario_state = f"started: {scenario['slug']}"
        changes.append(f"Situation started from the other box: {scenario['slug']}")
    return {"ok": True, "version": payload["version"], "exported_at": payload.get("exported_at"),
            "counts": counts, "home": home_state, "scenario": scenario_state, "changes": changes}


def summary_line(summary: dict) -> str:
    """One line for the event log: what an import actually moved."""
    counts = summary["counts"]
    parts = [f"{counts['conditions']['updated']} condition(s)",
             f"{counts['household']['added'] + counts['household']['updated']} person/people",
             f"{counts['neighbours']['added'] + counts['neighbours']['updated']} neighbour(s)",
             f"{counts['events']['added']} event(s)"]
    return ", ".join(parts)
