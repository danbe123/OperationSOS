"""Map configuration derived from manifest items of category `maps` and from overlay items.
Conventions plan 04 must follow: base map item ids are `uk-ie` (osm) and `os-zoomstack` (os); terrain items are
`contours` and `hillshade`; phone packs are items of kind `mwm`/`apk` plus a `dir` item `packs` whose index is
`/maps/packs/index.html`; styles live at `/maps/styles/<base>-<theme>.json`."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends

from sos.db import get_setting
from sos.routers import get_db

router = APIRouter(tags=["map"])
BASES = [("osm", "OpenStreetMap", "uk-ie"), ("os", "Ordnance Survey", "os-zoomstack")]
THEMES = ("field", "mono")


def _maps_url(row) -> str:
    dest = row["dest"]
    return "/maps/" + (dest[5:] if dest.startswith("maps/") else dest)


def overlays_list(conn) -> list[dict]:
    scenarios_on = json.loads(get_setting(conn, "overlay_scenarios", "{}") or "{}")
    out = []
    indexes = {}
    for row in conn.execute("SELECT * FROM library_items WHERE overlay_json IS NOT NULL ORDER BY priority, id"):
        o = json.loads(row["overlay_json"])
        available = bool(row["available"])
        built = {}
        if available and row["local_path"]:
            index_path = Path(row["local_path"]).parent / "index.json"
            if index_path not in indexes:
                try:
                    indexes[index_path] = json.loads(index_path.read_text())
                except (OSError, ValueError):
                    indexes[index_path] = {}
            built = indexes[index_path].get(row["id"], {})
        out.append({
            "id": o["id"], "title": row["title"], "kind": o["kind"], "layer_id": o.get("layer_id"),
            "url": _maps_url(row) if available and o["kind"] != "style-layer" else None,
            "default_on": bool(o.get("default_on")), "scenarios_on": scenarios_on.get(o["id"], []),
            "coverage": built.get("coverage", o.get("coverage", [])), "color": o.get("color", "#ffffff"), "icon": o.get("icon"), "available": available,
        })
    return out


@router.get("/map/config")
def map_config(conn=Depends(get_db)):
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items WHERE category='maps'")}

    def available(item_id: str) -> bool:
        return bool(rows.get(item_id) and rows[item_id]["available"])

    def index(item_id: str) -> dict:
        row = rows.get(item_id)
        if not row or not row["available"] or not row["local_path"]:
            return {}
        try:
            return json.loads((Path(row["local_path"]) / "index.json").read_text())
        except (OSError, ValueError):
            return {}

    styles = index("styles")
    bases = [{"id": bid, "title": title, "styles": {t: styles.get(bid, {}).get(t, f"/maps/styles/{bid}-{t}.json") for t in THEMES}, "available": available(item)}
             for bid, title, item in BASES]
    terrain = {name: (_maps_url(rows[name]) if available(name) else None) for name in ("contours", "hillshade")}
    packs = [{"title": r["title"], "url": _maps_url(r), "size_bytes": r["size_bytes"] or 0}
             for r in rows.values() if r["kind"] in ("mwm", "apk") and r["available"]]
    for pack in index("packs").get("packs", []):
        packs.append({"title": pack["title"], "url": pack["url"], "size_bytes": pack["size_bytes"]})
    return {"bases": bases, "terrain": terrain, "overlays": overlays_list(conn), "packs": packs,
            "packs_index_url": "/maps/packs/index.html" if available("packs") else None}


@router.get("/map/overlays")
def map_overlays(conn=Depends(get_db)):
    return overlays_list(conn)
