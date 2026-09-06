"""Kits: tiered lists of things to have, their shared ticks, and the hand-off into Stock (kits spec)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sos import content as content_mod, directives, kits as kits_mod, readiness
from sos.db import now_iso
from sos.routers import get_db
from sos.routers.household import _item as stock_item_view, people_count
from sos.routers.situation import current_flags

router = APIRouter(tags=["kits"])


class StockAdd(BaseModel):
    quantity: float
    expires: Optional[str] = None
    notes: str = ""


class ItemBody(BaseModel):
    checked: bool
    stock: Optional[StockAdd] = None


def _key(slug: str) -> str:
    return f"kit:{slug}"


def _household(conn) -> list[dict]:
    return [{"name": r["name"], "age": r["age"], "needs": r["needs"] or "", "medications": r["medications"] or ""}
            for r in conn.execute("SELECT * FROM household ORDER BY id")]


def _ticks(conn, slug: str) -> dict[str, dict]:
    return {r["item_id"]: {"checked": bool(r["checked"]), "updated_at": r["updated_at"]}
            for r in conn.execute("SELECT item_id, checked, updated_at FROM checklist_state WHERE playbook=?", (_key(slug),))}


def _stock_rows(conn, slug: str, people: int) -> dict[str, dict]:
    out = {}
    for r in conn.execute("SELECT * FROM stock WHERE kit_item LIKE ? ORDER BY id", (f"{slug}/%",)):
        item_id = r["kit_item"].partition("/")[2]
        out.setdefault(item_id, stock_item_view(r, people))
    return out


def _tier_counts(kit, ticks: dict[str, dict]) -> dict[str, dict]:
    out = {}
    for tier in kits_mod.TIERS:
        items = kit.items_in(tier)
        out[tier] = {"done": sum(1 for i in items if ticks.get(i.id, {}).get("checked")), "total": len(items)}
    return out


def _get_kit(request: Request, slug: str):
    kit = request.app.state.content.kit(slug)
    if kit is None:
        raise HTTPException(status_code=404, detail="Kit not found")
    return kit


def kit_view(kit, conn, request: Request) -> dict:
    people = people_count(conn)
    household = _household(conn)
    ticks = _ticks(conn, kit.id)
    stock_rows = _stock_rows(conn, kit.id, people)
    flags = current_flags(request, conn)
    intro_md = directives.resolve(kit.intro, flags) if kit.intro else ""
    intro_html = content_mod.render_markdown(intro_md, request.app.state.content.resolver) if intro_md else ""
    tiers = []
    for tier_id in kits_mod.TIERS:
        tier = kit.tiers.get(tier_id, {})
        days = int(tier.get("days", kits_mod.TIER_DAYS[tier_id]))
        items = []
        for item in kit.items_in(tier_id):
            tick = ticks.get(item.id, {})
            stock_row = stock_rows.get(item.id)
            items.append({
                "id": item.id, "name": item.name, "why": item.why, "note": item.note, "link": item.link,
                "href": content_mod.resolve_link(item.link) if item.link else None,
                "qty": kits_mod.scaled(item, days, people),
                "stock": dict(item.stock) if item.stock else None,
                "checked": bool(tick.get("checked", False)), "updated_at": tick.get("updated_at"),
                "stock_item": None if stock_row is None else {
                    "id": stock_row["id"], "quantity": stock_row["quantity"], "unit": stock_row["unit"],
                    "expires": stock_row["expires"], "days_left": stock_row["days_left"]},
            })
        tiers.append({"id": tier_id, "title": tier.get("title", tier_id.title()), "days": days, "why": tier.get("why", ""),
                      "done": sum(1 for i in items if i["checked"]), "total": len(items), "items": items})
    return {"slug": kit.id, "title": kit.title, "icon": kit.icon, "order": kit.order, "summary": kit.summary,
            "intro_html": intro_html, "sources": kit.sources, "relevant": kits_mod.relevant(kit, household),
            "people": people, "tiers": tiers}


@router.get("/kits")
def list_kits(request: Request, conn=Depends(get_db)):
    household = _household(conn)
    out = []
    for kit in request.app.state.content.kits():
        out.append({"slug": kit.id, "title": kit.title, "icon": kit.icon, "order": kit.order, "summary": kit.summary,
                    "relevant": kits_mod.relevant(kit, household), "tiers": _tier_counts(kit, _ticks(conn, kit.id))})
    return {"people": people_count(conn), "kits": out}


@router.get("/kits/{slug}")
def get_kit(slug: str, request: Request, conn=Depends(get_db)):
    return kit_view(_get_kit(request, slug), conn, request)


@router.put("/kits/{slug}/items/{item_id}")
def set_item(slug: str, item_id: str, body: ItemBody, request: Request, conn=Depends(get_db)):
    kit = _get_kit(request, slug)
    item = next((i for i in kit.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Kit item not found")
    if body.stock is not None:
        if not item.stock:
            raise HTTPException(status_code=400, detail="This item is not tracked in Stock")
        if body.stock.quantity < 0:
            raise HTTPException(status_code=400, detail="Quantity must be zero or more")
        key = f"{slug}/{item_id}"
        if conn.execute("SELECT 1 FROM stock WHERE kit_item=?", (key,)).fetchone():
            raise HTTPException(status_code=409, detail="This item is already in Stock")
        rate = float(item.qty["amount"]) if item.qty and item.qty.get("per") == "person-day" else None
        conn.execute("INSERT INTO stock(name, category, quantity, unit, per_person_day, expires, notes, updated_at, kit_item) "
                     "VALUES (?,?,?,?,?,?,?,?,?)",
                     (item.name, item.stock["category"], body.stock.quantity, item.stock["unit"], rate,
                      body.stock.expires, body.stock.notes, now_iso(), key))
    conn.execute("INSERT INTO checklist_state(playbook, item_id, checked, updated_at) VALUES (?,?,?,?) "
                 "ON CONFLICT(playbook, item_id) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at",
                 (_key(slug), item_id, int(body.checked), now_iso()))
    conn.commit()
    readiness.refresh(request, conn)
    return kit_view(kit, conn, request)


@router.delete("/kits/{slug}/ticks")
def reset_ticks(slug: str, request: Request, conn=Depends(get_db)):
    kit = _get_kit(request, slug)
    conn.execute("DELETE FROM checklist_state WHERE playbook=?", (_key(slug),))
    conn.commit()
    readiness.refresh(request, conn)
    return kit_view(kit, conn, request)
