"""What the box senses, what it has recorded off the radio, and reading a page aloud."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from sos import sensors, speak
from sos.routers import get_db, settings_dep

router = APIRouter(tags=["sensors"])
RECORDING_NAME = re.compile(r"^[A-Za-z0-9._-]+\.wav$")


class SpeakBody(BaseModel):
    text: str


@router.get("/sensors")
def get_sensors(request: Request, conn=Depends(get_db)):
    """The latest reading from every driver, and what the box makes of them."""
    settings = request.app.state.settings
    return {"readings": sensors.latest(conn), "detected": sensors.detected_states(conn),
            "drivers": {"rtl_power": sensors.have(settings.rtl_power_bin),
                        "rtl_fm": sensors.have(settings.rtl_fm_bin),
                        "piper": speak.available(settings),
                        "enabled": bool(settings.sensors)}}


@router.get("/recordings")
def get_recordings(settings=Depends(settings_dep)):
    return sensors.list_recordings(settings)


@router.get("/recordings/{name}")
def get_recording(name: str, settings=Depends(settings_dep)):
    if not RECORDING_NAME.match(name):
        raise HTTPException(status_code=404, detail="No such recording")
    path = settings.recordings / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No such recording")
    return FileResponse(path, media_type="audio/wav", filename=name)


@router.post("/speak")
def post_speak(body: SpeakBody, settings=Depends(settings_dep)):
    """Piper reads the text in a British voice and the WAV comes back; 503 when Piper is not installed."""
    try:
        audio = speak.synthesise(settings, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except speak.SpeakError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return Response(content=audio, media_type="audio/wav",
                    headers={"Cache-Control": "no-store", "Content-Disposition": 'inline; filename="speech.wav"'})
