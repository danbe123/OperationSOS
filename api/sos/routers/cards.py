from fastapi import APIRouter, Depends, HTTPException, Request

from sos.routers import get_db
from sos.routers.situation import current_flags

router = APIRouter(tags=["cards"])


def _card(doc) -> dict:
    return {"slug": doc.slug, "title": doc.title, "icon": doc.icon, "order": doc.order, "summary": doc.summary, "html": doc.html}


@router.get("/cards")
def list_cards(request: Request, conn=Depends(get_db)):
    content = request.app.state.content
    flags = current_flags(request, conn)
    return [_card(content.rendered("card", d.id, flags)) for d in content.list("card")]


@router.get("/cards/{slug}")
def get_card(slug: str, request: Request, conn=Depends(get_db)):
    doc = request.app.state.content.rendered("card", slug, current_flags(request, conn))
    if doc is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card(doc)
