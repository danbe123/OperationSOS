"""AI endpoints placeholder: every /api/ai/* call answers 503 until plan 05 installs the assistant."""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["ai"])


@router.api_route("/ai/{rest:path}", methods=["GET", "POST"])
def ai_not_installed(rest: str):
    raise HTTPException(status_code=503, detail="AI not installed")
