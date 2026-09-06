"""Nearest facilities: the six or seven places you want to be able to walk to when everything else has stopped.

The answer comes out of the map overlays the box already carries (`maps/overlays/*.geojson`), so it works with no
network, no routing engine and no index to keep in step. Distance is the great-circle line, the bearing is the
compass direction to walk in, and the time is Naismith's rule (an hour per five kilometres, plus a minute per ten
metres of climb) with the honest warning that it is measured as the crow flies.

Overlays that the map build turned into PMTiles (health, water) have no GeoJSON on the box: `overlay_geojson`
falls back to the source GeoJSON the build kept in its workspace when `SOS_MAPS_SRC` points at it, and the
endpoint says plainly when a facility cannot be answered rather than guessing."""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from sos.config import Settings

EARTH_R = 6371008.8                     # mean Earth radius, metres
NAISMITH_KMH = 5.0                      # Naismith's rule: one hour per five kilometres on the flat
NAISMITH_MIN_PER_M_ASCENT = 0.1         # plus one minute for every ten metres of climb
COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
# Properties worth carrying back to the screen; the rest of the OSM tags are dropped when the file is read.
KEEP = ("name", "amenity", "man_made", "emergency", "operator", "phone", "opening_hours", "healthcare", "network")
ROAD_KINDS = {"named-road", "postcode"}
MAX_RESULTS = 3


# --- geometry ------------------------------------------------------------------------------------------------

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The initial great-circle bearing from the first point to the second, 0 to 360 clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def compass(deg: float) -> str:
    return COMPASS[int((deg % 360.0) / 22.5 + 0.5) % 16]


def naismith_minutes(distance_m: float, ascent_m: float = 0.0) -> int:
    """Naismith's rule, rounded up to the minute: five kilometres an hour plus a minute per ten metres of climb."""
    minutes = (distance_m / 1000.0) / NAISMITH_KMH * 60.0 + max(0.0, ascent_m) * NAISMITH_MIN_PER_M_ASCENT
    return max(1, math.ceil(minutes)) if distance_m > 0 else 0


# --- reading the overlays -------------------------------------------------------------------------------------

def representative_point(geometry: dict | None) -> Optional[tuple[float, float]]:
    """(lat, lon) for any GeoJSON geometry: the point itself, or the mean of the outer ring or line."""
    if not geometry:
        return None
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if not coords:
        return None
    try:
        if kind == "Point":
            return float(coords[1]), float(coords[0])
        if kind == "MultiPoint" or kind == "LineString":
            ring = coords
        elif kind == "Polygon" or kind == "MultiLineString":
            ring = coords[0]
        elif kind == "MultiPolygon":
            ring = coords[0][0]
        else:
            return None
        lons = [float(c[0]) for c in ring]
        lats = [float(c[1]) for c in ring]
    except (TypeError, ValueError, IndexError):
        return None
    if not lats:
        return None
    return sum(lats) / len(lats), sum(lons) / len(lons)


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float
    props: dict


def overlay_geojson(settings: Settings, overlay_id: str) -> Optional[Path]:
    """Where an overlay's features can be read as GeoJSON, or None when only tiles were kept.

    In order: the overlay itself when the build wrote GeoJSON, a `<id>.source.geojson` kept beside the tiles,
    and finally the build workspace named by `SOS_MAPS_SRC` (`overlays-work/<id>.geojson`, then `<id>_raw.geojson`,
    which is what `sos build-maps` leaves behind for the overlays it turned into PMTiles)."""
    overlays = Path(settings.core) / "maps" / "overlays"
    candidates = [overlays / f"{overlay_id}.geojson", overlays / f"{overlay_id}.source.geojson"]
    if settings.maps_src:
        work = Path(settings.maps_src) / "overlays-work"
        candidates += [work / f"{overlay_id}.geojson", work / f"{overlay_id}_raw.geojson"]
    return next((p for p in candidates if p.is_file()), None)


def _trim(props: dict | None) -> dict:
    return {k: v for k, v in (props or {}).items() if k in KEEP and v not in (None, "")}


def load_points(path: Path) -> tuple[Point, ...]:
    """Every feature in a GeoJSON file as one representative point, cached by the file's mtime and size."""
    path = Path(path)
    st = path.stat()
    signature = (st.st_mtime, st.st_size)
    cached = _CACHE.get(path)
    if cached is not None and cached[0] == signature:
        return cached[1]
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    points: list[Point] = []
    for feature in obj.get("features") or []:
        at = representative_point(feature.get("geometry"))
        if at is not None:
            points.append(Point(at[0], at[1], _trim(feature.get("properties"))))
    out = tuple(points)
    _CACHE[path] = (signature, out)
    return out


_CACHE: dict[Path, tuple[tuple, tuple[Point, ...]]] = {}


# --- what we look for -------------------------------------------------------------------------------------------

def _is(props: dict, key: str, *values: str) -> bool:
    return str(props.get(key, "")).lower() in values


def _emergency_department(props: dict) -> bool:
    # The map build's POI export keeps amenity but not `emergency`, so on a box built before that tag is carried
    # every hospital qualifies. Where the tag is present it is honoured, and emergency=no is excluded.
    return _is(props, "amenity", "hospital") and not _is(props, "emergency", "no")


@dataclass(frozen=True)
class Facility:
    id: str
    title: str
    overlays: tuple[str, ...]
    match: Callable[[dict], bool]
    places: tuple[str, ...] = ()        # words to look for in the places index when no overlay carries it
    note: str = ""


FACILITIES: tuple[Facility, ...] = (
    Facility("emergency-department", "Emergency department", ("health",), _emergency_department,
             note="Hospitals from OpenStreetMap. The overlay does not carry the emergency=yes tag, so a small "
                  "hospital without an A&E can appear: ring ahead if the phones are up."),
    Facility("pharmacy", "Pharmacy", ("health",), lambda p: _is(p, "amenity", "pharmacy")),
    Facility("gp", "GP surgery", ("health",), lambda p: _is(p, "amenity", "doctors")),
    Facility("fuel", "Fuel station", ("fuel",), lambda p: _is(p, "amenity", "fuel")),
    Facility("water-works", "Water treatment works", ("water",),
             lambda p: _is(p, "man_made", "water_works", "water_treatment", "wastewater_plant")),
    Facility("fire-station", "Fire station", ("emergency-services", "health"),
             lambda p: _is(p, "amenity", "fire_station"), places=("fire station",),
             note="No overlay carries fire stations yet: the map build filters amenity=hospital, pharmacy and "
                  "doctors only. Add amenity=fire_station to the health overlay's filters to fill this in."),
    Facility("rest-centre", "Rest centre", ("emergency-services", "health"),
             lambda p: _is(p, "amenity", "shelter", "community_centre") or _is(p, "emergency", "assembly_point"),
             places=("rest centre", "community centre"),
             note="Rest centres are opened by the council on the day and are not mapped in advance; the nearest "
                  "community centre or hall is the usual building. Ask on local radio which one is open."),
)
BY_ID = {f.id: f for f in FACILITIES}


# --- the answer ---------------------------------------------------------------------------------------------------

def _entry(lat: float, lon: float, point: Point, source: str) -> dict:
    distance = haversine_m(lat, lon, point.lat, point.lon)
    bearing = bearing_deg(lat, lon, point.lat, point.lon)
    props = dict(point.props)
    return {"name": props.pop("name", None) or "Unnamed", "lat": round(point.lat, 6), "lon": round(point.lon, 6),
            "distance_m": int(round(distance)), "bearing_deg": int(round(bearing)), "compass": compass(bearing),
            "walk_minutes": naismith_minutes(distance), "source": source, "properties": props}


def _from_places(conn: Optional[sqlite3.Connection], words: Iterable[str], lat: float, lon: float) -> list[dict]:
    """A best-effort look in the places index for facilities no overlay carries. Roads and postcodes are ignored,
    so a 'Fire Station Lane' never masquerades as a fire station."""
    if conn is None:
        return []
    from sos import places as places_mod

    found: list[dict] = []
    for phrase in words:
        for row in places_mod.query_places(conn, phrase, limit=25):
            if row["kind"] in ROAD_KINDS or phrase not in row["name"].lower():
                continue
            found.append(_entry(lat, lon, Point(row["lat"], row["lon"], {"name": row["name"]}), "places"))
    found.sort(key=lambda r: r["distance_m"])
    return found


def facility_answer(settings: Settings, facility: Facility, lat: float, lon: float,
                    conn: Optional[sqlite3.Connection] = None) -> dict:
    candidates: list[dict] = []
    searched: list[str] = []
    missing: list[str] = []
    for overlay_id in facility.overlays:
        path = overlay_geojson(settings, overlay_id)
        if path is None:
            missing.append(overlay_id)
            continue
        searched.append(overlay_id)
        for point in load_points(path):
            if facility.match(point.props):
                candidates.append(_entry(lat, lon, point, f"overlay:{overlay_id}"))
    if not candidates and facility.places:
        candidates = _from_places(conn, facility.places, lat, lon)
        if candidates:
            searched.append("places")
    candidates.sort(key=lambda r: (r["distance_m"], r["name"]))
    # a hospital mapped as several buildings is one place to a household: keep the nearest of each name
    seen: set[str] = set()
    candidates = [c for c in candidates if not ((c["name"] or "").lower() in seen or seen.add((c["name"] or "").lower()))]
    out: dict = {"id": facility.id, "title": facility.title, "found": bool(candidates),
                 "nearest": candidates[0] if candidates else None, "also": candidates[1:MAX_RESULTS],
                 "searched": searched, "note": facility.note or None}
    if not candidates:
        if missing and not searched:
            out["why"] = (f"No searchable copy of the {', '.join(missing)} overlay on this box. "
                          "Overlays kept only as PMTiles need the build's source GeoJSON: point SOS_MAPS_SRC at "
                          "the map build workspace.")
        else:
            out["why"] = f"Nothing matching in {', '.join(searched) or 'any overlay'}."
    return out


def nearest(settings: Settings, lat: float, lon: float, conn: Optional[sqlite3.Connection] = None,
            ids: Iterable[str] | None = None) -> dict:
    """Every facility in FACILITIES (or the ids asked for), nearest first, with distance, bearing and walking time."""
    wanted = [BY_ID[i] for i in ids if i in BY_ID] if ids is not None else list(FACILITIES)
    return {"lat": round(float(lat), 6), "lon": round(float(lon), 6),
            "method": "Straight-line distance and bearing; walking time by Naismith's rule (5 km/h). "
                      "Roads and paths will be longer.",
            "facilities": [facility_answer(settings, f, float(lat), float(lon), conn) for f in wanted]}


def summary(answer: dict) -> list[dict]:
    """The short form the View carries in `meta.home.nearby`: one line per facility that was found."""
    out = []
    for item in answer["facilities"]:
        near = item["nearest"]
        if near is None:
            continue
        out.append({"id": item["id"], "title": item["title"], "name": near["name"], "lat": near["lat"],
                    "lon": near["lon"], "distance_m": near["distance_m"], "bearing_deg": near["bearing_deg"],
                    "compass": near["compass"], "walk_minutes": near["walk_minutes"]})
    return out
