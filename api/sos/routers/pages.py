from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["pages"])


@router.get("/pages")
def list_pages(request: Request):
    return [{"slug": d.id, "title": d.title, "icon": d.icon, "order": d.order, "category": d.category, "summary": d.summary}
            for d in request.app.state.content.list("page")]


@router.get("/pages/{slug}")
def get_page(slug: str, request: Request):
    doc = request.app.state.content.rendered("page", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"slug": doc.slug, "title": doc.title, "icon": doc.icon, "order": doc.order, "html": doc.html, "category": doc.category}
