"""The situation: the clock, the conditions, the tasks, the home, drills and the View every screen reads."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from sos import conditions as cond
from sos import engine, rules as rules_mod, situation
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

def _title(request: Request, kind: str, slug: str) -> Optional[str]:
    doc = request.app.state.content.document(kind, slug)
    return doc.title if doc is not None else None


def _home(conn: sqlite3.Connection) -> dict:
    lat, lon = get_setting(conn, "home_lat"), get_setting(conn, "home_lon")
    return {"lat": float(lat) if lat else None, "lon": float(lon) if lon else None,
            "label": get_setting(conn, "home_label", "Home"), "flood_zone": get_setting(conn, "home_flood_zone")}


def _stock(conn: sqlite3.Connection) -> tuple[dict, ...]:
    from sos.routers.household import days_left, people_count

    people = people_count(conn)
    return tuple({"name": r["name"], "category": r["category"], "notes": r["notes"] or "",
                  "days_left": days_left(r["quantity"], r["per_person_day"], people)}
                 for r in conn.execute("SELECT * FROM stock ORDER BY category, id"))


def _titles(request: Request, ruleset: rules_mod.Rules, scenario: Optional[str]) -> dict[str, str]:
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
            title = _title(request, kinds[scheme], slug)
            if title:
                out[f"{scheme}:{slug}"] = title
    return out


def _ruleset(request: Request) -> rules_mod.Rules:
    return rules_mod.load(request.app.state.settings.playbooks / "rules")


def build_model(request: Request, conn: sqlite3.Connection, now: Optional[datetime] = None) -> engine.Model:
    """Everything in the database that the engine is allowed to see, as one immutable snapshot."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    ruleset = _ruleset(request)
    slug = get_setting(conn, "situation_slug")
    scenario = situation.snapshot(conn, _title(request, "scenario", slug) if slug else None, now) if slug else None
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
        rendered = request.app.state.content.rendered("scenario", slug, flags)
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
    return engine.Model(
        now=now, conditions=cond.load(conn), scenario=scenario, household=household, stock=_stock(conn), home=home,
        drill=situation.is_drill(conn), checklist=checklist, checklist_state=checklist_state, task_state=task_state,
        titles=_titles(request, ruleset, slug), meeting_point=meeting is not None,
        last_drill_at=situation.last_drill_at(conn), tz=get_setting(conn, "timezone", "Europe/London"),
    )


def view_for(request: Request, conn: sqlite3.Connection) -> dict:
    return engine.compute(build_model(request, conn), _ruleset(request))


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
        snap["title"] = _title(request, "scenario", snap["slug"]) or snap["slug"]
    return snap


@router.post("/situation")
def start_situation(body: StartBody, request: Request, conn=Depends(get_db)):
    if request.app.state.content.document("scenario", body.slug) is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    situation.start(conn, body.slug)
    event(conn, f"Situation started: {_title(request, 'scenario', body.slug)} ({actor(request, conn)})")
    return get_situation(request, conn)


@router.delete("/situation")
def end_situation(request: Request, conn=Depends(get_db)):
    snap = situation.snapshot(conn)
    if snap["slug"]:
        event(conn, f"Situation ended: {_title(request, 'scenario', snap['slug'])} ({actor(request, conn)})")
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
    cond.set_state(conn, cid, proposal["state"], since=proposal["due_at"], note=proposal["why"],
                   source="inferred", confidence=float(proposal["confidence"]), set_by=who)
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
    event(conn, f"Home set to {home['label']} at {body.lat:.4f}, {body.lon:.4f} ({actor(request, conn)})",
          f"Flood zone {home['flood_zone']}" if home["flood_zone"] else "")
    return home


# --- drills ------------------------------------------------------------------------------------------------------

@router.post("/drill")
def start_drill(body: DrillBody, request: Request, conn=Depends(get_db)):
    if request.app.state.content.document("scenario", body.scenario) is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    for cid in body.conditions:
        if cid not in cond.IDS:
            raise HTTPException(status_code=422, detail=f"Unknown condition '{cid}'")
    situation.start_drill(conn, body.scenario, dict(body.conditions), body.hours_ago)
    event(conn, f"Drill started: {_title(request, 'scenario', body.scenario)} (drill)",
          ", ".join(f"{cid} {state}" for cid, state in sorted(body.conditions.items())))
    return view_for(request, conn)


@router.delete("/drill")
def end_drill(request: Request, conn=Depends(get_db)):
    if not situation.is_drill(conn):
        raise HTTPException(status_code=404, detail="No drill is running")
    who = actor(request, conn)
    summary = situation.end_drill(conn)
    event(conn, f"Drill ended: {summary['tasks_done']} task{'s' if summary['tasks_done'] != 1 else ''} done in "
                f"{summary['elapsed_s'] // 60} minutes ({who})")
    return view_for(request, conn)
