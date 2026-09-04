from fastapi import APIRouter, Depends

from sos import places
from sos.routers import get_db

router = APIRouter(tags=["places"])


@router.get("/places")
def get_places(q: str = "", limit: int = 10, conn=Depends(get_db)):
    return places.query_places(conn, q, limit)
