from fastapi import APIRouter, Depends, Request

from sos import services, situation, system
from sos.routers import get_db

router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(request: Request, conn=Depends(get_db)):
    result = system.status(conn, request.app.state.settings)
    result["ai"] = request.app.state.ai_runtime.snapshot()
    result["situation"] = situation.brief(conn)
    result["services"] = services.state(conn)
    return result
