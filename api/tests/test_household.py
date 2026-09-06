def test_household_crud(client):
    r = client.post("/api/household", json={"name": "Sam", "age": 7, "needs": "asthma", "medications": "salbutamol inhaler"})
    assert r.status_code == 200
    sam = r.json()
    assert sam["id"] == 1 and sam["name"] == "Sam" and sam["age"] == 7 and sam["contacts"] == "" and sam["updated_at"]
    assert client.post("/api/household", json={"name": "  "}).status_code == 400
    ali = client.post("/api/household", json={"name": "Ali"}).json()
    assert ali["age"] is None and ali["needs"] == "" and ali["medications"] == ""
    assert [p["name"] for p in client.get("/api/household").json()] == ["Sam", "Ali"]
    r = client.put("/api/household/1", json={"contacts": "Gran 01onal 555"})
    assert r.json()["contacts"] == "Gran 01onal 555" and r.json()["needs"] == "asthma"
    assert client.put("/api/household/99", json={"name": "x"}).status_code == 404
    assert client.delete("/api/household/2").json() == {"ok": True}
    assert client.delete("/api/household/2").status_code == 404
    assert len(client.get("/api/household").json()) == 1


def test_stock_rows_carry_kit_item(client):
    item = client.post("/api/stock", json={"name": "Bottled water", "category": "water", "quantity": 12, "unit": "L"}).json()
    assert item["kit_item"] is None
    assert client.get("/api/stock").json()["items"][0]["kit_item"] is None
