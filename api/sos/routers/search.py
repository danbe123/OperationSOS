from fastapi import APIRouter, Depends, Request

from sos import search as search_mod
from sos.routers import get_db

router = APIRouter(tags=["search"])


@router.get("/search")
async def do_search(request: Request, q: str = "", sources: str | None = None, limit: int = 40, conn=Depends(get_db)):
    wanted = [s for s in sources.split(",") if s] if sources else None
    return await search_mod.search(conn, request.app.state.settings, request.app.state.kiwix, q, wanted, limit,
                                   semantic=getattr(request.app.state, "semantic", None))


@router.get("/suggest")
async def do_suggest(request: Request, q: str = "", conn=Depends(get_db)):
    return await search_mod.suggest(conn, request.app.state.settings, request.app.state.kiwix, q)
