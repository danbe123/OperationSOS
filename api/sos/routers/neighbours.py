"""The street list: the neighbours register and the printable sheet (spec section 8)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from sos import neighbours as nb
from sos.db import now_iso
from sos.routers import get_db
from sos.routers.situation import actor, event

router = APIRouter(tags=["neighbours"])


class NeighbourIn(BaseModel):
    name: str
    address: str = ""
    needs: str = ""
    skills: str = ""
    contacts: str = ""
    notes: str = ""


class NeighbourPatch(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    needs: Optional[str] = None
    skills: Optional[str] = None
    contacts: Optional[str] = None
    notes: Optional[str] = None


def _found(conn, neighbour_id: int) -> dict:
    person = nb.get(conn, neighbour_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Neighbour not found")
    return person


@router.get("/neighbours")
def list_neighbours(conn=Depends(get_db)):
    return nb.listing(conn)


@router.post("/neighbours")
def add_neighbour(body: NeighbourIn, request: Request, conn=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Neighbours need a name")
    person = nb.add(conn, body.model_dump())
    event(conn, f"Neighbour added: {nb.label(person)} ({actor(request, conn)})", person["needs"])
    return person


@router.put("/neighbours/{neighbour_id}")
def update_neighbour(neighbour_id: int, body: NeighbourPatch, request: Request, conn=Depends(get_db)):
    _found(conn, neighbour_id)
    values = body.model_dump(exclude_none=True)
    if "name" in values and not values["name"].strip():
        raise HTTPException(status_code=400, detail="Neighbours need a name")
    person = nb.update(conn, neighbour_id, values)
    event(conn, f"Neighbour updated: {nb.label(person)} ({actor(request, conn)})", person["needs"])
    return person


@router.delete("/neighbours/{neighbour_id}")
def delete_neighbour(neighbour_id: int, request: Request, conn=Depends(get_db)):
    person = _found(conn, neighbour_id)
    nb.remove(conn, neighbour_id)
    event(conn, f"Neighbour removed: {nb.label(person)} ({actor(request, conn)})")
    return {"ok": True}


@router.get("/street-list", response_class=PlainTextResponse)
def get_street_list(conn=Depends(get_db)):
    """One sheet of paper for the front of the fridge: who is on the street, what they need, who to ring."""
    return PlainTextResponse(nb.street_list(nb.listing(conn), now_iso()),
                             media_type="text/markdown; charset=utf-8")
