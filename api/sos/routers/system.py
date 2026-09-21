"""System control endpoints. PIN-gated ones depend on require_pin; rescan is localhost-only."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from sos import library, system
from sos.routers import get_db, get_db_durable, require_localhost, require_pin
from sos.routers.kiosk import BacklightBody, apply_backlight

router = APIRouter(tags=["system"])


class PowerBody(BaseModel):
    mode: Literal["normal", "low"]


class EthBody(BaseModel):
    mode: Literal["client", "direct"]


class HotspotBody(BaseModel):
    ssid: str
    passphrase: str | None = None


class SettingsBody(BaseModel):
    # Not a Literal: invalid values must reach system.apply_settings so its ValueError becomes a 400
    # with "default_theme" in the message, rather than a generic pydantic 422.
    default_theme: str | None = None
    thermal_ai_off_c: int | None = None
    idle_minutes: int | None = None
    home_minutes: int | None = None


class PeopleBody(BaseModel):
    # Not a range on the field: an out-of-range count must reach system.apply_settings so its ValueError
    # becomes a 400 naming "people", the same way default_theme's does.
    people: int


class UpdateBody(BaseModel):
    """Whole tiers, or `only` these item ids (their tiers are looked up); at least one of the two."""
    tiers: list[Literal["core", "extended"]] = Field(default_factory=list)
    only: list[str] = Field(default_factory=list)


class PinBody(BaseModel):
    pin: str


def _status(request: Request, conn) -> dict:
    result = system.status(conn, request.app.state.settings)
    result["ai"] = request.app.state.ai_runtime.snapshot()
    return result


@router.post("/system/backlight")
def system_backlight(body: BacklightBody, request: Request):
    return apply_backlight(request, body.level)


@router.post("/system/power-mode", dependencies=[Depends(require_pin)])
async def power_mode(body: PowerBody, request: Request, conn=Depends(get_db_durable)):
    if body.mode == "low":
        await system.stop_ai_for(request.app, "power")
    system.set_power_mode(conn, request.app.state.settings, body.mode)
    return _status(request, conn)


@router.post("/system/eth-mode", dependencies=[Depends(require_pin)])
def eth_mode(body: EthBody, request: Request, conn=Depends(get_db_durable)):
    system.set_eth_mode(conn, request.app.state.settings, body.mode)
    return _status(request, conn)


@router.post("/system/hotspot", dependencies=[Depends(require_pin)])
def hotspot(body: HotspotBody, request: Request, conn=Depends(get_db_durable)):
    system.set_hotspot(conn, request.app.state.settings, body.ssid, body.passphrase)
    return _status(request, conn)


@router.post("/system/settings")
def settings_update(body: SettingsBody, request: Request, conn=Depends(get_db_durable)):
    system.apply_settings(conn, body.model_dump(exclude_none=True))
    return _status(request, conn)


@router.get("/settings/people")
def get_people(conn=Depends(get_db)):
    """The one number the box asks a household for: how many people the kits are scaled to."""
    return {"people": system.people_count(conn)}


@router.put("/settings/people")
def put_people(body: PeopleBody, conn=Depends(get_db_durable)):
    system.apply_settings(conn, {"people": body.people})
    return {"people": system.people_count(conn)}


@router.post("/system/rescan", dependencies=[Depends(require_localhost)])
def rescan(request: Request, conn=Depends(get_db)):
    return system.rescan(conn, request.app.state.settings)


@router.post("/system/update", dependencies=[Depends(require_pin)])
def update(body: UpdateBody, request: Request, conn=Depends(get_db)):
    settings = request.app.state.settings
    only = list(dict.fromkeys(body.only))
    if only:
        marks = ",".join("?" for _ in only)
        rows = {r["id"]: r["tier"] for r in conn.execute(f"SELECT id, tier FROM library_items WHERE id IN ({marks})", only)}
        missing = [i for i in only if i not in rows]
        if missing:
            raise HTTPException(status_code=404, detail=f"Not in the library: {', '.join(missing)}")
        wanted = list(dict.fromkeys(rows[i] for i in only))
    elif body.tiers:
        wanted = list(dict.fromkeys(body.tiers))
    else:
        raise HTTPException(status_code=422, detail="Say which tiers or which items to fetch")
    tiers = [t for t in wanted if t == "core" or library.ext_mounted(settings)]
    if not tiers:
        raise HTTPException(status_code=400, detail="External drive is not connected")
    if not request.app.state.updater.start(tiers, only or None):
        raise HTTPException(status_code=409, detail="Update already running")
    return {"started": True}


@router.get("/system/update/progress")
def update_progress(request: Request):
    return request.app.state.updater.progress()


@router.post("/system/pin")
def pin_login(body: PinBody, request: Request, conn=Depends(get_db_durable)):
    # Checked before the rate limiter: a call made while no PIN is set yet must not burn an attempt.
    if not system.pin_required(conn):
        raise HTTPException(status_code=401, detail="No PIN is set")
    host = request.client.host if request.client else "unknown"
    if not request.app.state.pin_limiter.allow(host):
        raise HTTPException(status_code=429, detail="Too many attempts; wait a minute")
    if not system.verify_pin(conn, body.pin):
        raise HTTPException(status_code=401, detail="Wrong PIN")
    return {"token": request.app.state.tokens.issue(), "expires_in": system.TOKEN_TTL}


@router.post("/system/pin/change", dependencies=[Depends(require_pin)])
def pin_change(body: PinBody, request: Request, conn=Depends(get_db_durable)):
    if not system.pin_required(conn):
        # No PIN claimed yet: require_pin no-ops in this state, so the first claim must be restricted to
        # the box itself -- the hotspot ships open, and anyone in range could otherwise claim the PIN first.
        require_localhost(request)
    system.set_pin(conn, body.pin)
    request.app.state.tokens.revoke_all()
    return {"ok": True}
