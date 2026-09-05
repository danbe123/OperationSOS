from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["cards"])


def _card(doc) -> dict:
    return {"slug": doc.slug, "title": doc.title, "icon": doc.icon, "order": doc.order, "html": doc.html}


@router.get("/cards")
def list_cards(request: Request):
    content = request.app.state.content
    return [_card(content.rendered("card", d.id)) for d in content.list("card")]


@router.get("/cards/{slug}")
def get_card(slug: str, request: Request):
    doc = request.app.state.content.rendered("card", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card(doc)
