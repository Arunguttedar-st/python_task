def test_user_registration(client):
    """Test registering a new user successfully."""
    payload = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "role": "Employee"
    }

    response = client.post("/auth/register", json=payload)
    # Adjust status code to 200 or 201 based on your app router
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "password" not in data  # Never expose passwords in responses


def test_user_login_success(client, test_user):
    """Test logging in with valid credentials returns a JWT access token."""
    response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_user_login_invalid_password(client, test_user):
    """Test logging in with an incorrect password returns 401 Unauthorized."""
    response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    """Test accessing a protected endpoint without authentication returns 401."""
    # Replace /users/me with any protected route in your app
    response = client.get("/users/me")
    assert response.status_code == 401


def test_role_based_access_control(client, test_user):
    """Test that regular employees receive 403 Forbidden when accessing admin routes."""
    # Login as regular employee
    login_res = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to access an admin-only endpoint (e.g., admin dashboard or management route)
    response = client.get("/admin/users", headers=headers)
    assert response.status_code == 403