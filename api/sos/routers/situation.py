"""The situation clock endpoints (tools spec section 4)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sos import situation
from sos.routers import get_db

router = APIRouter(tags=["situation"])


class StartBody(BaseModel):
    slug: str


def _title(request: Request, slug: str | None) -> str | None:
    if not slug:
        return None
    doc = request.app.state.content.rendered("scenario", slug)
    return doc.title if doc is not None else slug


@router.get("/situation")
def get_situation(request: Request, conn=Depends(get_db)):
    snap = situation.snapshot(conn)
    if snap["slug"]:
        snap["title"] = _title(request, snap["slug"])
    return snap


@router.post("/situation")
def start_situation(body: StartBody, request: Request, conn=Depends(get_db)):
    if request.app.state.content.rendered("scenario", body.slug) is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    situation.start(conn, body.slug)
    return get_situation(request, conn)


@router.delete("/situation")
def end_situation(conn=Depends(get_db)):
    situation.clear(conn)
    return {"slug": None}
