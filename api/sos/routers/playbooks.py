"""Playbooks, their shared checklist state, and standalone modules."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sos.db import now_iso
from sos.routers import get_db

router = APIRouter(tags=["playbooks"])


class ChecklistBody(BaseModel):
    checked: bool


def _rendered(request: Request, slug: str):
    doc = request.app.state.content.rendered("scenario", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return doc


def _checklist(conn, slug: str, rendered) -> list[dict]:
    state = {r["item_id"]: r for r in conn.execute(
        "SELECT item_id, checked, updated_at FROM checklist_state WHERE playbook=?", (slug,))}
    out = []
    for item in rendered.checklist:
        row = state.get(item["id"])
        out.append({"id": item["id"], "text": item["text"], "checked": bool(row["checked"]) if row else False,
                    "updated_at": row["updated_at"] if row else None})
    return out


def _summary(doc) -> dict:
    return {"slug": doc.id, "title": doc.title, "icon": doc.icon, "summary": doc.summary, "order": doc.order}


@router.get("/playbooks")
def list_playbooks(request: Request):
    return [_summary(d) for d in request.app.state.content.list("scenario")]


@router.get("/playbooks/{slug}")
def get_playbook(slug: str, request: Request, conn=Depends(get_db)):
    r = _rendered(request, slug)
    return {"slug": r.slug, "title": r.title, "icon": r.icon, "summary": r.summary, "order": r.order,
            "sections": r.sections, "checklist": _checklist(conn, slug, r), "modules": r.modules,
            "overlays": r.overlays, "sources": r.sources, "reviewed": r.reviewed}


@router.put("/playbooks/{slug}/checklist/{item_id:path}")
def set_checklist_item(slug: str, item_id: str, body: ChecklistBody, request: Request, conn=Depends(get_db)):
    r = _rendered(request, slug)
    if item_id not in {c["id"] for c in r.checklist}:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    conn.execute(
        "INSERT INTO checklist_state(playbook, item_id, checked, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(playbook, item_id) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at",
        (slug, item_id, int(body.checked), now_iso()),
    )
    conn.commit()
    return _checklist(conn, slug, r)


@router.delete("/playbooks/{slug}/checklist")
def reset_checklist(slug: str, request: Request, conn=Depends(get_db)):
    r = _rendered(request, slug)
    conn.execute("DELETE FROM checklist_state WHERE playbook=?", (slug,))
    conn.commit()
    return _checklist(conn, slug, r)


@router.get("/modules/{slug}")
def get_module(slug: str, request: Request):
    doc = request.app.state.content.rendered("module", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return {"slug": doc.slug, "title": doc.title, "html": doc.html}
