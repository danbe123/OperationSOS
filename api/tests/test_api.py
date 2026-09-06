import shutil
import sys
import time
from pathlib import Path

import httpx
import respx

from sos import db, places, system

FX = Path(__file__).parent / "fixtures"
WIKI = "wikipedia_en_100_mini_2026-01"
KIWIX = "http://kiwix.test/kiwix"


def _install_zims(env):
    for n in (WIKI, "sos-test-noindex"):
        shutil.copy(FX / "library" / f"{n}.zim", env.core / "zim" / f"{n}.zim")


def _index_playbook(env):
    """Seed the one fts_docs row `sos index` writes for the grid-collapse playbook.

    Authored content is indexed by `sos.sync.index_content`, which the CLI task adds; the API only
    reads fts_docs, so the search test seeds the row it expects to find.
    """
    conn = db.connect(env.db_path)
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("National grid collapse", "Fill every bottle and the bath with water before the pumps stop.",
         "grid-collapse", "playbook", "playbooks", "grid-collapse", None, "/s/grid-collapse"),
    )
    conn.commit()
    conn.close()


def test_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["dev"] is True and body["version"] == "0.1.0" and body["pin_required"] is False
    assert body["hotspot"]["ip"] == "10.42.0.1" and body["ai"]["state"] == "off"


def test_library_and_rescan(client, env):
    r = client.get("/api/library")
    assert r.status_code == 200
    wiki = next(i for c in r.json()["categories"] for i in c["items"] if i["id"] == WIKI)
    assert wiki["available"] is False and wiki["url"] is None
    _install_zims(env)
    r = client.post("/api/system/rescan")
    assert r.status_code == 200 and r.json() == {"items": 25, "available": 2}
    r = client.get(f"/api/library/{WIKI}")
    assert r.status_code == 200
    assert r.json()["available"] is True and r.json()["url"] == f"/read/{WIKI}/" and r.json()["drive_label"] == "Core"
    ext = client.get("/api/library/sos-ext-missing").json()
    assert ext["drive_label"] == "On external drive (not connected)" and ext["available"] is False
    assert client.get("/api/library/nope").status_code == 404
    assert client.get("/api/library/nope").json() == {"detail": "Item not found"}


@respx.mock(base_url=KIWIX)
def test_search_and_suggest(respx_mock, client, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "suggest.json").read_text()))
    _install_zims(env)
    client.post("/api/system/rescan")
    _index_playbook(env)
    r = client.get("/api/search", params={"q": "water"})
    assert r.status_code == 200
    body = r.json()
    assert body["q"] == "water" and body["partial"] is False
    assert any(x["kind"] == "article" and x["url"] == f"/read/{WIKI}/Precipitation" for x in body["results"])
    assert any(x["kind"] == "playbook" for x in body["results"])
    r = client.get("/api/search", params={"q": "water", "sources": "playbooks", "limit": 1})
    assert len(r.json()["results"]) == 1 and r.json()["results"][0]["source"] == "playbooks"
    r = client.get("/api/suggest", params={"q": "wat"})
    assert r.status_code == 200 and 1 <= len(r.json()) <= 10
    assert any(s["url"] == f"/read/{WIKI}/Water" for s in r.json())
    assert client.get("/api/search").json()["results"] == []


def test_playbooks_list_and_detail(client):
    r = client.get("/api/playbooks")
    assert r.status_code == 200
    assert r.json() == [{"slug": "grid-collapse", "title": "National grid collapse", "icon": "bolt",
                         "summary": "A weeks-long blackout with water pumps and comms down.", "order": 4}]
    r = client.get("/api/playbooks/grid-collapse")
    assert r.status_code == 200
    pb = r.json()
    assert [s["id"] for s in pb["sections"]] == ["right-now", "first-72-hours", "first-month", "long-term", "uk-specifics", "go-deeper"]
    assert [c["id"] for c in pb["checklist"]] == ["fill-every-bottle-and-the-bath", "cooker-off", "check-on-neighbours",
                                                  "water/fill-clean-containers", "water/label-treated"]
    assert all(c["checked"] is False and c["updated_at"] is None for c in pb["checklist"])
    assert pb["modules"][0]["slug"] == "water" and pb["overlays"] == ["health", "water"] and pb["reviewed"] == "2026-09-01"
    assert pb["sources"][1] == {"title": "Test PDF", "doc": "sos-test-pdf", "as_at": "2026-09"}
    assert client.get("/api/playbooks/nope").status_code == 404


def test_checklist_put_and_reset(client):
    r = client.put("/api/playbooks/grid-collapse/checklist/cooker-off", json={"checked": True})
    assert r.status_code == 200
    items = {c["id"]: c for c in r.json()}
    assert items["cooker-off"]["checked"] is True and items["cooker-off"]["updated_at"] is not None
    assert items["check-on-neighbours"]["checked"] is False
    r = client.put("/api/playbooks/grid-collapse/checklist/water/label-treated", json={"checked": True})
    assert {c["id"] for c in r.json() if c["checked"]} == {"cooker-off", "water/label-treated"}
    r = client.put("/api/playbooks/grid-collapse/checklist/cooker-off", json={"checked": False})
    assert {c["id"] for c in r.json() if c["checked"]} == {"water/label-treated"}
    assert client.put("/api/playbooks/grid-collapse/checklist/nope", json={"checked": True}).status_code == 404
    assert client.put("/api/playbooks/nope/checklist/cooker-off", json={"checked": True}).status_code == 404
    r = client.delete("/api/playbooks/grid-collapse/checklist")
    assert r.status_code == 200 and not any(c["checked"] for c in r.json()) and len(r.json()) == 5


def test_modules_cards_pages(client):
    r = client.get("/api/modules/water")
    assert r.status_code == 200 and set(r.json()) == {"slug", "title", "html"}
    assert 'data-item-id="water/label-treated"' in r.json()["html"]
    assert client.get("/api/modules/nope").status_code == 404
    r = client.get("/api/cards")
    assert r.status_code == 200 and r.json()[0]["slug"] == "bleeding" and "<ol>" in r.json()[0]["html"]
    assert set(r.json()[0]) == {"slug", "title", "icon", "order", "summary", "html"}
    assert client.get("/api/cards/bleeding").json()["title"] == "Severe bleeding"
    assert client.get("/api/cards/nope").status_code == 404
    r = client.get("/api/pages")
    assert r.json() == [{"slug": "pmr446", "title": "PMR446 radio channels", "icon": "radio", "order": 1, "category": "comms", "summary": "The 16 licence-free UK walkie-talkie channels."}]
    page = client.get("/api/pages/pmr446").json()
    assert set(page) == {"slug", "title", "icon", "order", "html", "category"} and "<table>" in page["html"]
    assert client.get("/api/pages/nope").status_code == 404


def test_map_config_and_overlays(client, env):
    (env.core / "maps" / "overlays").mkdir()
    (env.core / "maps" / "test.pmtiles").write_bytes(b"PMTiles")
    (env.core / "maps" / "overlays" / "health.geojson").write_text('{"type":"FeatureCollection","features":[]}')
    conn = db.connect(env.db_path)
    db.set_setting(conn, "overlay_scenarios", '{"health": ["grid-collapse", "pandemic"]}')
    conn.close()
    client.post("/api/system/rescan")
    cfg = client.get("/api/map/config").json()
    assert [b["id"] for b in cfg["bases"]] == ["osm", "os"]
    osm = cfg["bases"][0]
    assert osm["available"] is True and osm["styles"] == {"vault": "/maps/styles/osm-vault.json", "field": "/maps/styles/osm-field.json",
                                                          "blackout": "/maps/styles/osm-blackout.json"}
    assert cfg["bases"][1]["available"] is False
    assert cfg["terrain"] == {"contours": None, "hillshade": None}
    assert cfg["packs"] == [] and cfg["packs_index_url"] is None
    overlays = {o["id"]: o for o in cfg["overlays"]}
    assert overlays["health"]["available"] is True and overlays["health"]["url"] == "/maps/overlays/health.geojson"
    assert overlays["health"]["scenarios_on"] == ["grid-collapse", "pandemic"] and overlays["health"]["color"] == "#d62728"
    assert overlays["nuclear-sites"]["available"] is False and overlays["nuclear-sites"]["url"] is None
    assert overlays["water"]["kind"] == "geojson" and overlays["water"]["layer_id"] is None
    assert set(overlays["health"]) == {"id", "title", "kind", "layer_id", "url", "default_on", "scenarios_on", "coverage", "color", "icon", "available"}
    assert client.get("/api/map/overlays").json() == cfg["overlays"]


def test_places_endpoint(client, env):
    conn = db.connect(env.db_path)
    places.import_places(conn, FX / "places.csv")
    conn.close()
    assert client.get("/api/places", params={"q": "ox"}).json() == []
    r = client.get("/api/places", params={"q": "oxf"})
    assert r.json()[0]["name"] == "Oxford" and set(r.json()[0]) == {"name", "kind", "lat", "lon", "region", "postcode"}
    assert len(client.get("/api/places", params={"q": "test hamlet", "limit": 100}).json()) == 25
    assert len(client.get("/api/places", params={"q": "test hamlet"}).json()) == 10


def test_notes_crud(client):
    r = client.post("/api/notes", json={"title": "Fuel", "body": "Two jerry cans in the shed"})
    assert r.status_code == 200
    note = r.json()
    assert note["kind"] == "note" and note["id"] == 1 and note["lat"] is None and note["updated_at"]
    assert client.post("/api/notes", json={"kind": "pin", "title": "Well"}).status_code == 400
    pin = client.post("/api/notes", json={"kind": "pin", "title": "Well", "body": "", "lat": 51.75, "lon": -1.25}).json()
    assert pin["kind"] == "pin" and pin["lat"] == 51.75
    assert [n["id"] for n in client.get("/api/notes").json()] == [1, 2]
    assert [n["id"] for n in client.get("/api/notes", params={"kind": "pin"}).json()] == [2]
    r = client.put("/api/notes/1", json={"body": "Three jerry cans"})
    assert r.json()["body"] == "Three jerry cans" and r.json()["title"] == "Fuel"
    assert client.put("/api/notes/99", json={"body": "x"}).status_code == 404
    assert client.delete("/api/notes/1").json() == {"ok": True}
    assert client.delete("/api/notes/1").status_code == 404
    assert [n["id"] for n in client.get("/api/notes").json()] == [2]


def test_ai_is_off_until_enabled(client):
    assert client.get("/api/ai/status").json() == {"state": "off", "model": None, "message": None}
    response = client.post("/api/ai/ask", json={"question": "Where is water?", "history": []})
    assert response.status_code == 200
    assert '"code": "unavailable"' in response.text


def test_localhost_only_endpoints(client, remote_client, monkeypatch):
    assert remote_client.post("/api/kiosk/backlight", json={"level": 50}).status_code == 403
    assert remote_client.post("/api/kiosk/idle", json={"state": "idle"}).status_code == 403
    assert remote_client.post("/api/system/rescan").status_code == 403
    assert remote_client.post("/api/system/backlight", json={"level": 50}).status_code == 200
    r = client.post("/api/kiosk/backlight", json={"level": 50})
    assert r.status_code == 200 and r.json() == {"level": 50}
    assert client.post("/api/kiosk/backlight", json={"level": 0}).json() == {"level": 10}
    assert client.post("/api/kiosk/backlight", json={"level": 101}).status_code == 422
    assert client.post("/api/kiosk/idle", json={"state": "idle"}).json() == {"ok": True}
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "3"
    assert client.post("/api/kiosk/idle", json={"state": "active"}).json() == {"ok": True}
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "16"
    monkeypatch.setattr(system, "backlight_device", lambda settings: None)
    assert client.post("/api/kiosk/backlight", json={"level": 50}).status_code == 501


def test_pin_gating_suite(client, app):
    # open when no PIN is set
    assert client.post("/api/system/power-mode", json={"mode": "low"}).status_code == 200
    assert client.post("/api/system/pin", json={"pin": "1234"}).status_code == 401
    # set the first PIN (no token needed while none is set)
    assert client.post("/api/system/pin/change", json={"pin": "1234"}).json() == {"ok": True}
    assert client.get("/api/status").json()["pin_required"] is True
    # gated endpoints now need a token
    for path, body in (("/api/system/power-mode", {"mode": "normal"}), ("/api/system/eth-mode", {"mode": "direct"}),
                       ("/api/system/hotspot", {"ssid": "X"}), ("/api/system/update", {"tiers": ["core"]}),
                       ("/api/system/pin/change", {"pin": "9999"})):
        r = client.post(path, json=body)
        assert r.status_code == 401 and r.json() == {"detail": "PIN required"}, path
    # wrong PIN is 401 and the sixth attempt in a minute is 429
    for _ in range(5):
        assert client.post("/api/system/pin", json={"pin": "0000"}).status_code == 401
    assert client.post("/api/system/pin", json={"pin": "1234"}).status_code == 429
    app.state.pin_limiter = system.RateLimiter()
    r = client.post("/api/system/pin", json={"pin": "1234"})
    assert r.status_code == 200 and r.json()["expires_in"] == 600
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers=headers).status_code == 200
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers={"Authorization": "Bearer nope"}).status_code == 401
    # expiry
    app.state.tokens.clock = lambda: time.monotonic() + 601
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers=headers).status_code == 401
    app.state.tokens.clock = time.monotonic
    token = client.post("/api/system/pin", json={"pin": "1234"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/system/pin/change", json={"pin": "12"}, headers=headers).status_code == 400
    assert client.post("/api/system/pin/change", json={"pin": "5678"}, headers=headers).json() == {"ok": True}
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers=headers).status_code == 401
    assert client.post("/api/system/pin", json={"pin": "5678"}).status_code == 200


def test_first_pin_claim_is_localhost_only(client, remote_client):
    # The hotspot ships open (no WPA2), so before any PIN is set, a remote client must not be able to
    # claim it -- only the box itself (localhost) may.
    r = remote_client.post("/api/system/pin/change", json={"pin": "1234"})
    assert r.status_code == 403 and r.json() == {"detail": "Only allowed from the box itself"}
    assert client.get("/api/status").json()["pin_required"] is False  # the rejected claim did not stick
    assert client.post("/api/system/pin/change", json={"pin": "1234"}).json() == {"ok": True}
    assert client.get("/api/status").json()["pin_required"] is True
    # once a PIN exists, remote clients go back to the normal bearer-token path (401, not 403)
    r = remote_client.post("/api/system/pin/change", json={"pin": "5678"})
    assert r.status_code == 401 and r.json() == {"detail": "PIN required"}


def test_unhandled_exception_returns_json_500(app, monkeypatch):
    # Any exception the plan's error contract doesn't already name (ValueError -> 400, validation -> 422)
    # must still come back as { "detail": string } JSON, not Starlette's default text/plain 500.
    from fastapi.testclient import TestClient

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(system, "set_power_mode", boom)
    # raise_server_exceptions=False: TestClient otherwise re-raises the original exception for debugging
    # even when the app's own exception_handler already produced a response -- we want that response here.
    with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
        r = c.post("/api/system/power-mode", json={"mode": "low"})
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"detail": "Internal error"}


def test_system_settings_hotspot_eth_and_update(client, app):
    r = client.post("/api/system/settings", json={"default_theme": "field", "thermal_ai_off_c": 70})
    assert r.status_code == 200 and r.json()["default_theme"] == "field" and r.json()["thermal_ai_off_c"] == 70
    r = client.post("/api/system/settings", json={"default_theme": "neon"})
    assert r.status_code == 400 and "default_theme" in r.json()["detail"]
    r = client.post("/api/system/hotspot", json={"ssid": "Bunker", "passphrase": "letmein123"})
    assert r.status_code == 200 and r.json()["hotspot"]["ssid"] == "Bunker"
    assert client.post("/api/system/hotspot", json={"ssid": "Bunker", "passphrase": "short"}).status_code == 400
    r = client.post("/api/system/eth-mode", json={"mode": "direct"})
    assert r.json()["eth_mode"] == "direct"
    assert client.post("/api/system/eth-mode", json={"mode": "bridge"}).status_code == 422
    app.state.updater = system.UpdateRunner(lambda tier: [sys.executable, "-c", f"print('sync {tier} ok')"])
    assert client.post("/api/system/update", json={"tiers": ["core", "extended"]}).json() == {"started": True}
    app.state.updater.wait(10)
    p = client.get("/api/system/update/progress").json()
    assert p["done"] is True and p["ok"] is True and p["lines"] == ["== sync core", "sync core ok"]
    app.state.updater = system.UpdateRunner(lambda tier: [sys.executable, "-c", "import time; time.sleep(0.5)"])
    assert client.post("/api/system/update", json={"tiers": ["core"]}).status_code == 200
    assert client.post("/api/system/update", json={"tiers": ["core"]}).status_code == 409
    app.state.updater.wait(5)
    assert client.post("/api/system/update", json={"tiers": ["nope"]}).status_code == 422


def test_validation_errors_are_strings(client):
    r = client.post("/api/notes", json={"kind": "bookmark"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and "kind" in r.json()["detail"]


def test_overlay_coverage_comes_from_the_installed_build(client, env):
    import json
    root = env.core / 'maps' / 'overlays'
    root.mkdir(exist_ok=True)
    (root / 'flood-zones.pmtiles').write_bytes(b'PMTiles')
    (root / 'index.json').write_text(json.dumps({'flood-zones': {'coverage': ['england']}}))
    client.post('/api/system/rescan')
    overlays = client.get('/api/map/overlays').json()
    flood = next(o for o in overlays if o['id'] == 'flood-zones')
    assert flood['available'] is True
    assert flood['coverage'] == ['england']


def test_library_resolves_a_dated_archive_link_after_an_upgrade(client, env):
    conn = db.connect(env.db_path)
    conn.execute("UPDATE library_items SET resolved_name='old-dated-name' WHERE id=?", (WIKI,))
    conn.commit()
    conn.close()
    response = client.get('/api/library/old-dated-name')
    assert response.status_code == 200
    assert response.json()['id'] == WIKI


def test_event_notes_keep_their_time_and_list_newest_first(client):
    first = client.post("/api/notes", json={"kind": "event", "title": "Water off"}).json()
    assert first["kind"] == "event" and first["updated_at"]
    second = client.post("/api/notes", json={"kind": "event", "title": "Heard sirens"}).json()
    assert [e["title"] for e in client.get("/api/notes", params={"kind": "event"}).json()] == ["Heard sirens", "Water off"]
    edited = client.put(f"/api/notes/{first['id']}", json={"title": "Water off at the mains"}).json()
    assert edited["title"] == "Water off at the mains" and edited["updated_at"] == first["updated_at"]
    assert second["updated_at"] >= first["updated_at"]
