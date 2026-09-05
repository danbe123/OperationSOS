def test_services_default_on_and_toggle(client):
    assert client.get("/api/services").json() == {"power": True, "water": True, "gas": True, "internet": True, "phones": True}
    r = client.put("/api/services/phones", json={"on": False})
    assert r.status_code == 200 and r.json()["phones"] is False and r.json()["power"] is True
    assert client.get("/api/status").json()["services"]["phones"] is False
    assert client.put("/api/services/broadband", json={"on": False}).status_code == 404
    assert client.put("/api/services/phones", json={"on": True}).json()["phones"] is True
