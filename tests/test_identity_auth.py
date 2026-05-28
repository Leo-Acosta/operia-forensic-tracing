def test_bootstrap_login_me_and_permissions(client):
    bootstrap = client.post(
        "/api/identity/bootstrap-admin",
        json={
            "organization_name": "OPERIA Auth",
            "organization_slug": "operia-auth",
            "name": "Auth Admin",
            "email": "auth@test.local",
            "password": "AuthPassword123!",
        },
    )
    assert bootstrap.status_code == 200
    assert bootstrap.json()["user"]["role"] == "admin"

    login = client.post("/api/identity/login", json={"email": "auth@test.local", "password": "AuthPassword123!"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["authenticated"] is True

    permissions = client.get("/api/identity/permissions")
    assert permissions.status_code == 200
    assert "admin" in permissions.json()


def test_invalid_login_is_rejected(client):
    client.post(
        "/api/identity/bootstrap-admin",
        json={"email": "badlogin@test.local", "password": "GoodPassword123!"},
    )
    response = client.post("/api/identity/login", json={"email": "badlogin@test.local", "password": "wrong"})
    assert response.status_code == 401

