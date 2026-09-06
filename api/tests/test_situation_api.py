"""The situation API: the View, conditions, tasks, home, drills, the report and the status fields."""
import shutil
from datetime import datetime, timedelta, timezone

import pytest

from sos import db


@pytest.fixture
def playbooks(env, tmp_path):
    """A throwaway copy of the fixture content, so a test may edit a document without touching the fixtures."""
    root = tmp_path / "editable-playbooks"
    shutil.copytree(env.playbooks, root)
    env.playbooks_dir = root
    return root


def hours_ago(n: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=n)).replace(microsecond=0).isoformat()


def events(client) -> list[str]:
    return [n["title"] for n in client.get("/api/notes", params={"kind": "event"}).json()]


def power_off(client, n: float = 5):
    return client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(n)})


# --- the View --------------------------------------------------------------------------------------------

def test_view_in_peacetime(client):
    view = client.get("/api/situation/view").json()
    assert set(view) == {"meta", "scenario", "conditions", "inferred", "forecast", "tasks", "neighbours", "briefing",
                         "modes", "readiness", "bulletins"}
    assert view["scenario"] is None and view["meta"]["drill"] is False
    assert set(view["conditions"]) == {"power", "water", "mobile", "landline", "internet", "gas", "heating", "roads",
                                       "shops", "sewage"}
    assert view["conditions"]["power"] == {"id": "power", "title": "Mains power", "state": "working", "since": None,
                                           "source": "manual", "confidence": 1.0, "note": "", "set_by": "",
                                           "updated_at": None, "confirmed_at": None, "for_s": 0, "stale": False}
    assert view["inferred"] == [] and view["forecast"] == [] and view["briefing"] == []
    assert view["neighbours"] == {"check_on": [], "skills": []}
    assert view["modes"] == {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
    assert 0 <= view["readiness"]["score"] <= 100 and view["readiness"]["gaps"]
    assert view["bulletins"]["next"]["station"] == "BBC Radio 4"


def test_the_view_reacts_to_a_power_cut(client):
    assert power_off(client, 5).status_code == 200
    view = client.get("/api/situation/view").json()
    assert view["conditions"]["power"]["state"] == "off" and 4.9 * 3600 < view["conditions"]["power"]["for_s"] <= 5 * 3600
    assert [(i["condition"], i["state"]) for i in view["inferred"]] == [("internet", "off"), ("mobile", "degraded")]
    assert [f["id"] for f in view["forecast"]] == ["fridge", "freezer"]
    assert view["forecast"][0]["passed"] is True and view["forecast"][1]["passed"] is False
    assert [t["id"] for t in view["tasks"]] == ["fill-bath", "water-stock-low"]
    assert view["briefing"] == [{"title": "PMR446 radio channels", "kind": "page", "ref": "pmr446"},
                                {"title": "Water", "kind": "module", "ref": "water"}]


def test_the_model_reads_the_stock_without_opening_a_kit_file(client, monkeypatch):
    """The engine reads a row's category, name, notes, days_left and days_raw, and nothing else -- so
    the model is built without the content cache, and without a `kit()` lookup (a file stat) per row."""
    from sos.routers import situation as situation_mod

    client.put("/api/kits/water/items/stored-water", json={"checked": True, "stock": {"quantity": 9}})
    conn = db.connect(client.app.state.settings.db_path)
    rows = situation_mod._stock(conn)
    row = next(r for r in rows if r["kit_item"])
    # The unrounded run is what the engine adds rows by, and it is still on every row.
    assert row["days_raw"] is not None and row["days_left"] == round(row["days_raw"], 1)
    assert row["kit_title"] is None                       # the one thing the content cache was for

    cache = client.app.state.content
    opened = []
    real = cache.kit
    monkeypatch.setattr(cache, "kit", lambda slug: opened.append(slug) or real(slug))
    situation_mod._stock(conn)
    assert opened == []                                   # no kit file stat'd per kit-sourced row
    # And the View the engine builds off those rows is still built.
    assert client.get("/api/situation/view").status_code == 200


# --- conditions ------------------------------------------------------------------------------------------

def test_conditions_endpoint_lists_all_ten(client):
    body = client.get("/api/conditions").json()
    assert len(body) == 10 and body["sewage"]["title"] == "Sewage and drains" and body["sewage"]["stale"] is False


def test_setting_a_condition_writes_an_event_naming_the_actor(client, remote_client):
    r = client.put("/api/conditions/power", json={"state": "off", "since": "2026-09-06T14:20:00+00:00", "note": "Whole street"})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "off" and body["set_by"] == "kiosk" and body["note"] == "Whole street" and body["updated_at"]
    assert "Mains power off since 14:20 (kiosk)" in events(client)
    remote_client.put("/api/conditions/water", json={"state": "degraded"})
    assert any(t.startswith("Water supply degraded since") and t.endswith("(phone)") for t in events(client))


def test_unknown_condition_and_bad_state(client):
    assert client.put("/api/conditions/broadband", json={"state": "off"}).status_code == 404
    assert client.put("/api/conditions/power", json={"state": "wobbly"}).status_code == 422
    assert client.post("/api/conditions/broadband/confirm").status_code == 404
    assert client.post("/api/conditions/broadband/accept", json={"rule": "x"}).status_code == 404


def test_a_stale_write_is_refused_with_the_current_row(client):
    client.put("/api/conditions/power", json={"state": "off"})
    stale = "2026-09-06T09:00:00+00:00"                    # what a phone that has been asleep still holds
    client.put("/api/conditions/power", json={"state": "degraded"})
    r = client.put("/api/conditions/power", json={"state": "working", "expected_updated_at": stale})
    assert r.status_code == 409
    assert r.json()["current"]["state"] == "degraded" and "changed" in r.json()["detail"]
    fresh = client.get("/api/conditions").json()["power"]["updated_at"]
    assert client.put("/api/conditions/power", json={"state": "working", "expected_updated_at": fresh}).status_code == 200


def test_confirming_a_condition_clears_the_stale_flag(client, app):
    power_off(client, 30)
    conn = db.connect(app.state.settings.db_path)
    conn.execute("UPDATE conditions SET updated_at=?, confirmed_at=? WHERE id='power'", (hours_ago(30), hours_ago(30)))
    conn.commit()
    conn.close()
    assert client.get("/api/conditions").json()["power"]["stale"] is True
    r = client.post("/api/conditions/power/confirm")
    assert r.status_code == 200 and r.json()["stale"] is False
    assert "Mains power still off (kiosk)" in events(client)


def test_accepting_an_inferred_state(client):
    power_off(client, 5)
    r = client.post("/api/conditions/mobile/accept", json={"rule": "power-off-mobile-degraded"})
    assert r.status_code == 200
    assert r.json()["state"] == "degraded" and r.json()["source"] == "inferred" and r.json()["confidence"] == 0.7
    assert r.json()["since"].startswith(hours_ago(1)[:13])          # since the moment the rule came due
    view = client.get("/api/situation/view").json()
    assert not any(i["condition"] == "mobile" for i in view["inferred"])
    assert any("Mobile network degraded taken from power-off-mobile-degraded (kiosk)" in t for t in events(client))
    assert client.post("/api/conditions/mobile/accept", json={"rule": "no-such-rule"}).status_code == 404


# --- tasks -----------------------------------------------------------------------------------------------

def test_tasks_can_be_ticked_and_assigned(client):
    power_off(client, 2)
    assert [t["id"] for t in client.get("/api/tasks").json()] == ["fill-bath", "water-stock-low"]
    r = client.put("/api/tasks/fill-bath", json={"done": True, "person": "Sam"})
    assert r.status_code == 200 and r.json()["done"] is True and r.json()["person"] == "Sam" and r.json()["done_at"]
    assert [t for t in client.get("/api/tasks").json() if t["id"] == "fill-bath"][0]["done"] is True
    assert any("Task done: Fill the bath while the water is still on — Sam (kiosk)" == t for t in events(client))
    r = client.put("/api/tasks/fill-bath", json={"done": False})
    assert r.json()["done"] is False and r.json()["done_at"] is None
    assert client.put("/api/tasks/nonsense", json={"done": True}).status_code == 404


def test_checklist_tasks_share_their_state_with_the_playbook(client):
    client.post("/api/situation", json={"slug": "grid-collapse"})
    tasks = client.get("/api/tasks").json()
    checklist = [t for t in tasks if t["source"] == "checklist:grid-collapse"]
    assert [t["id"] for t in checklist] == [                       # in bucket order, then by title
        "checklist:grid-collapse/check-on-neighbours",
        "checklist:grid-collapse/water/fill-clean-containers",
        "checklist:grid-collapse/fill-every-bottle-and-the-bath",
        "checklist:grid-collapse/water/label-treated",
        "checklist:grid-collapse/cooker-off"]
    assert all(t["bucket"] == "today" and t["done"] is False for t in checklist)
    r = client.put("/api/tasks/checklist:grid-collapse/cooker-off", json={"done": True})
    assert r.status_code == 200 and r.json()["done"] is True
    playbook = client.get("/api/playbooks/grid-collapse").json()
    assert [c["checked"] for c in playbook["checklist"] if c["id"] == "cooker-off"] == [True]
    # and the other way round
    client.put("/api/playbooks/grid-collapse/checklist/fill-every-bottle-and-the-bath", json={"checked": True})
    done = {t["id"]: t["done"] for t in client.get("/api/tasks").json()}
    assert done["checklist:grid-collapse/fill-every-bottle-and-the-bath"] is True


# --- home ------------------------------------------------------------------------------------------------

def test_home_is_read_and_written(client):
    assert client.get("/api/home").json() == {"lat": None, "lon": None, "label": "Home", "flood_zone": None}
    r = client.put("/api/home", json={"lat": 50.9333, "lon": -1.4333, "label": "The house", "flood_zone": "3"})
    assert r.status_code == 200 and r.json() == {"lat": 50.9333, "lon": -1.4333, "label": "The house", "flood_zone": "3"}
    assert client.get("/api/situation/view").json()["meta"]["home"]["label"] == "The house"
    assert any(t.startswith("Home set to The house at 50.9333, -1.4333") for t in events(client))
    assert client.put("/api/home", json={"lat": 950, "lon": 0}).status_code == 422


def test_the_view_knows_whether_it_is_dark_at_home(client):
    client.put("/api/home", json={"lat": 50.9333, "lon": -1.4333})
    meta = client.get("/api/situation/view").json()["meta"]
    assert meta["sunrise"] and meta["sunset"] and isinstance(meta["dark"], bool)


# --- drills ----------------------------------------------------------------------------------------------

def test_a_drill_runs_and_puts_everything_back(client):
    client.put("/api/conditions/water", json={"state": "degraded", "note": "Real"})
    r = client.post("/api/drill", json={"scenario": "grid-collapse", "conditions": {"power": "off"}, "hours_ago": 6})
    assert r.status_code == 200
    view = r.json()
    assert view["meta"]["drill"] is True and view["scenario"]["slug"] == "grid-collapse"
    assert 5.9 * 3600 < view["scenario"]["elapsed_s"] <= 6 * 3600
    assert view["conditions"]["power"]["state"] == "off" and view["conditions"]["power"]["source"] == "drill"
    assert view["conditions"]["water"]["state"] == "degraded"      # the real state is still in place
    assert client.get("/api/status").json()["drill"] is True
    client.put("/api/tasks/boil-water", json={"done": True})
    assert any("Task done: Boil or treat every drop (drill)" == t for t in events(client))
    ended = client.delete("/api/drill")
    assert ended.status_code == 200
    view = ended.json()
    assert view["meta"]["drill"] is False and view["scenario"] is None
    assert view["conditions"]["power"]["state"] == "working" and view["conditions"]["water"]["note"] == "Real"
    assert not any(t["id"] == "fill-bath" for t in view["tasks"])          # the power is back on
    assert not any(t["done"] for t in view["tasks"])                        # the drill's ticks went with it
    assert any(t.startswith("Drill ended after 6 h: 1 job ticked (drill)") for t in events(client))
    assert client.delete("/api/drill").status_code == 404


def test_a_drill_restores_the_scenario_that_was_running(client):
    client.post("/api/situation", json={"slug": "grid-collapse"})
    started = client.get("/api/situation").json()["started_at"]
    client.post("/api/drill", json={"scenario": "grid-collapse", "conditions": {"power": "off"}})
    client.delete("/api/drill")
    assert client.get("/api/situation").json()["started_at"] == started


def test_a_drill_needs_a_real_playbook_and_real_conditions(client):
    assert client.post("/api/drill", json={"scenario": "no-such-playbook"}).status_code == 404
    assert client.post("/api/drill", json={"scenario": "grid-collapse", "conditions": {"broadband": "off"}}).status_code == 422
    assert client.post("/api/drill", json={"scenario": "grid-collapse", "conditions": {"power": "wobbly"}}).status_code == 422


def test_a_finished_drill_counts_as_practice(client):
    before = client.get("/api/situation/view").json()["readiness"]
    client.post("/api/drill", json={"scenario": "grid-collapse", "conditions": {"power": "off"}})
    client.delete("/api/drill")
    after = client.get("/api/situation/view").json()["readiness"]
    assert after["score"] == before["score"] + 10
    assert not any(g["title"] == "No drill in the last six months" for g in after["gaps"])


# --- the report and the status ---------------------------------------------------------------------------

def test_the_report_is_markdown(client):
    power_off(client, 5)
    client.post("/api/situation", json={"slug": "grid-collapse"})
    r = client.get("/api/situation/report")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown")
    text = r.text
    assert text.startswith("# Situation report") and "**Mains power**: off" in text
    assert "Freezer food unsafe" in text and "## Tasks" in text and "Readiness" in text
    assert "Situation started: National grid collapse (kiosk)" in text


def test_status_carries_the_situation_and_no_services(client):
    power_off(client, 1)
    body = client.get("/api/status").json()
    assert "services" not in body
    assert body["conditions"]["power"] == "off" and body["conditions"]["water"] == "working"
    assert body["modes"] == {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
    assert body["drill"] is False and isinstance(body["readiness_score"], int)
    assert client.get("/api/services").status_code == 404


def test_calls_are_hidden_when_both_phone_routes_are_off(client):
    client.put("/api/conditions/mobile", json={"state": "off"})
    client.put("/api/conditions/landline", json={"state": "off"})
    assert client.get("/api/status").json()["modes"]["calls"] == "hidden"


# --- content follows the situation -------------------------------------------------------------------------

@pytest.fixture
def branching_page(playbooks):
    path = playbooks / "pages" / "pmr446.md"
    path.write_text(path.read_text(encoding="utf-8")
                    + "\n\n{{#if power}}Charge the handsets.{{else}}Save the batteries.{{/if}}\n", encoding="utf-8")
    yield path


def test_a_page_renders_the_branch_for_the_current_situation(branching_page, client):
    assert "Charge the handsets." in client.get("/api/pages/pmr446").json()["html"]
    client.put("/api/conditions/power", json={"state": "off"})
    assert "Save the batteries." in client.get("/api/pages/pmr446").json()["html"]
    client.put("/api/conditions/power", json={"state": "degraded"})
    assert "Charge the handsets." in client.get("/api/pages/pmr446").json()["html"]     # degraded still counts as on


def test_a_module_and_a_card_render_the_branch_too(playbooks, client):
    for kind, slug in (("modules", "water"), ("cards", "bleeding")):
        path = playbooks / kind / f"{slug}.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n\nIf they stop breathing [[call 999]].\n", encoding="utf-8")
    assert "call 999" in client.get("/api/cards/bleeding").json()["html"]
    client.put("/api/conditions/mobile", json={"state": "off"})
    client.put("/api/conditions/landline", json={"state": "off"})
    assert "will not connect" in client.get("/api/cards/bleeding").json()["html"]
    assert "will not connect" in client.get("/api/modules/water").json()["html"]
    assert any("will not connect" in c["html"] for c in client.get("/api/cards").json())


def test_a_playbook_renders_the_branch_for_the_current_situation(playbooks, client):
    path = playbooks / "scenarios" / "grid-collapse.md"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "## First month", "{{#if scenario:grid-collapse}}The grid is down.{{/if}}\n\n## First month"), encoding="utf-8")
    assert "The grid is down." not in client.get("/api/playbooks/grid-collapse").json()["sections"][1]["html"]
    client.post("/api/situation", json={"slug": "grid-collapse"})
    assert "The grid is down." in client.get("/api/playbooks/grid-collapse").json()["sections"][1]["html"]
