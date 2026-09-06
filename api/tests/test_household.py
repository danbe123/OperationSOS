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


def test_stock_days_sum_per_category_and_ignore_expired(client):
    client.post("/api/household", json={"name": "Dan"})
    client.post("/api/household", json={"name": "Sam"})
    client.post("/api/stock", json={"name": "Bottles", "category": "water", "quantity": 12, "unit": "L"})            # rate defaults to 3
    client.post("/api/stock", json={"name": "Butt", "category": "water", "quantity": 12, "unit": "L"})
    client.post("/api/stock", json={"name": "Tins", "category": "food", "quantity": 6, "unit": "person-days"})      # rate defaults to 1
    client.post("/api/stock", json={"name": "Old pills", "category": "medicine", "quantity": 14, "unit": "days of supply", "expires": "2020-01-01"})
    client.post("/api/stock", json={"name": "Gas", "category": "fuel", "quantity": 2, "unit": "canisters"})
    body = client.get("/api/stock").json()
    assert body["people"] == 2
    assert body["days"] == {"water": 4.0, "food": 3.0, "medicine": 0.0}
    rows = {r["name"]: r for r in body["items"]}
    assert rows["Bottles"]["days_left"] == 2.0 and rows["Bottles"]["expired"] is False
    assert rows["Old pills"]["expired"] is True and rows["Old pills"]["days_left"] == 0.0
    assert rows["Gas"]["days_left"] is None and rows["Gas"]["per_person_day"] is None


def test_readiness_ignores_expired_stock(client):
    client.post("/api/household", json={"name": "Dan"})
    client.post("/api/stock", json={"name": "Old pills", "category": "medicine", "quantity": 140, "unit": "days of supply", "expires": "2020-01-01"})
    gaps = client.get("/api/situation/view").json()["readiness"]["gaps"]
    assert any(g["title"].startswith("Medicine: 0 days") for g in gaps)
