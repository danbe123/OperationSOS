"""The readiness score kept in the settings table: recomputed on every change that moves it, and once a night."""
from datetime import datetime, timezone

from sos import db, readiness


def score(env) -> int | None:
    conn = db.connect(env.db_path)
    try:
        return readiness.stored(conn)
    finally:
        conn.close()


def stored_at(env) -> str | None:
    conn = db.connect(env.db_path)
    try:
        return db.get_setting(conn, readiness.AT_KEY)
    finally:
        conn.close()


def test_status_stores_the_score_on_the_first_read(client, env):
    assert score(env) is None
    first = client.get("/api/status").json()["readiness_score"]
    assert 0 <= first <= 100 and score(env) == first


def test_stock_changes_recompute_the_score(client, env):
    client.get("/api/status")
    before = score(env)
    item = client.post("/api/stock", json={"name": "Bottled water", "category": "water", "quantity": 60,
                                           "unit": "l"}).json()
    after = score(env)
    assert after > before                                   # three people-days of water is worth points
    assert client.get("/api/status").json()["readiness_score"] == after

    client.put(f"/api/stock/{item['id']}", json={"quantity": 3})
    assert score(env) < after
    client.delete(f"/api/stock/{item['id']}")
    assert score(env) == before


def test_household_changes_recompute_the_score(client, env):
    client.get("/api/status")
    before = score(env)
    person = client.post("/api/household", json={"name": "Ruth", "needs": "insulin"}).json()
    with_need = score(env)
    assert with_need != before                              # a need nothing in the cupboard covers costs points
    client.put(f"/api/household/{person['id']}", json={"contacts": "07700 900000"})
    assert score(env) == with_need + 5                      # a contact number is five points of the plan
    client.delete(f"/api/household/{person['id']}")
    assert score(env) == before


def test_setting_the_home_recomputes_the_score(client, env):
    client.get("/api/status")
    before = score(env)
    client.put("/api/home", json={"lat": 50.93, "lon": -1.42, "label": "Home"})
    assert score(env) == before + 6                         # home on the map is six points


def test_a_finished_drill_recomputes_the_score(client, env):
    client.get("/api/status")
    before = score(env)
    client.post("/api/drill", json={"scenario": "grid-collapse", "conditions": {"power": "off"}, "hours_ago": 1})
    client.delete("/api/drill")
    assert score(env) == before + 10                        # a drill in the last six months is ten points


def test_the_nightly_recompute_runs_once_a_day_after_three(client, env):
    conn = db.connect(env.db_path)
    try:
        assert readiness._due(conn, datetime(2026, 9, 6, 1, 0, tzinfo=timezone.utc)) is False   # too early
        assert readiness._due(conn, datetime(2026, 9, 6, 3, 5, tzinfo=timezone.utc)) is True
        db.set_setting(conn, readiness.AT_KEY, "2026-09-06T03:05:00+00:00")
        assert readiness._due(conn, datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)) is False  # already done today
        assert readiness._due(conn, datetime(2026, 9, 7, 3, 5, tzinfo=timezone.utc)) is True
    finally:
        conn.close()


def test_a_scoring_failure_never_fails_the_write_that_caused_it(client, env, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("rules are broken")

    monkeypatch.setattr(readiness, "store", boom)
    assert client.post("/api/stock", json={"name": "Rice", "category": "food", "quantity": 5,
                                           "unit": "kg"}).status_code == 200


def test_the_score_is_written_with_a_timestamp(client, env):
    client.get("/api/status")
    assert (stored_at(env) or "").startswith(datetime.now(timezone.utc).date().isoformat())
