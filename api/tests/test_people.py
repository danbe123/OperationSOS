"""The one number a household is ever asked: how many people the kits are for (no-setup spec section 3)."""


def test_the_people_setting_starts_at_two(client):
    assert client.get("/api/settings/people").json() == {"people": 2}


def test_the_people_setting_round_trips(client):
    assert client.put("/api/settings/people", json={"people": 5}).json() == {"people": 5}
    assert client.get("/api/settings/people").json() == {"people": 5}
    assert client.get("/api/status").json()["people"] == 5


def test_a_household_of_none_or_of_twenty_one_is_refused(client):
    for count in (0, -3, 21, 100):
        r = client.put("/api/settings/people", json={"people": count})
        assert r.status_code == 400, count
        assert "people" in r.json()["detail"]
    assert client.get("/api/settings/people").json() == {"people": 2}       # nothing stuck
    assert client.put("/api/settings/people", json={"people": 1}).json() == {"people": 1}
    assert client.put("/api/settings/people", json={"people": 20}).json() == {"people": 20}


def test_not_a_number_is_refused(client):
    assert client.put("/api/settings/people", json={"people": "lots"}).status_code == 422


def test_status_carries_the_count(client):
    assert client.get("/api/status").json()["people"] == 2


def test_the_endpoints_a_household_had_to_fill_in_are_gone(client):
    """The register, the street list and Stock: nothing to type in, so nothing to answer (no-setup spec)."""
    for path in ("/api/household", "/api/stock", "/api/neighbours", "/api/street-list"):
        assert client.get(path).status_code == 404, path
    assert client.post("/api/household", json={"name": "Sam"}).status_code == 404
