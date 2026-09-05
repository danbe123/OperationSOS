from datetime import datetime, timedelta, timezone

from sos import situation


def test_phase_thresholds():
    h = 3600
    assert situation.phase_for(0) == "right-now"
    assert situation.phase_for(12 * h - 1) == "right-now"
    assert situation.phase_for(12 * h) == "first-72-hours"
    assert situation.phase_for(72 * h - 1) == "first-72-hours"
    assert situation.phase_for(72 * h) == "first-month"
    assert situation.phase_for(30 * 24 * h - 1) == "first-month"
    assert situation.phase_for(30 * 24 * h) == "long-term"


def test_situation_lifecycle(client):
    assert client.get("/api/situation").json() == {"slug": None}
    assert client.post("/api/situation", json={"slug": "no-such-playbook"}).status_code == 404
    r = client.post("/api/situation", json={"slug": "grid-collapse"})
    assert r.status_code == 200
    s = r.json()
    assert s["slug"] == "grid-collapse" and s["title"] == "National grid collapse" and s["phase"] == "right-now"
    assert 0 <= s["elapsed_s"] < 5 and s["started_at"].endswith("+00:00")
    assert client.get("/api/status").json()["situation"] == {"slug": "grid-collapse", "started_at": s["started_at"]}
    assert client.get("/api/situation").json()["slug"] == "grid-collapse"
    assert client.delete("/api/situation").json() == {"slug": None}
    assert client.get("/api/status").json()["situation"] is None


def test_situation_phase_from_stored_start(client, app):
    from sos import db
    conn = db.connect(app.state.settings.db_path)
    started = (datetime.now(timezone.utc) - timedelta(hours=20)).replace(microsecond=0).isoformat()
    situation.start(conn, "grid-collapse", started_at=started)
    conn.close()
    s = client.get("/api/situation").json()
    assert s["phase"] == "first-72-hours" and 19 * 3600 < s["elapsed_s"] < 21 * 3600
