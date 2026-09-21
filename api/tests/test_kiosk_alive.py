"""The kiosk page's heartbeat: the page posts /api/kiosk/alive every 30 s; the API keeps the time in memory and
reports the age to the kiosk wrapper (loopback only), which restarts a Chromium whose page has gone quiet."""
from __future__ import annotations

import pytest

from sos.routers.kiosk import Heartbeat


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_heartbeat_reports_no_age_until_the_page_has_spoken_and_then_how_long_ago():
    clock = Clock()
    beat = Heartbeat(clock)
    assert beat.snapshot() == {"age_s": None, "api_up_s": 0.0}
    clock.now += 40
    assert beat.snapshot() == {"age_s": None, "api_up_s": 40.0}
    assert beat.hit("kiosk") is True
    clock.now += 25.5
    assert beat.snapshot() == {"age_s": 25.5, "api_up_s": 65.5}


def test_heartbeat_is_rate_limited_and_a_flood_does_not_refresh_the_time():
    clock = Clock()
    beat = Heartbeat(clock)
    assert [beat.hit("kiosk") for _ in range(6)] == [True] * 6
    clock.now += 10
    assert beat.hit("kiosk") is False
    assert beat.snapshot()["age_s"] == 10.0
    clock.now += 60
    assert beat.hit("kiosk") is True


def test_the_endpoints_are_loopback_only_and_round_trip(client, remote_client):
    assert client.get("/api/kiosk/alive-age").json()["age_s"] is None
    r = client.post("/api/kiosk/alive")
    assert r.status_code == 200 and r.json() == {"ok": True}
    body = client.get("/api/kiosk/alive-age").json()
    assert 0 <= body["age_s"] < 5 and body["api_up_s"] >= body["age_s"]
    # a phone on the hotspot is not the kiosk and may neither say it is alive nor read the age
    assert remote_client.post("/api/kiosk/alive").status_code == 403
    assert remote_client.get("/api/kiosk/alive-age").status_code == 403


def test_the_endpoint_answers_429_when_flooded(client):
    codes = [client.post("/api/kiosk/alive").status_code for _ in range(8)]
    assert codes[:6] == [200] * 6 and set(codes[6:]) == {429}


def test_the_heartbeat_takes_no_body_and_no_pin(client):
    assert client.post("/api/kiosk/alive", content=b"").status_code == 200
