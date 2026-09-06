"""Household register and stock (tools spec sections 3 and 4)."""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sos import readiness
from sos.db import now_iso
from sos.routers import get_db

router = APIRouter(tags=["household"])

CATEGORIES = ("water", "food", "fuel", "medicine", "other")
Category = Literal["water", "food", "fuel", "medicine", "other"]
# litres of water, person-days of food, days of supply of medicine (UK guidance)
DEFAULT_PER_PERSON_DAY = {"water": 3.0, "food": 1.0, "medicine": 1.0}
COUNTED = ("water", "food", "medicine")     # categories the readiness score and the Stock/Now screens count in days


class PersonIn(BaseModel):
    name: str
    age: Optional[int] = None
    needs: str = ""
    medications: str = ""
    contacts: str = ""


class PersonPatch(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    needs: Optional[str] = None
    medications: Optional[str] = None
    contacts: Optional[str] = None


class StockIn(BaseModel):
    name: str
    category: Category
    quantity: float
    unit: str
    per_person_day: Optional[float] = None
    expires: Optional[str] = None
    notes: str = ""


class StockPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[Category] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    per_person_day: Optional[float] = None
    expires: Optional[str] = None
    notes: Optional[str] = None


def _person(r) -> dict:
    return {"id": r["id"], "name": r["name"], "age": r["age"], "needs": r["needs"] or "",
            "medications": r["medications"] or "", "contacts": r["contacts"] or "", "updated_at": r["updated_at"]}


def _get_person(conn, person_id: int):
    row = conn.execute("SELECT * FROM household WHERE id=?", (person_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return row


def people_count(conn) -> int:
    return max(1, conn.execute("SELECT COUNT(*) FROM household").fetchone()[0])


def days_left(quantity: float, per_person_day: Optional[float], people: int) -> Optional[float]:
    if not per_person_day or per_person_day <= 0:
        return None
    return round(quantity / (per_person_day * people), 1)


def _kit_title(content, kit_item) -> str | None:
    """The title of the kit a row came from, so the screen can say "From the Power and light kit" rather than
    guessing it from the slug. None when the row is not from a kit, or the kit has since left the box."""
    if not kit_item or content is None:
        return None
    kit = content.kit(str(kit_item).partition("/")[0])
    return kit.title if kit is not None else None


def is_expired(expires: Optional[str], today: Optional[date] = None) -> bool:
    if not expires:
        return False
    try:
        return date.fromisoformat(expires[:10]) < (today or date.today())
    except ValueError:
        return False


def _item(r, people: int, content=None) -> dict:
    expired = is_expired(r["expires"])
    dl = days_left(r["quantity"], r["per_person_day"], people)
    return {"id": r["id"], "name": r["name"], "category": r["category"], "quantity": r["quantity"], "unit": r["unit"],
            "per_person_day": r["per_person_day"], "expires": r["expires"], "notes": r["notes"] or "",
            "kit_item": r["kit_item"], "kit_title": _kit_title(content, r["kit_item"]),
            "updated_at": r["updated_at"], "expired": expired,
            "days_left": (0.0 if expired and dl is not None else dl)}


def stock_days_by_category(items: list[dict], people: int) -> dict[str, float]:
    """One figure per counted category: the raw (unrounded) days summed over rows that have a rate and are
    not expired, rounded once at the end — rounding each row first and then summing compounds the error."""
    out = {c: 0.0 for c in COUNTED}
    for i in items:
        rate = i["per_person_day"]
        if i["category"] in out and not i["expired"] and rate and rate > 0:
            out[i["category"]] += i["quantity"] / (rate * people)
    return {c: round(v, 1) for c, v in out.items()}


def _get_item(conn, item_id: int):
    row = conn.execute("SELECT * FROM stock WHERE id=?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return row


def _check_stock(name: str, quantity: float) -> None:
    if not name.strip():
        raise HTTPException(status_code=400, detail="Stock items need a name")
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")


@router.get("/household")
def list_household(conn=Depends(get_db)):
    return [_person(r) for r in conn.execute("SELECT * FROM household ORDER BY id")]


@router.post("/household")
def add_person(body: PersonIn, request: Request, conn=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="People need a name")
    cur = conn.execute("INSERT INTO household(name, age, needs, medications, contacts, updated_at) VALUES (?,?,?,?,?,?)",
                       (body.name.strip(), body.age, body.needs, body.medications, body.contacts, now_iso()))
    conn.commit()
    readiness.refresh(request, conn)
    return _person(_get_person(conn, cur.lastrowid))


@router.put("/household/{person_id}")
def update_person(person_id: int, body: PersonPatch, request: Request, conn=Depends(get_db)):
    current = _get_person(conn, person_id)
    merged = {k: (getattr(body, k) if getattr(body, k) is not None else current[k])
              for k in ("name", "age", "needs", "medications", "contacts")}
    if not (merged["name"] or "").strip():
        raise HTTPException(status_code=400, detail="People need a name")
    conn.execute("UPDATE household SET name=?, age=?, needs=?, medications=?, contacts=?, updated_at=? WHERE id=?",
                 (merged["name"].strip(), merged["age"], merged["needs"], merged["medications"], merged["contacts"],
                  now_iso(), person_id))
    conn.commit()
    readiness.refresh(request, conn)
    return _person(_get_person(conn, person_id))


@router.delete("/household/{person_id}")
def delete_person(person_id: int, request: Request, conn=Depends(get_db)):
    _get_person(conn, person_id)
    conn.execute("DELETE FROM household WHERE id=?", (person_id,))
    conn.commit()
    readiness.refresh(request, conn)
    return {"ok": True}


@router.get("/stock")
def list_stock(request: Request, conn=Depends(get_db)):
    people = people_count(conn)
    content = request.app.state.content
    items = [_item(r, people, content) for r in conn.execute("SELECT * FROM stock ORDER BY category, id")]
    return {"people": people, "days": stock_days_by_category(items, people), "items": items}


@router.post("/stock")
def add_stock(body: StockIn, request: Request, conn=Depends(get_db)):
    _check_stock(body.name, body.quantity)
    rate = body.per_person_day if body.per_person_day is not None else DEFAULT_PER_PERSON_DAY.get(body.category)
    cur = conn.execute(
        "INSERT INTO stock(name, category, quantity, unit, per_person_day, expires, notes, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (body.name.strip(), body.category, body.quantity, body.unit, rate, body.expires, body.notes, now_iso()))
    conn.commit()
    readiness.refresh(request, conn)
    return _item(_get_item(conn, cur.lastrowid), people_count(conn), request.app.state.content)


@router.put("/stock/{item_id}")
def update_stock(item_id: int, body: StockPatch, request: Request, conn=Depends(get_db)):
    current = _get_item(conn, item_id)
    merged = {k: (getattr(body, k) if getattr(body, k) is not None else current[k])
              for k in ("name", "category", "quantity", "unit", "per_person_day", "expires", "notes")}
    _check_stock(merged["name"] or "", merged["quantity"])
    conn.execute("UPDATE stock SET name=?, category=?, quantity=?, unit=?, per_person_day=?, expires=?, notes=?, updated_at=? WHERE id=?",
                 (merged["name"].strip(), merged["category"], merged["quantity"], merged["unit"], merged["per_person_day"],
                  merged["expires"], merged["notes"], now_iso(), item_id))
    conn.commit()
    readiness.refresh(request, conn)
    return _item(_get_item(conn, item_id), people_count(conn), request.app.state.content)


@router.delete("/stock/{item_id}")
def delete_stock(item_id: int, request: Request, conn=Depends(get_db)):
    _get_item(conn, item_id)
    conn.execute("DELETE FROM stock WHERE id=?", (item_id,))
    conn.commit()
    readiness.refresh(request, conn)
    return {"ok": True}
