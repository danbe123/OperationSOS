from fastapi import APIRouter, Depends, HTTPException, Request

from sos import library
from sos.routers import get_db

router = APIRouter(tags=["library"])


@router.get("/library")
def list_library(request: Request, conn=Depends(get_db)):
    return library.library_response(conn, request.app.state.settings)


@router.get("/library/{item_id}")
def get_library_item(item_id: str, request: Request, conn=Depends(get_db)):
    row = library.get_item(conn, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return library.item_dict(row, library.ext_mounted(request.app.state.settings))
