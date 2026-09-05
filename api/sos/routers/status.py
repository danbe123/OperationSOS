from fastapi import APIRouter, Depends, Request

from sos import readiness, situation, system
from sos.routers import get_db
from sos.routers.situation import view_for

router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(request: Request, conn=Depends(get_db)):
    result = system.status(conn, request.app.state.settings)
    result["ai"] = request.app.state.ai_runtime.snapshot()
    result["situation"] = situation.brief(conn)
    view = view_for(request, conn)
    result["conditions"] = {cid: item["state"] for cid, item in view["conditions"].items()}
    result["modes"] = view["modes"]
    result["drill"] = view["meta"]["drill"]
    score = readiness.stored(conn)
    if score is None:                              # first boot: store it once so later reads are a settings lookup
        score = view["readiness"]["score"]
        readiness.refresh(request, conn)
    result["readiness_score"] = score
    return result
