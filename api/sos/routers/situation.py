"""The situation: the clock, the conditions, the tasks, the home, drills and the View every screen reads."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from sos import conditions as cond
from sos import engine, nearby, neighbours as nb, readiness, rules as rules_mod, sensors, situation, transfer
from sos.db import get_setting, now_iso, set_setting
from sos.routers import LOCALHOSTS, get_db

router = APIRouter(tags=["situation"])

HOME_KEYS = ("home_lat", "home_lon", "home_label", "home_flood_zone")


class StartBody(BaseModel):
    slug: str


class ConditionBody(BaseModel):
    state: Literal["working", "degraded", "off"]
    since: Optional[str] = None
    note: Optional[str] = None
    expected_updated_at: Optional[str] = None


class AcceptBody(BaseModel):
    rule: str


class TaskBody(BaseModel):
    done: Optional[bool] = None
    person: Optional[str] = None


class HomeBody(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    label: Optional[str] = None
    flood_zone: Optional[str] = None


class DrillBody(BaseModel):
    scenario: str
    conditions: dict[str, Literal["working", "degraded", "off"]] = Field(default_factory=dict)
    hours_ago: float = 0.0


# --- building the model -------------------------------------------------------------------------------------

def _title(content, kind: str, slug: str) -> Optional[str]:
    doc = content.document(kind, slug)
    return doc.title if doc is not None else None


def _home(conn: sqlite3.Connection) -> dict:
    lat, lon = get_setting(conn, "home_lat"), get_setting(conn, "home_lon")
    return {"lat": float(lat) if lat else None, "lon": float(lon) if lon else None,
            "label": get_setting(conn, "home_label", "Home"), "flood_zone": get_setting(conn, "home_flood_zone")}


def _stock(conn: sqlite3.Connection, content) -> tuple[dict, ...]:
    """The same rows and the same days_left as `GET /stock`, so the engine never disagrees with the API."""
    from sos.routers.household import _item, people_count

    people = people_count(conn)
    return tuple(_item(r, people, content) for r in conn.execute("SELECT * FROM stock ORDER BY category, id"))


def _titles(content, ruleset: rules_mod.Rules, scenario: Optional[str]) -> dict[str, str]:
    """Titles for everything the reading rules can open, so the briefing reads like a list of pages."""
    kinds = {"playbook": "scenario", "module": "module", "page": "page", "card": "card"}
    links = [link for rule in ruleset.readings for link in rule.open]
    if scenario:
        links.append(f"playbook:{scenario}")
    out: dict[str, str] = {}
    for link in links:
        scheme, _, rest = link.partition(":")
        slug = rest.partition("#")[0]
        if scheme in kinds and link not in out:
            title = _title(content, kinds[scheme], slug)
            if title:
                out[f"{scheme}:{slug}"] = title
    return out


def _ruleset(request: Request) -> rules_mod.Rules:
    return ruleset_for(request.app.state.settings)


def ruleset_for(settings) -> rules_mod.Rules:
    return rules_mod.load(settings.playbooks / "rules")


def build_model_for(content, settings, conn: sqlite3.Connection, now: Optional[datetime] = None) -> engine.Model:
    """Everything in the database that the engine is allowed to see, as one immutable snapshot.

    Takes the content cache and the settings rather than the request, so the background tasks (the nightly
    readiness recompute) can build the same model as a screen does."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    ruleset = ruleset_for(settings)
    slug = get_setting(conn, "situation_slug")
    scenario = situation.snapshot(conn, _title(content, "scenario", slug) if slug else None, now) if slug else None
    if scenario is not None and not scenario.get("slug"):
        scenario = None
    states = {cid: c.state for cid, c in cond.load(conn).items()}
    home = _home(conn)
    lat, lon = (home["lat"], home["lon"]) if home["lat"] is not None else engine.FALLBACK_LATLON
    from sos import sun

    flags = engine.flags_for(states, slug, sun.is_dark(lat, lon, now))
    checklist: tuple[dict, ...] = ()
    checklist_state: dict[str, bool] = {}
    if slug:
        rendered = content.rendered("scenario", slug, flags)
        if rendered is not None:
            checklist = tuple({"id": item["id"], "text": item["text"]} for item in rendered.checklist)
            checklist_state = {r["item_id"]: bool(r["checked"]) for r in conn.execute(
                "SELECT item_id, checked FROM checklist_state WHERE playbook=?", (slug,))}
    task_state = {r["task_id"]: {"done": bool(r["done"]), "done_at": r["done_at"], "person": r["person"]}
                  for r in conn.execute("SELECT * FROM task_state")}
    household = tuple({"name": r["name"], "age": r["age"], "needs": r["needs"] or "",
                       "medications": r["medications"] or "", "contacts": r["contacts"] or ""}
                      for r in conn.execute("SELECT * FROM household ORDER BY id"))
    meeting = conn.execute("SELECT 1 FROM notes WHERE kind IN ('note','pin') AND "
                           "(lower(title) LIKE '%meeting point%' OR lower(body) LIKE '%meeting point%') LIMIT 1").fetchone()
    from sos import kits as kits_mod

    # Every kit's ticks in one read, not one query per kit: fifteen kits is fifteen round trips on a screen refresh.
    ticked: dict[str, set[str]] = {}
    for row in conn.execute("SELECT playbook, item_id FROM checklist_state WHERE checked=1 AND playbook LIKE 'kit:%'"):
        ticked.setdefault(row["playbook"][len("kit:"):], set()).add(row["item_id"])
    kit_rows: list[dict] = []
    for kit in content.kits():
        done, total = kits_mod.basic_progress(kit, ticked.get(kit.id, set()))
        kit_rows.append({"slug": kit.id, "title": kit.title, "relevant": kits_mod.relevant(kit, household),
                         "basic_done": done, "basic_total": total})
    return engine.Model(
        now=now, conditions=cond.load(conn), scenario=scenario, household=household, neighbours=tuple(nb.listing(conn)),
        stock=_stock(conn, content), home=home,
        drill=situation.is_drill(conn), checklist=checklist, checklist_state=checklist_state, task_state=task_state,
        titles=_titles(content, ruleset, slug), meeting_point=meeting is not None,
        last_drill_at=situation.last_drill_at(conn), tz=get_setting(conn, "timezone", "Europe/London"),
        detected=sensors.detected_states(conn, now),
        kits=tuple(kit_rows),
    )


def build_model(request: Request, conn: sqlite3.Connection, now: Optional[datetime] = None) -> engine.Model:
    return build_model_for(request.app.state.content, request.app.state.settings, conn, now)


def view_for(request: Request, conn: sqlite3.Connection) -> dict:
    settings = request.app.state.settings
    view = engine.compute(build_model(request, conn), _ruleset(request))
    return with_nearby(settings, conn, view)


def with_nearby(settings, conn: sqlite3.Connection, view: dict) -> dict:
    """The home's nearest facilities, in `meta.home.nearby`, cached per home so the overlays are read once."""
    home = view["meta"]["home"]
    if home.get("lat") is None or home.get("lon") is None:
        return view
    home["nearby"] = _nearby_cached(settings, round(float(home["lat"]), 5), round(float(home["lon"]), 5), conn)
    return view


_NEARBY_CACHE: dict[tuple, list[dict]] = {}


def _nearby_cached(settings, lat: float, lon: float, conn: sqlite3.Connection) -> list[dict]:
    key = (str(settings.core), lat, lon)
    if key not in _NEARBY_CACHE:
        if len(_NEARBY_CACHE) > 8:                 # one home, a handful of drills; never a cache to manage
            _NEARBY_CACHE.clear()
        _NEARBY_CACHE[key] = nearby.summary(nearby.nearest(settings, lat, lon, conn))
    return _NEARBY_CACHE[key]


def current_flags(request: Request, conn: sqlite3.Connection) -> dict[str, bool]:
    """The flag set the content directives are resolved against on every content screen."""
    return engine.flags(view_for(request, conn))


# --- the audit log ------------------------------------------------------------------------------------------

def actor(request: Request, conn: sqlite3.Connection) -> str:
    if situation.is_drill(conn):
        return "drill"
    host = request.client.host if request.client else None
    return "kiosk" if host in LOCALHOSTS else "phone"


def event(conn: sqlite3.Connection, title: str, body: str = "") -> None:
    conn.execute("INSERT INTO notes(kind, title, body, updated_at) VALUES ('event', ?, ?, ?)", (title, body, now_iso()))
    conn.commit()


def _clock(value: Optional[str]) -> str:
    parsed = cond.parse_iso(value)
    return parsed.strftime("%H:%M") if parsed else "now"


# --- the clock ------------------------------------------------------------------------------------------------

@router.get("/situation")
def get_situation(request: Request, conn=Depends(get_db)):
    snap = situation.snapshot(conn)
    if snap["slug"]:
        snap["title"] = _title(request.app.state.content, "scenario", snap["slug"]) or snap["slug"]
    return snap


@router.post("/situation")
def start_situation(body: StartBody, request: Request, conn=Depends(get_db)):
    if request.app.state.content.document("scenario", body.slug) is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    situation.start(conn, body.slug)
    event(conn, f"Situation started: {_title(request.app.state.content, 'scenario', body.slug)} ({actor(request, conn)})")
    return get_situation(request, conn)


@router.delete("/situation")
def end_situation(request: Request, conn=Depends(get_db)):
    snap = situation.snapshot(conn)
    if snap["slug"]:
        event(conn, f"Situation ended: {_title(request.app.state.content, 'scenario', snap['slug'])} ({actor(request, conn)})")
    situation.clear(conn)
    return {"slug": None}


# --- the View ---------------------------------------------------------------------------------------------

@router.get("/situation/view")
def get_view(request: Request, conn=Depends(get_db)):
    return view_for(request, conn)


@router.get("/situation/report", response_class=PlainTextResponse)
def get_report(request: Request, conn=Depends(get_db)):
    view = view_for(request, conn)
    since = (view.get("scenario") or {}).get("started_at")
    if since:
        rows = conn.execute("SELECT * FROM notes WHERE kind='event' AND updated_at >= ? ORDER BY updated_at, id", (since,))
    else:
        rows = conn.execute("SELECT * FROM notes WHERE kind='event' ORDER BY updated_at DESC, id DESC LIMIT 50")
    events = [{"updated_at": r["updated_at"], "title": r["title"]} for r in rows]
    return PlainTextResponse(engine.report(view, events), media_type="text/markdown; charset=utf-8")


# --- export and import (spec section 8) -------------------------------------------------------------------------

@router.get("/situation/export")
def get_export(conn=Depends(get_db)):
    """The whole situation as one JSON document, with a version and a checksum."""
    return transfer.export(conn)


@router.get("/situation/export/qr")
def get_export_qr(conn=Depends(get_db)):
    """The same document as a sequence of QR-sized chunks, to be shown one after another on a phone."""
    return {"chunks": transfer.chunks(transfer.export(conn))}


@router.post("/situation/import")
async def post_import(request: Request, conn=Depends(get_db)):
    """Merge another box's export: the newer of each condition, people and stock by name, events appended."""
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(status_code=422, detail="The import is not JSON") from None
    try:
        summary = transfer.merge(conn, body)
    except transfer.TransferError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    event(conn, f"Situation imported from {summary['exported_at']} ({actor(request, conn)})",
          transfer.summary_line(summary))
    readiness.refresh(request, conn)
    return summary


# --- conditions -----------------------------------------------------------------------------------------------

@router.get("/conditions")
def get_conditions(request: Request, conn=Depends(get_db)):
    return view_for(request, conn)["conditions"]


@router.put("/conditions/{cid}")
def put_condition(cid: str, body: ConditionBody, request: Request, conn=Depends(get_db)):
    if cid not in cond.IDS:
        raise HTTPException(status_code=404, detail="Unknown condition")
    who = actor(request, conn)
    try:
        cond.set_state(conn, cid, body.state, since=body.since, note=body.note or "",
                       source="drill" if who == "drill" else "manual", set_by=who,
                       expected_updated_at=body.expected_updated_at)
    except cond.ConflictError:
        current = view_for(request, conn)["conditions"][cid]
        return JSONResponse(status_code=409,
                            content={"detail": "That condition changed while you were reading it", "current": current})
    updated = view_for(request, conn)["conditions"][cid]
    event(conn, f"{cond.TITLES[cid]} {body.state}"
                + (f" since {_clock(updated['since'])}" if updated["since"] else "") + f" ({who})", body.note or "")
    return updated


@router.post("/conditions/{cid}/confirm")
def confirm_condition(cid: str, request: Request, conn=Depends(get_db)):
    if cid not in cond.IDS:
        raise HTTPException(status_code=404, detail="Unknown condition")
    cond.confirm(conn, cid)
    updated = view_for(request, conn)["conditions"][cid]
    event(conn, f"{cond.TITLES[cid]} still {updated['state']} ({actor(request, conn)})")
    return updated


@router.post("/conditions/{cid}/accept")
def accept_condition(cid: str, body: AcceptBody, request: Request, conn=Depends(get_db)):
    if cid not in cond.IDS:
        raise HTTPException(status_code=404, detail="Unknown condition")
    view = view_for(request, conn)
    proposal = next((i for i in view["inferred"] if i["condition"] == cid and i["rule"] == body.rule), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail="No such proposal")
    who = actor(request, conn)
    # A proposal the box sensed for itself is recorded as `detected`, so a later reading may move it again;
    # one worked out from the implication rules stays `inferred`.
    source = "detected" if proposal["rule"].startswith("sensor:") else "inferred"
    cond.set_state(conn, cid, proposal["state"], since=proposal["due_at"], note=proposal["why"],
                   source=source, confidence=float(proposal["confidence"]), set_by=who)
    updated = view_for(request, conn)["conditions"][cid]
    event(conn, f"{cond.TITLES[cid]} {proposal['state']} taken from {proposal['rule']} ({who})", proposal["why"])
    return updated


# --- tasks ----------------------------------------------------------------------------------------------------

@router.get("/tasks")
def get_tasks(request: Request, conn=Depends(get_db)):
    return view_for(request, conn)["tasks"]


@router.put("/tasks/{task_id:path}")
def put_task(task_id: str, body: TaskBody, request: Request, conn=Depends(get_db)):
    view = view_for(request, conn)
    task = next((t for t in view["tasks"] if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    who = actor(request, conn)
    done = task["done"] if body.done is None else bool(body.done)
    person = task["person"] if body.person is None else (body.person or None)
    if task_id.startswith("checklist:"):
        slug, _, item_id = task_id[len("checklist:"):].partition("/")
        conn.execute("INSERT INTO checklist_state(playbook, item_id, checked, updated_at) VALUES (?,?,?,?) "
                     "ON CONFLICT(playbook, item_id) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at",
                     (slug, item_id, int(done), now_iso()))
    done_at = now_iso() if (done and not task["done"]) else (task["done_at"] if done else None)
    conn.execute("INSERT INTO task_state(task_id, done, done_at, person, updated_at, drill) VALUES (?,?,?,?,?,?) "
                 "ON CONFLICT(task_id) DO UPDATE SET done=excluded.done, done_at=excluded.done_at, "
                 "person=excluded.person, updated_at=excluded.updated_at, drill=excluded.drill",
                 (task_id, int(done), done_at, person, now_iso(), int(situation.is_drill(conn))))
    conn.commit()
    if body.done is not None and bool(body.done) != task["done"]:
        event(conn, f"Task {'done' if done else 'reopened'}: {task['title']}"
                    + (f" — {person}" if person else "") + f" ({who})")
    elif body.person is not None:
        event(conn, f"Task assigned to {person or 'nobody'}: {task['title']} ({who})")
    updated = view_for(request, conn)["tasks"]
    return next((t for t in updated if t["id"] == task_id), {**task, "done": done, "person": person, "done_at": done_at})


# --- home ------------------------------------------------------------------------------------------------------

@router.get("/home")
def get_home(conn=Depends(get_db)):
    return _home(conn)


@router.put("/home")
def put_home(body: HomeBody, request: Request, conn=Depends(get_db)):
    set_setting(conn, "home_lat", f"{body.lat:.6f}")
    set_setting(conn, "home_lon", f"{body.lon:.6f}")
    set_setting(conn, "home_label", body.label or "Home")
    set_setting(conn, "home_flood_zone", body.flood_zone)
    home = _home(conn)
    readiness.refresh(request, conn)               # the home on the map is worth eight points of the plan score
    event(conn, f"Home set to {home['label']} at {body.lat:.4f}, {body.lon:.4f} ({actor(request, conn)})",
          f"Flood zone {home['flood_zone']}" if home["flood_zone"] else "")
    return home


@router.get("/nearby")
def get_nearby(request: Request, lat: float | None = None, lon: float | None = None, conn=Depends(get_db)):
    """The nearest emergency department, pharmacy, GP, fuel station, water works, fire station and rest centre.

    Defaults to the home when no point is given; 404 when neither is set, because a bearing from nowhere is
    worse than no answer."""
    settings = request.app.state.settings
    if lat is None or lon is None:
        home = _home(conn)
        lat, lon = home["lat"], home["lon"]
        if lat is None or lon is None:
            raise HTTPException(status_code=404, detail="No home is set on the map, and no lat and lon were given")
    if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
        raise HTTPException(status_code=422, detail="lat must be -90 to 90 and lon -180 to 180")
    return nearby.nearest(settings, float(lat), float(lon), conn)


# --- drills ------------------------------------------------------------------------------------------------------

@router.post("/drill")
def start_drill(body: DrillBody, request: Request, conn=Depends(get_db)):
    if request.app.state.content.document("scenario", body.scenario) is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    for cid in body.conditions:
        if cid not in cond.IDS:
            raise HTTPException(status_code=422, detail=f"Unknown condition '{cid}'")
    situation.start_drill(conn, body.scenario, dict(body.conditions), body.hours_ago)
    event(conn, f"Drill started: {_title(request.app.state.content, 'scenario', body.scenario)} (drill)",
          ", ".join(f"{cid} {state}" for cid, state in sorted(body.conditions.items())))
    return view_for(request, conn)


@router.delete("/drill")
def end_drill(request: Request, conn=Depends(get_db)):
    if not situation.is_drill(conn):
        raise HTTPException(status_code=404, detail="No drill is running")
    who = actor(request, conn)
    summary = situation.end_drill(conn)
    hours = summary["elapsed_s"] / 3600
    length = f"{summary['elapsed_s'] // 60} min" if hours < 1 else f"{hours:.0f} h"
    jobs = f"{summary['tasks_done']} job{'s' if summary['tasks_done'] != 1 else ''} ticked"
    event(conn, f"Drill ended after {length}: {jobs} ({who})")
    readiness.refresh(request, conn)               # a drill just now is ten points of practice
    return view_for(request, conn)
