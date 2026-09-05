"""Nearest facilities: the geometry, reading the overlays, and `GET /api/nearby`."""
import json
from pathlib import Path

import pytest

from sos import nearby

# Somewhere unambiguous to measure from: the middle of Southampton Common.
HOME = (50.9300, -1.4200)


def point(lon, lat, **props):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props}


def collection(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def write_overlay(root: Path, name: str, obj: dict) -> Path:
    path = root / "maps" / "overlays" / f"{name}.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


@pytest.fixture
def overlays(env):
    """A health, fuel and water overlay around the home, plus a far-away hospital to sort behind the near one."""
    write_overlay(env.core, "health", collection(
        point(-1.4350, 50.9340, amenity="hospital", name="Southampton General Hospital", phone="+44 23 8077 7222"),
        point(-1.3000, 50.9000, amenity="hospital", name="Far Cottage Hospital"),
        point(-1.4210, 50.9310, amenity="pharmacy", name="Common Road Pharmacy"),
        point(-1.4180, 50.9260, amenity="doctors", name="Highfield Surgery"),
        point(-1.4190, 50.9330, amenity="dentist", name="Not a surgery"),
    ))
    write_overlay(env.core, "fuel", collection(
        point(-1.4100, 50.9250, amenity="fuel", name="Portswood Filling Station"),
    ))
    write_overlay(env.core, "water", collection(
        point(-1.4500, 50.9500, man_made="water_works", name="Otterbourne Water Works", operator="Southern Water"),
        point(-1.4400, 50.9400, man_made="outfall"),
        {"type": "Feature", "properties": {"landuse": "reservoir", "name": "A reservoir"},
         "geometry": {"type": "Polygon", "coordinates": [[[-1.44, 50.94], [-1.43, 50.94], [-1.43, 50.95],
                                                          [-1.44, 50.95], [-1.44, 50.94]]]}},
    ))
    nearby._CACHE.clear()
    yield env
    nearby._CACHE.clear()


# --- the geometry ------------------------------------------------------------------------------------------

def test_haversine_matches_a_degree_of_latitude():
    metres = nearby.haversine_m(51.0, -1.0, 52.0, -1.0)
    assert 111_100 < metres < 111_300           # one degree of latitude is about 111.2 km
    assert nearby.haversine_m(51.0, -1.0, 51.0, -1.0) == 0.0


def test_bearing_and_compass_point_the_right_way():
    assert nearby.bearing_deg(51.0, -1.0, 52.0, -1.0) == pytest.approx(0.0, abs=0.1)
    assert nearby.bearing_deg(51.0, -1.0, 50.0, -1.0) == pytest.approx(180.0, abs=0.1)
    assert nearby.bearing_deg(51.0, -1.0, 51.0, 0.0) == pytest.approx(90.0, abs=0.5)
    assert nearby.compass(0) == "N" and nearby.compass(90) == "E" and nearby.compass(225) == "SW"
    assert nearby.compass(359) == "N" and nearby.compass(23) == "NNE"


def test_naismith_is_an_hour_per_five_kilometres():
    assert nearby.naismith_minutes(5000) == 60
    assert nearby.naismith_minutes(1000) == 12
    assert nearby.naismith_minutes(1000, ascent_m=100) == 22       # plus a minute per ten metres of climb
    assert nearby.naismith_minutes(0) == 0
    assert nearby.naismith_minutes(10) == 1                         # never rounds a real walk down to nothing


@pytest.mark.parametrize("geometry, expected", [
    ({"type": "Point", "coordinates": [-1.4, 50.9]}, (50.9, -1.4)),
    ({"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}, (0.8, 0.8)),
    ({"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]]}, (0.25, 0.5)),
    ({"type": "LineString", "coordinates": [[0, 0], [2, 2]]}, (1.0, 1.0)),
    ({"type": "GeometryCollection", "coordinates": []}, None),
    (None, None),
])
def test_representative_point(geometry, expected):
    got = nearby.representative_point(geometry)
    if expected is None:
        assert got is None
    else:
        assert got[0] == pytest.approx(expected[0]) and got[1] == pytest.approx(expected[1])


# --- reading the overlays -------------------------------------------------------------------------------------

def test_overlay_geojson_prefers_the_overlay_then_the_build_workspace(env, tmp_path):
    assert nearby.overlay_geojson(env, "health") is None
    work = tmp_path / "maps-src" / "overlays-work"
    work.mkdir(parents=True)
    (work / "health_raw.geojson").write_text(json.dumps(collection()))
    env.maps_src = tmp_path / "maps-src"
    assert nearby.overlay_geojson(env, "health") == work / "health_raw.geojson"
    (work / "health.geojson").write_text(json.dumps(collection()))
    assert nearby.overlay_geojson(env, "health") == work / "health.geojson"
    shipped = write_overlay(env.core, "health", collection())
    assert nearby.overlay_geojson(env, "health") == shipped


def test_load_points_trims_the_tags_and_caches_by_mtime(env):
    path = write_overlay(env.core, "fuel", collection(point(-1.41, 50.92, amenity="fuel", name="A", ref="ignored")))
    nearby._CACHE.clear()
    points = nearby.load_points(path)
    assert len(points) == 1 and points[0].props == {"amenity": "fuel", "name": "A"}
    assert nearby.load_points(path) is points        # unchanged file, same object


# --- the answer --------------------------------------------------------------------------------------------------

def test_nearest_finds_each_facility_with_distance_bearing_and_walking_time(overlays):
    answer = nearby.nearest(overlays, *HOME)
    by_id = {f["id"]: f for f in answer["facilities"]}
    assert [f["id"] for f in answer["facilities"]] == [
        "emergency-department", "pharmacy", "gp", "fuel", "water-works", "fire-station", "rest-centre"]

    ed = by_id["emergency-department"]["nearest"]
    assert ed["name"] == "Southampton General Hospital"
    assert 1000 < ed["distance_m"] < 1200 and ed["compass"] in ("NW", "WNW", "NNW")
    assert ed["walk_minutes"] == nearby.naismith_minutes(ed["distance_m"])
    assert ed["properties"]["phone"] == "+44 23 8077 7222"
    assert by_id["emergency-department"]["also"][0]["name"] == "Far Cottage Hospital"

    assert by_id["pharmacy"]["nearest"]["name"] == "Common Road Pharmacy"
    assert by_id["gp"]["nearest"]["name"] == "Highfield Surgery"       # the dentist is not a GP surgery
    assert by_id["fuel"]["nearest"]["name"] == "Portswood Filling Station"
    assert by_id["water-works"]["nearest"]["name"] == "Otterbourne Water Works"   # not the outfall or the reservoir
    assert all(f["found"] for f in answer["facilities"] if f["id"] != "fire-station" and f["id"] != "rest-centre")
    assert "Naismith" in answer["method"]


def test_fire_stations_and_rest_centres_say_they_are_missing(overlays):
    answer = nearby.nearest(overlays, *HOME, ids=["fire-station", "rest-centre"])
    for item in answer["facilities"]:
        assert item["found"] is False and item["nearest"] is None
        assert item["why"] and item["note"]
    assert "fire_station" in answer["facilities"][0]["note"]


def test_a_pmtiles_only_overlay_explains_itself(env):
    """No GeoJSON for health anywhere: the answer says why rather than inventing a hospital."""
    nearby._CACHE.clear()
    answer = nearby.nearest(env, *HOME, ids=["pharmacy"])
    item = answer["facilities"][0]
    assert item["found"] is False and "SOS_MAPS_SRC" in item["why"] and "health" in item["why"]


def test_summary_is_one_line_per_facility_found(overlays):
    rows = nearby.summary(nearby.nearest(overlays, *HOME))
    assert [r["id"] for r in rows] == ["emergency-department", "pharmacy", "gp", "fuel", "water-works"]
    assert set(rows[0]) == {"id", "title", "name", "lat", "lon", "distance_m", "bearing_deg", "compass", "walk_minutes"}


# --- the endpoint ---------------------------------------------------------------------------------------------------

def test_nearby_endpoint(overlays, client):
    answer = client.get("/api/nearby", params={"lat": HOME[0], "lon": HOME[1]}).json()
    assert answer["lat"] == pytest.approx(HOME[0]) and answer["lon"] == pytest.approx(HOME[1])
    by_id = {f["id"]: f for f in answer["facilities"]}
    assert by_id["pharmacy"]["nearest"]["name"] == "Common Road Pharmacy"


def test_nearby_defaults_to_the_home_and_404s_without_one(overlays, client):
    assert client.get("/api/nearby").status_code == 404
    client.put("/api/home", json={"lat": HOME[0], "lon": HOME[1], "label": "Home"})
    answer = client.get("/api/nearby").json()
    assert answer["lat"] == pytest.approx(HOME[0])
    assert client.get("/api/nearby", params={"lat": 991, "lon": 0}).status_code == 422


def test_the_view_carries_the_homes_nearest_facilities(overlays, client):
    assert "nearby" not in client.get("/api/situation/view").json()["meta"]["home"]
    client.put("/api/home", json={"lat": HOME[0], "lon": HOME[1], "label": "Home"})
    home = client.get("/api/situation/view").json()["meta"]["home"]
    assert [r["id"] for r in home["nearby"]] == ["emergency-department", "pharmacy", "gp", "fuel", "water-works"]
    assert home["nearby"][0]["name"] == "Southampton General Hospital"
    assert home["nearby"][0]["walk_minutes"] >= 1
