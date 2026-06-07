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
    assert "*" in permissions.json()["admin"]

    logout = client.post("/api/identity/logout", json={"token": token}, headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200

    logged_out_me = client.get("/api/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert logged_out_me.status_code == 200
    assert logged_out_me.json()["authenticated"] is False


def test_invalid_login_is_rejected(client):
    client.post(
        "/api/identity/bootstrap-admin",
        json={"email": "badlogin@test.local", "password": "GoodPassword123!"},
    )
    response = client.post("/api/identity/login", json={"email": "badlogin@test.local", "password": "wrong"})
    assert response.status_code == 401


def test_identity_admin_endpoints_require_valid_token(client, admin_headers):
    unauthenticated = client.get("/api/identity/users")
    assert unauthenticated.status_code == 401

    authenticated = client.get("/api/identity/users", headers=admin_headers)
    assert authenticated.status_code == 200
    assert authenticated.json()


def test_sensitive_write_requires_permission_token(client, admin_headers):
    case_without_auth = client.post(
        "/api/cases",
        json={
            "case_code": "AUTH-LOCK-001",
            "title": "Caso protegido",
            "description": "Intento sin sesión",
            "incident_type": "phishing",
        },
    )
    assert case_without_auth.status_code == 401

    case = client.post(
        "/api/cases",
        json={
            "case_code": "AUTH-LOCK-002",
            "title": "Caso protegido con sesión",
            "description": "Alta autorizada",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200


def test_local_admin_recovery_resets_admin_access(client):
    client.post(
        "/api/identity/bootstrap-admin",
        json={"email": "recover@test.local", "password": "OldPassword123!"},
    )
    recovery = client.post(
        "/api/identity/local-admin-recovery",
        json={
            "organization_name": "OPERIA Local",
            "organization_slug": "operia-local",
            "name": "OPERIA Admin Recuperado",
            "email": "admin@operia.local",
            "password": "OperiaAdmin2026!",
        },
    )
    assert recovery.status_code == 200
    token = recovery.json()["access_token"]

    me = client.get("/api/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["authenticated"] is True
    assert me.json()["user"]["role"] == "admin"


def test_settings_readiness_exposes_alembic_head(client):
    response = client.get("/api/settings/readiness")
    assert response.status_code == 200
    database = response.json()["database"]
    assert "20260528_0001" in database["alembic_heads"]
    assert database["schema_version"]


def test_user_can_update_professional_profile(client, admin_headers):
    response = client.put(
        "/api/identity/me/profile",
        json={
            "name": "Analista Forense",
            "title": "Perito informatico",
            "agency": "OPERIA Lab",
            "registration_id": "MP-001",
            "phone": "+54 11 0000-0000",
            "signature": "Firma profesional registrada",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Perito informatico"
    assert data["agency"] == "OPERIA Lab"

    me = client.get("/api/identity/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["user"]["registration_id"] == "MP-001"


def test_admin_can_manage_users_and_reset_password(client, admin_headers):
    created = client.post(
        "/api/identity/users",
        json={
            "name": "Analista Junior",
            "email": "junior@test.local",
            "role": "analista",
            "password": "InitialPassword123!",
            "title": "Analista tecnico",
        },
        headers=admin_headers,
    )
    assert created.status_code == 200
    user_id = created.json()["id"]

    updated = client.put(
        f"/api/identity/users/{user_id}",
        json={"role": "legal", "status": "active", "agency": "Equipo Legal"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "legal"
    assert updated.json()["agency"] == "Equipo Legal"

    reset = client.post(
        f"/api/identity/users/{user_id}/reset-password",
        json={"password": "NewPassword123!"},
        headers=admin_headers,
    )
    assert reset.status_code == 200

    login = client.post("/api/identity/login", json={"email": "junior@test.local", "password": "NewPassword123!"})
    assert login.status_code == 200


def test_non_admin_cannot_manage_users(client, admin_headers):
    created = client.post(
        "/api/identity/users",
        json={
            "name": "Analista sin admin",
            "email": "noadmin@test.local",
            "role": "analista",
            "password": "AnalystPassword123!",
        },
        headers=admin_headers,
    )
    assert created.status_code == 200
    login = client.post("/api/identity/login", json={"email": "noadmin@test.local", "password": "AnalystPassword123!"})
    token = login.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {token}"}

    users = client.get("/api/identity/users", headers=analyst_headers)
    assert users.status_code == 403

    update = client.put(
        f"/api/identity/users/{created.json()['id']}",
        json={"role": "admin"},
        headers=analyst_headers,
    )
    assert update.status_code == 403


def test_inactive_user_cannot_login(client, admin_headers):
    created = client.post(
        "/api/identity/users",
        json={
            "name": "Usuario Inactivo",
            "email": "inactive@test.local",
            "role": "analista",
            "password": "InactivePassword123!",
        },
        headers=admin_headers,
    )
    assert created.status_code == 200
    user_id = created.json()["id"]

    updated = client.put(
        f"/api/identity/users/{user_id}",
        json={"status": "inactive"},
        headers=admin_headers,
    )
    assert updated.status_code == 200

    login = client.post("/api/identity/login", json={"email": "inactive@test.local", "password": "InactivePassword123!"})
    assert login.status_code == 403
