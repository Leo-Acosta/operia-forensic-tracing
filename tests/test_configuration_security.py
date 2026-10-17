"""Configuration is administrative metadata, never a secret delivery endpoint."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

from apps.api.main import app
from operia.core.config import settings
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.security.safe_errors import install_safe_errors


@pytest.mark.parametrize("path", ["/api/settings/", "/api/settings/readiness"])
def test_anonymous_configuration_rejected_before_diagnostic(client, monkeypatch, path):
    import operia.settings.router as router
    def forbidden():
        pytest.fail("Unauthorized diagnostic was executed")
    monkeypatch.setattr(router, "migration_status", forbidden)
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid-synthetic"}).status_code == 401


@pytest.mark.parametrize("role", ["lector", "analista", "legal", "coordinador"])
@pytest.mark.parametrize("path", ["/api/settings/", "/api/settings/readiness"])
def test_configuration_requires_administrator(client, monkeypatch, role, path):
    import operia.settings.router as router
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 1, "Synthetic", None, role)
    def forbidden():
        pytest.fail("Non-administrative diagnostic was executed")
    monkeypatch.setattr(router, "migration_status", forbidden)
    try:
        assert client.get(path).status_code == 403
    finally:
        app.dependency_overrides.pop(get_optional_user)


def test_administrator_receives_only_allowlisted_metadata(client, admin_headers, monkeypatch):
    import operia.settings.router as router
    sentinel = "SYNTHETIC_SECRET_NOT_REAL_731"
    monkeypatch.setattr(settings, "database_url", f"postgresql://synthetic:{sentinel}@localhost/private?token={sentinel}")
    private_storage_path = str(settings.storage_dir)
    monkeypatch.setattr(router, "migration_status", lambda: {
        "dialect": "sqlite", "current_schema_version": "synthetic-v1", "alembic_heads": ["synthetic"],
        "alembic_available": True, "registered": [{"description": sentinel}], "postgres_ready": False,
        "database_url": sentinel, "unexpected_future_secret": sentinel})
    summary = client.get("/api/settings/", headers=admin_headers)
    readiness = client.get("/api/settings/readiness", headers=admin_headers)
    assert summary.status_code == readiness.status_code == 200
    assert set(summary.json()) == {"app_name", "env", "api_prefix"}
    assert readiness.json()["storage"] == {"mode": "managed_local_storage"}
    assert readiness.json()["database"]["registered_migration_count"] == 1
    assert sentinel not in summary.text + readiness.text
    assert "database_url" not in summary.text + readiness.text
    assert private_storage_path not in summary.text + readiness.text


def test_diagnostic_failure_never_returns_or_logs_driver_message(client, admin_headers, monkeypatch, caplog):
    import operia.settings.router as router
    sentinel = "SYNTHETIC_DRIVER_PASSWORD_842"
    def fail():
        raise RuntimeError(f"postgresql://operator:{sentinel}@localhost/private")
    monkeypatch.setattr(router, "migration_status", fail)
    response = client.get("/api/settings/readiness", headers=admin_headers)
    assert response.status_code == 503
    assert response.json()["detail"] == "settings_readiness_unavailable"
    assert sentinel not in response.text + caplog.text


def test_rejected_identity_input_is_not_echoed(client, caplog):
    sentinel = "SYNTHETIC_REQUEST_PASSWORD_953"
    response = client.post("/api/identity/login", json=[{"password": sentinel}])
    assert response.status_code == 422
    assert response.json()["detail"] == "request_validation_failed"
    assert sentinel not in response.text + caplog.text


def test_database_exception_is_sanitized_in_identity_route(client, caplog):
    sentinel = "SYNTHETIC_SQL_PASSWORD_164"
    class BrokenDatabase:
        def query(self, *args):
            raise OperationalError("synthetic statement", {"password": sentinel}, RuntimeError(sentinel))
    previous = app.dependency_overrides[get_db]
    def broken_database():
        yield BrokenDatabase()
    app.dependency_overrides[get_db] = broken_database
    try:
        response = client.post("/api/identity/login", json={"email": "synthetic@test.local", "password": sentinel})
        assert response.status_code == 503
        assert response.json()["detail"] == "database_operation_failed"
        assert sentinel not in response.text + caplog.text
    finally:
        app.dependency_overrides[get_db] = previous


def test_invalid_response_does_not_echo_internal_values(caplog):
    sentinel = "SYNTHETIC_RESPONSE_SECRET_275"
    local_app = FastAPI()
    install_safe_errors(local_app)
    @local_app.get("/synthetic", response_model=dict[str, int])
    def invalid():
        return {"value": sentinel}
    with TestClient(local_app) as client:
        response = client.get("/synthetic")
    assert response.status_code == 500
    assert response.json()["detail"] == "response_validation_failed"
    assert sentinel not in response.text + caplog.text


def test_migration_diagnostic_is_read_only_and_omits_url(monkeypatch):
    import operia.core.migrations as migrations
    engine = create_engine("sqlite://")
    monkeypatch.setattr(migrations, "engine", engine)
    try:
        result = migrations.migration_status()
        assert result["registered"] == []
        assert inspect(engine).get_table_names() == []
        assert "database_url" not in result
    finally:
        engine.dispose()


def test_identity_does_not_serialize_organization_configuration(client, admin_headers):
    import json
    from operia.identity.models import Organization
    from test_native_mobile_workflow import database_factory
    sentinel = "SYNTHETIC_ORGANIZATION_API_KEY_386"
    configuration = json.dumps({"api_key": sentinel, "connectors": {"local_ai": {"enabled": False}}})
    with database_factory()() as db:
        db.get(Organization, 1).settings_json = configuration
        db.commit()
    response = client.get("/api/identity/organizations", headers=admin_headers)
    assert response.status_code == 200
    assert set(response.json()[0]) == {"id", "name", "slug", "status", "created_at", "updated_at"}
    assert sentinel not in response.text and "settings_json" not in response.text
    with database_factory()() as db:
        assert db.get(Organization, 1).settings_json == configuration
