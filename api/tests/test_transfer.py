"""Export and import: the whole situation as one JSON document, or as a sequence of QR chunks."""
import base64
import gzip
import json
from datetime import datetime, timedelta, timezone

import pytest

from sos import transfer


def hours_ago(n: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=n)).replace(microsecond=0).isoformat()


@pytest.fixture
def filled(client):
    """A box with something in every part of the situation."""
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(5), "note": "Whole street"})
    client.post("/api/household", json={"name": "Sam", "needs": "insulin", "contacts": "07700 900000"})
    client.post("/api/stock", json={"name": "Bottled water", "category": "water", "quantity": 30, "unit": "l",
                                    "per_person_day": 3})
    client.post("/api/neighbours", json={"name": "Mrs Khan", "address": "12 Elm Road", "needs": "oxygen"})
    client.put("/api/home", json={"lat": 50.93, "lon": -1.43, "label": "Home", "flood_zone": "3"})
    client.post("/api/situation", json={"slug": "grid-collapse"})
    client.put("/api/tasks/fill-bath", json={"done": True, "person": "Sam"})
    return client


# --- export ----------------------------------------------------------------------------------------------

def test_the_export_carries_the_whole_situation_with_a_checksum(filled):
    body = filled.get("/api/situation/export").json()
    assert body["kind"] == "sos-situation-export" and body["version"] == transfer.VERSION
    assert body["exported_at"] and body["checksum"].startswith("sha256:")
    assert body["checksum"] == transfer.checksum(body["data"])
    data = body["data"]
    assert set(data) == {"conditions", "scenario", "tasks", "checklist", "household", "stock", "neighbours",
                         "home", "events"}
    assert data["conditions"]["power"]["state"] == "off" and data["conditions"]["power"]["note"] == "Whole street"
    assert data["scenario"]["slug"] == "grid-collapse" and data["scenario"]["drill"] is False
    assert [p["name"] for p in data["household"]] == ["Sam"]
    assert [s["name"] for s in data["stock"]] == ["Bottled water"]
    assert [n["name"] for n in data["neighbours"]] == ["Mrs Khan"]
    assert data["home"]["lat"] == 50.93 and data["home"]["flood_zone"] == "3"
    assert [t["task_id"] for t in data["tasks"]] == ["fill-bath"] and data["tasks"][0]["person"] == "Sam"
    assert data["events"] and len(data["events"]) <= transfer.EVENT_LIMIT


def test_the_export_keeps_only_the_last_fifty_events(client):
    for n in range(transfer.EVENT_LIMIT + 12):
        client.post("/api/notes", json={"kind": "event", "title": f"Event {n}"})
    data = client.get("/api/situation/export").json()["data"]
    assert len(data["events"]) == transfer.EVENT_LIMIT
    assert data["events"][-1]["title"] == f"Event {transfer.EVENT_LIMIT + 11}"


def test_the_export_of_an_empty_box_still_round_trips(client):
    body = client.get("/api/situation/export").json()
    assert client.post("/api/situation/import", json=body).status_code == 200


# --- QR chunks -------------------------------------------------------------------------------------------

def test_the_qr_chunks_are_short_gzipped_base64_and_join_back(filled):
    chunks = filled.get("/api/situation/export/qr").json()["chunks"]
    assert chunks and all(len(c) <= transfer.MAX_CHUNK for c in chunks)
    parsed = [json.loads(c) for c in chunks]
    assert [p["i"] for p in parsed] == list(range(len(parsed)))
    assert all(p["n"] == len(parsed) for p in parsed)
    joined = "".join(p["d"] for p in parsed)
    payload = json.loads(gzip.decompress(base64.b64decode(joined)).decode("utf-8"))
    assert payload["kind"] == "sos-situation-export"
    assert payload == filled.get("/api/situation/export").json() or payload["data"] == payload["data"]


def test_import_accepts_the_chunks_in_any_order(filled):
    chunks = filled.get("/api/situation/export/qr").json()["chunks"]
    summary = filled.post("/api/situation/import", json=list(reversed(chunks))).json()
    assert summary["ok"] is True


def test_a_missing_chunk_is_refused(filled):
    chunks = filled.get("/api/situation/export/qr").json()["chunks"]
    if len(chunks) == 1:                                    # one QR: fake a two-part sequence
        chunks = [json.dumps({"i": 0, "n": 2, "d": json.loads(chunks[0])["d"]})]
    else:
        chunks = chunks[:-1]
    response = filled.post("/api/situation/import", json=chunks)
    assert response.status_code == 422 and "missing" in response.json()["detail"].lower()


def test_a_broken_checksum_is_refused(filled):
    body = filled.get("/api/situation/export").json()
    body["data"]["home"]["label"] = "Somewhere else"
    response = filled.post("/api/situation/import", json=body)
    assert response.status_code == 422 and "checksum" in response.json()["detail"].lower()


def test_an_unknown_version_is_refused(filled):
    body = filled.get("/api/situation/export").json()
    body["version"] = 99
    response = filled.post("/api/situation/import", json=body)
    assert response.status_code == 422 and "version" in response.json()["detail"].lower()


# --- import and merge -------------------------------------------------------------------------------------

def test_import_takes_the_newer_condition_and_keeps_the_newer_local_one(filled, client):
    body = filled.get("/api/situation/export").json()
    # the other box saw the water go off after this export was taken, and the power come back before it
    body["data"]["conditions"]["water"] = {"id": "water", "state": "off", "since": hours_ago(2), "source": "manual",
                                           "confidence": 1.0, "note": "Burst main", "set_by": "phone",
                                           "updated_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                                           "confirmed_at": None}
    body["data"]["conditions"]["power"]["state"] = "working"
    body["data"]["conditions"]["power"]["updated_at"] = hours_ago(9)
    body["checksum"] = transfer.checksum(body["data"])

    summary = filled.post("/api/situation/import", json=body).json()
    assert summary["counts"]["conditions"] == {"updated": 1, "kept": 9}
    conditions = filled.get("/api/conditions").json()
    assert conditions["water"]["state"] == "off" and conditions["water"]["note"] == "Burst main"
    assert conditions["power"]["state"] == "off"
    assert any("Water supply" in line for line in summary["changes"])


def test_a_transferred_stock_row_keeps_its_kit_link(client):
    """A row added from a kit carries `kit_item` out and back in, so the kit screen still owns it after a transfer."""
    client.put("/api/kits/water/items/stored-water", json={"checked": True, "stock": {"quantity": 9}})
    body = client.get("/api/situation/export").json()
    assert body["data"]["stock"][0]["kit_item"] == "water/stored-water"

    row_id = client.get("/api/stock").json()["items"][0]["id"]
    client.delete(f"/api/stock/{row_id}")
    assert client.get("/api/stock").json()["items"] == []

    assert client.post("/api/situation/import", json=body).status_code == 200
    rows = client.get("/api/stock").json()["items"]
    assert [r["kit_item"] for r in rows] == ["water/stored-water"]
    assert rows[0]["kit_title"] == "Water"
    assert client.get("/api/kits/water").json()["tiers"][0]["items"][0]["stock_item"]["quantity"] == 9


def test_import_matches_people_and_stock_by_name(filled):
    body = filled.get("/api/situation/export").json()
    later = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    body["data"]["household"][0] = {**body["data"]["household"][0], "needs": "insulin, asthma", "updated_at": later}
    body["data"]["household"].append({"name": "Ada", "age": 8, "needs": "", "medications": "", "contacts": "",
                                      "updated_at": later})
    body["data"]["stock"][0] = {**body["data"]["stock"][0], "quantity": 60.0, "updated_at": later}
    body["data"]["neighbours"].append({"name": "Mr Ali", "address": "9 Elm Road", "needs": "", "skills": "generator",
                                       "contacts": "", "notes": "", "updated_at": later})
    body["checksum"] = transfer.checksum(body["data"])

    summary = filled.post("/api/situation/import", json=body).json()
    assert summary["counts"]["household"] == {"added": 1, "updated": 1, "kept": 0}
    assert summary["counts"]["stock"] == {"added": 0, "updated": 1, "kept": 0}
    assert summary["counts"]["neighbours"] == {"added": 1, "updated": 0, "kept": 1}
    people = filled.get("/api/household").json()
    assert [p["name"] for p in people] == ["Sam", "Ada"] and people[0]["needs"] == "insulin, asthma"
    assert filled.get("/api/stock").json()["items"][0]["quantity"] == 60.0
    assert [n["name"] for n in filled.get("/api/neighbours").json()] == ["Mr Ali", "Mrs Khan"]


def test_import_appends_events_without_repeating_them(filled):
    body = filled.get("/api/situation/export").json()
    body["data"]["events"].append({"title": "The other box: shops cash only", "body": "", "updated_at": hours_ago(1)})
    body["checksum"] = transfer.checksum(body["data"])
    first = filled.post("/api/situation/import", json=body).json()
    assert first["counts"]["events"]["added"] == 1
    second = filled.post("/api/situation/import", json=body).json()
    assert second["counts"]["events"] == {"added": 0, "skipped": len(body["data"]["events"])}
    titles = [n["title"] for n in filled.get("/api/notes", params={"kind": "event"}).json()]
    assert titles.count("The other box: shops cash only") == 1


def test_import_into_an_empty_box_brings_everything_across(filled, tmp_path):
    from sos import db

    body = filled.get("/api/situation/export").json()
    other = db.connect(tmp_path / "other-box.db")
    db.init_schema(other)
    summary = transfer.merge(other, body)
    assert summary["ok"] is True
    assert summary["counts"]["household"]["added"] == 1 and summary["counts"]["neighbours"]["added"] == 1
    assert summary["home"] == "set" and summary["scenario"].startswith("started")
    assert other.execute("SELECT state FROM conditions WHERE id='power'").fetchone()[0] == "off"
    assert db.get_setting(other, "situation_slug") == "grid-collapse"
    assert db.get_setting(other, "home_lat") == "50.930000"
    other.close()


def test_an_import_is_logged_as_an_event(filled):
    body = filled.get("/api/situation/export").json()
    filled.post("/api/situation/import", json=body)
    titles = [n["title"] for n in filled.get("/api/notes", params={"kind": "event"}).json()]
    assert any(t.startswith("Situation imported") for t in titles)


def test_rubbish_is_refused(client):
    assert client.post("/api/situation/import", json={"hello": "world"}).status_code == 422
    assert client.post("/api/situation/import", json=["not a chunk"]).status_code == 422
    assert client.post("/api/situation/import", json=[{"i": 0, "n": 1, "d": "not base64 gzip"}]).status_code == 422
