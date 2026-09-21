"""Kits: tiered lists of things to have and their shared ticks (kits spec, cut back by the no-setup spec)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from sos import content as content_mod, directives, kits as kits_mod, system
from sos.db import now_iso
from sos.routers import get_db_durable
from sos.routers.situation import current_flags

router = APIRouter(tags=["kits"])


class ItemBody(BaseModel):
    # A tick is the only thing a kit item takes now: an old client's `stock` block is a 422, not a
    # silent no-op, so nobody thinks a hand-off into a Stock list that no longer exists has happened.
    model_config = ConfigDict(extra="forbid")

    checked: bool


def _key(slug: str) -> str:
    return f"kit:{slug}"


def _ticks(conn, slug: str) -> dict[str, dict]:
    return {r["item_id"]: {"checked": bool(r["checked"]), "updated_at": r["updated_at"]}
            for r in conn.execute("SELECT item_id, checked, updated_at FROM checklist_state WHERE playbook=?", (_key(slug),))}


def _tier_counts(kit, ticks: dict[str, dict]) -> dict[str, dict]:
    out = {}
    for tier in kits_mod.TIERS:
        items = kit.items_in(tier)
        out[tier] = {"done": sum(1 for i in items if ticks.get(i.id, {}).get("checked")), "total": len(items)}
    return out


def _inline(text: str, request: Request) -> str:
    """A why or a note as inline HTML, so its `[Prepare](kiwix:...)` becomes a link the screen can render.
    Markdown gives a whole paragraph back; the row wants what is inside it.

    Only when there is exactly one paragraph to unwrap. Stripping the first `<p>` and the last `</p>`
    off a two-paragraph why leaves `first</p><p>second` -- a row of broken markup on the screen -- so
    a why that really is two paragraphs comes back as the block HTML it is."""
    if not text:
        return ""
    html = content_mod.render_markdown(text, request.app.state.content.resolver).strip()
    if html.startswith("<p>") and html.endswith("</p>") and "<p>" not in html[3:]:
        html = html[3:-4]
    return html.strip()


def _get_kit(request: Request, slug: str):
    kit = request.app.state.content.kit(slug)
    if kit is None:
        raise HTTPException(status_code=404, detail="Kit not found")
    return kit


def kit_view(kit, conn, request: Request) -> dict:
    people = kits_mod.matching_people(kit, system.people_count(conn))
    ticks = _ticks(conn, kit.id)
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
            items.append({
                "id": item.id, "name": item.name, "why": item.why, "note": item.note, "link": item.link,
                "why_html": _inline(item.why, request), "note_html": _inline(item.note, request),
                "href": content_mod.resolve_link(item.link) if item.link else None,
                "qty": kits_mod.scaled(item, days, people),
                "checked": bool(tick.get("checked", False)), "updated_at": tick.get("updated_at"),
            })
        tiers.append({"id": tier_id, "title": tier.get("title", tier_id.title()), "days": days, "why": tier.get("why", ""),
                      "done": sum(1 for i in items if i["checked"]), "total": len(items), "items": items})
    return {"slug": kit.id, "title": kit.title, "icon": kit.icon, "order": kit.order, "summary": kit.summary,
            "intro_html": intro_html, "sources": kit.sources, "relevant": kits_mod.relevant(kit),
            "people": people, "tiers": tiers}


@router.get("/kits")
def list_kits(request: Request, conn=Depends(get_db_durable)):
    out = []
    for kit in request.app.state.content.kits():
        out.append({"slug": kit.id, "title": kit.title, "icon": kit.icon, "order": kit.order, "summary": kit.summary,
                    "relevant": kits_mod.relevant(kit), "tiers": _tier_counts(kit, _ticks(conn, kit.id))})
    return {"people": system.people_count(conn), "kits": out}


@router.get("/kits/have")
def kits_have(request: Request, conn=Depends(get_db_durable)):
    """Everything ticked, across every kit: the "what you have" list, kits in their order and items in
    the kit's own (basic, then serious, then full). A kit with nothing ticked is left out rather than
    printed as an empty heading. Declared before `/kits/{slug}` so `have` is never read as a slug."""
    people = system.people_count(conn)
    out = []
    for kit in request.app.state.content.kits():
        ticks = _ticks(conn, kit.id)
        if not any(t["checked"] for t in ticks.values()):
            continue
        scale = kits_mod.matching_people(kit, people)
        items = []
        for tier_id in kits_mod.TIERS:
            days = int(kit.tiers.get(tier_id, {}).get("days", kits_mod.TIER_DAYS[tier_id]))
            for item in kit.items_in(tier_id):
                tick = ticks.get(item.id)
                if not (tick and tick["checked"]):
                    continue
                items.append({"id": item.id, "name": item.name, "tier": tier_id,
                              "qty": kits_mod.scaled(item, days, scale), "updated_at": tick["updated_at"]})
        if items:
            out.append({"slug": kit.id, "title": kit.title, "icon": kit.icon, "items": items})
    return {"people": people, "kits": out}


@router.get("/kits/{slug}")
def get_kit(slug: str, request: Request, conn=Depends(get_db_durable)):
    return kit_view(_get_kit(request, slug), conn, request)


@router.put("/kits/{slug}/items/{item_id}")
def set_item(slug: str, item_id: str, body: ItemBody, request: Request, conn=Depends(get_db_durable)):
    kit = _get_kit(request, slug)
    item = next((i for i in kit.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Kit item not found")
    conn.execute("INSERT INTO checklist_state(playbook, item_id, checked, updated_at) VALUES (?,?,?,?) "
                 "ON CONFLICT(playbook, item_id) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at",
                 (_key(kit.id), item_id, int(body.checked), now_iso()))
    conn.commit()
    return kit_view(kit, conn, request)


@router.delete("/kits/{slug}/ticks")
def reset_ticks(slug: str, request: Request, conn=Depends(get_db_durable)):
    kit = _get_kit(request, slug)
    conn.execute("DELETE FROM checklist_state WHERE playbook=?", (_key(kit.id),))
    conn.commit()
    return kit_view(kit, conn, request)
