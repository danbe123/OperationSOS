def test_stock_days_left_uses_household_size(client):
    r = client.post("/api/stock", json={"name": "Bottled water", "category": "water", "quantity": 36, "unit": "L"})
    assert r.status_code == 200
    water = r.json()
    assert water["per_person_day"] == 3.0            # UK guidance default for water
    assert water["days_left"] == 12.0                # nobody registered yet counts as one person
    assert client.get("/api/stock").json()["people"] == 1
    client.post("/api/household", json={"name": "Sam"})
    client.post("/api/household", json={"name": "Ali"})
    client.post("/api/household", json={"name": "Jo"})
    body = client.get("/api/stock").json()
    assert body["people"] == 3 and body["items"][0]["days_left"] == 4.0


def test_stock_validation_and_updates(client):
    assert client.post("/api/stock", json={"name": "Rice", "category": "snacks", "quantity": 1, "unit": "kg"}).status_code == 422   # schema rejects the category
    assert client.post("/api/stock", json={"name": "Rice", "category": "food", "quantity": -1, "unit": "kg"}).status_code == 400
    assert client.post("/api/stock", json={"name": "", "category": "food", "quantity": 1, "unit": "kg"}).status_code == 400
    rice = client.post("/api/stock", json={"name": "Rice", "category": "food", "quantity": 5, "unit": "kg", "expires": "2027-01-31"}).json()
    assert rice["per_person_day"] == 1.0 and rice["days_left"] == 5.0 and rice["expires"] == "2027-01-31"     # UK guidance default for food
    rice = client.put(f"/api/stock/{rice['id']}", json={"per_person_day": 0.25}).json()
    assert rice["days_left"] == 20.0 and rice["quantity"] == 5
    rice = client.put(f"/api/stock/{rice['id']}", json={"quantity": 2.5}).json()
    assert rice["days_left"] == 10.0
    assert client.put("/api/stock/99", json={"quantity": 1}).status_code == 404
    assert client.delete(f"/api/stock/{rice['id']}").json() == {"ok": True}
    assert client.get("/api/stock").json()["items"] == []
