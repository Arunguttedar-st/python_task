def test_create_product(client, admin_user):
    # Authenticate admin user to get JWT token
    response = client.post("/auth/login", data={"username": "admin@example.com", "password": "admin123"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "sku": "PROD-001",
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse",
        "price": 29.99,
        "stock": 50,
        "reorder_level": 10
    }

    res = client.post("/products/", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["sku"] == "PROD-001"
    assert data["name"] == "Wireless Mouse"


def test_duplicate_sku_constraint(client, admin_user):
    response = client.post("/auth/login", data={"username": "admin@example.com", "password": "admin123"})
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    payload = {
        "sku": "PROD-DUP",
        "name": "Keyboard",
        "price": 49.99,
        "stock": 20
    }

    # First creation should succeed
    client.post("/products/", json=payload, headers=headers)

    # Second creation with the same SKU should fail
    res = client.post("/products/", json=payload, headers=headers)
    assert res.status_code == 400
    assert "sku" in res.json()["detail"].lower()


def test_get_nonexistent_product(client, test_user):
    response = client.post("/auth/login", data={"username": "user@example.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    res = client.get("/products/99999", headers=headers)
    assert res.status_code == 404