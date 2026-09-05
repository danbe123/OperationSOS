"""Endpoints only the kiosk browser on the box may call (backlight, idle state)."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from sos import system
from sos.routers import require_localhost

router = APIRouter(tags=["kiosk"], dependencies=[Depends(require_localhost)])
IDLE_LEVEL = 10


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
