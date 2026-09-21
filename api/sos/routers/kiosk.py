"""Endpoints only the kiosk browser on the box may call (backlight, idle state)."""
import time
from typing import Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from sos import system
from sos.routers import require_localhost

router = APIRouter(tags=["kiosk"], dependencies=[Depends(require_localhost)])
IDLE_LEVEL = 10


class Heartbeat:
    """When the kiosk page last said it was alive, in memory only: a restart of the API forgets it, and the kiosk
    wrapper reads that as "no news", never as "hung". Posts are limited to six a minute (the page sends two), and
    a flood does not refresh the time."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.started = clock()
        self.last: float | None = None
        self.limiter = system.RateLimiter(6, 60.0, clock)

    def hit(self, key: str) -> bool:
        if not self.limiter.allow(key):
            return False
        self.last = self.clock()
        return True

    def snapshot(self) -> dict:
        now = self.clock()
        return {"age_s": None if self.last is None else round(now - self.last, 1), "api_up_s": round(now - self.started, 1)}


class BacklightBody(BaseModel):
    level: int = Field(ge=0, le=100)


class IdleBody(BaseModel):
    state: Literal["idle", "active"]


def apply_backlight(request: Request, level: int, persist: bool = True) -> dict:
    applied = system.set_backlight(request.app.state.settings, level)
    if applied is None:
        raise HTTPException(status_code=501, detail="No backlight device")
    if persist:
        # backlight_level is the level idle->active restores to. Only the persisted (system/settings)
        # setter updates it; a one-off kiosk adjustment must not become the new restore target.
        request.app.state.backlight_level = applied
    return {"level": applied}


@router.post("/kiosk/backlight")
def kiosk_backlight(body: BacklightBody, request: Request):
    return apply_backlight(request, body.level, persist=False)


@router.post("/kiosk/idle")
def kiosk_idle(body: IdleBody, request: Request):
    request.app.state.idle = body.state
    settings = request.app.state.settings
    if body.state == "idle":
        system.set_backlight(settings, IDLE_LEVEL)
    else:
        system.set_backlight(settings, getattr(request.app.state, "backlight_level", 100))
    return {"ok": True}


@router.post("/kiosk/alive")
def kiosk_alive(request: Request):
    """The kiosk page's heartbeat (every 30 s, from the kiosk's own page only). No body, no PIN: it says nothing
    and changes nothing but this timestamp. Loopback only, though nothing relies on that."""
    if not request.app.state.kiosk_heartbeat.hit("kiosk"):
        raise HTTPException(status_code=429, detail="Too many heartbeats")
    return {"ok": True}


@router.get("/kiosk/alive-age")
def kiosk_alive_age(request: Request):
    """How long since the kiosk page last posted, for `sos-kiosk-app`: null when it has not since the API started."""
    return request.app.state.kiosk_heartbeat.snapshot()
