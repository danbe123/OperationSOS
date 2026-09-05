"""The street list: the neighbours register, the who-to-check-on tasks and the printable list."""
from datetime import datetime, timedelta, timezone

import pytest

from sos import neighbours as nb


def hours_ago(n: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=n)).replace(microsecond=0).isoformat()


def events(client) -> list[str]:
    return [n["title"] for n in client.get("/api/notes", params={"kind": "event"}).json()]


@pytest.fixture
def khan(client):
    return client.post("/api/neighbours", json={
        "name": "Mrs Khan", "address": "12 Elm Road", "needs": "oxygen concentrator",
        "skills": "retired nurse", "contacts": "07700 900123", "notes": "Spare key with number 14."}).json()


# --- the register ---------------------------------------------------------------------------------------

def test_a_neighbour_is_added_read_updated_and_deleted(client, khan):
    assert khan["id"] > 0 and khan["name"] == "Mrs Khan" and khan["address"] == "12 Elm Road"
    assert khan["needs"] == "oxygen concentrator" and khan["skills"] == "retired nurse"
    assert khan["contacts"] == "07700 900123" and khan["notes"].startswith("Spare key")
    assert khan["updated_at"]

    assert client.get("/api/neighbours").json() == [khan]

    updated = client.put(f"/api/neighbours/{khan['id']}", json={"needs": "oxygen concentrator, over 75"}).json()
    assert updated["needs"] == "oxygen concentrator, over 75" and updated["name"] == "Mrs Khan"

    assert client.delete(f"/api/neighbours/{khan['id']}").json() == {"ok": True}
    assert client.get("/api/neighbours").json() == []


def test_neighbours_are_listed_in_name_order(client):
    for name in ("Zoe", "Ali", "Mrs Khan"):
        client.post("/api/neighbours", json={"name": name})
    assert [n["name"] for n in client.get("/api/neighbours").json()] == ["Ali", "Mrs Khan", "Zoe"]


def test_a_neighbour_needs_a_name(client):
    assert client.post("/api/neighbours", json={"name": "   "}).status_code == 400
    assert client.post("/api/neighbours", json={}).status_code == 422


def test_unknown_neighbours_are_404(client):
    assert client.get("/api/neighbours").json() == []
    assert client.put("/api/neighbours/99", json={"name": "Nobody"}).status_code == 404
    assert client.delete("/api/neighbours/99").status_code == 404


def test_every_neighbour_change_is_an_event_naming_the_actor(client, remote_client):
    row = remote_client.post("/api/neighbours", json={"name": "Mrs Khan", "address": "12 Elm Road"}).json()
    remote_client.put(f"/api/neighbours/{row['id']}", json={"needs": "oxygen"})
    remote_client.delete(f"/api/neighbours/{row['id']}")
    log = events(client)
    assert "Neighbour added: Mrs Khan at 12 Elm Road (phone)" in log
    assert "Neighbour updated: Mrs Khan at 12 Elm Road (phone)" in log
    assert "Neighbour removed: Mrs Khan at 12 Elm Road (phone)" in log


# --- the printable street list --------------------------------------------------------------------------

def test_the_street_list_is_markdown_with_a_row_for_each_neighbour(client, khan):
    client.post("/api/neighbours", json={"name": "Mr Ali", "address": "9 Elm Road", "skills": "generator, van"})
    response = client.get("/api/street-list")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    text = response.text
    assert text.startswith("# Street list")
    assert "| Mrs Khan | 12 Elm Road | oxygen concentrator | retired nurse | 07700 900123 |" in text
    assert "| Mr Ali | 9 Elm Road |" in text
    assert "Spare key with number 14." in text
    assert "2 neighbours" in text


def test_an_empty_street_list_still_prints(client):
    text = client.get("/api/street-list").text
    assert "Nobody is on the street list yet" in text


def test_the_street_list_escapes_a_pipe_in_a_field():
    text = nb.street_list([{"name": "A|B", "address": "", "needs": "", "skills": "", "contacts": "", "notes": ""}],
                          "2026-09-06T14:00:00+00:00")
    rows = [line for line in text.splitlines() if line.startswith("| A")]
    assert rows and rows[0].startswith("| A\\|B |") and rows[0].endswith(" |")


# --- the rules -------------------------------------------------------------------------------------------

def test_a_power_cut_yields_a_check_on_task_for_the_neighbour(client, khan):
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(1)})
    view = client.get("/api/situation/view").json()
    check_on = view["neighbours"]["check_on"]
    assert [c["id"] for c in check_on] == ["neighbour:mrs-khan"]
    assert check_on[0]["title"] == "Check on Mrs Khan at 12 Elm Road"
    assert check_on[0]["address"] == "12 Elm Road" and check_on[0]["contacts"] == "07700 900123"
    assert check_on[0]["done"] is False and check_on[0]["bucket"] == "now"
    assert "Check on Mrs Khan at 12 Elm Road" in [t["title"] for t in view["tasks"]]


def test_a_neighbour_check_on_task_can_be_ticked(client, khan):
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(1)})
    done = client.put("/api/tasks/neighbour:mrs-khan", json={"done": True}).json()
    assert done["done"] is True
    view = client.get("/api/situation/view").json()
    assert view["neighbours"]["check_on"][0]["done"] is True


def test_a_neighbour_with_no_matching_need_is_not_on_the_check_on_list(client):
    client.post("/api/neighbours", json={"name": "Mr Ali", "address": "9 Elm Road", "needs": "", "skills": "nurse"})
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(1)})
    assert client.get("/api/situation/view").json()["neighbours"]["check_on"] == []


def test_skills_are_listed_when_a_reading_rule_asks_for_them(client, khan):
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(1)})
    skills = client.get("/api/situation/view").json()["neighbours"]["skills"]
    assert skills == [{"name": "Mrs Khan", "address": "12 Elm Road", "skill": "nurse",
                       "text": "Mrs Khan is a nurse", "contacts": "07700 900123",
                       "why": skills[0]["why"], "rule": "neighbour-skills", "link": None}]


def test_the_report_carries_the_neighbours(client, khan):
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(1)})
    text = client.get("/api/situation/report").text
    assert "## Neighbours" in text
    assert "Check on Mrs Khan at 12 Elm Road" in text
    assert "Mrs Khan is a nurse" in text


def test_nothing_about_neighbours_when_the_list_is_empty(client):
    client.put("/api/conditions/power", json={"state": "off", "since": hours_ago(1)})
    view = client.get("/api/situation/view").json()
    assert view["neighbours"] == {"check_on": [], "skills": []}
    assert "## Neighbours" not in client.get("/api/situation/report").text
