import base64
import hashlib
import hmac
import json
from pathlib import Path
import subprocess
import sys
import time
import pytest
from apps.api.main import app
from operia.core.config import settings
from operia.identity.models import Organization, User, AuthToken
from operia.identity.security import hash_password, hash_token, verify_password, create_access_token, verify_access_token, _secret, _stored_secret
from operia.security import outbound
from operia.security.context import ConnectorScope, connector_scope
from test_native_mobile_workflow import database_factory


@pytest.fixture(autouse=True)
def reset_connector_budgets():
    with outbound._lock:
        outbound._calls.clear()
        outbound._active.clear()


def second_tenant(client):
    with database_factory()() as db:
        org = Organization(name="Isolated tenant", slug="isolated")
        db.add(org); db.flush()
        user = User(organization_id=org.id, name="Other admin", email="audit-other@test.local", role="admin", password_hash=hash_password("OtherPassword123!"))
        db.add(user); db.commit(); org_id, user_id = org.id, user.id
    response = client.post("/api/identity/login", json={"email": "audit-other@test.local", "password": "OtherPassword123!"})
    assert response.status_code == 200, response.text
    return org_id, user_id, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_signing_key_random_persistent_and_no_predictable_fallback(client, monkeypatch):
    key = _secret()
    assert len(key) >= 32 and key != f"{settings.app_name}:{settings.database_url}".encode()
    _stored_secret.cache_clear()
    assert _secret() == key
    token, _ = create_access_token(1, 1, "admin")
    assert verify_access_token(token)
    body = token.split(".")[0]
    forged = body + "." + hmac.new(f"{settings.app_name}:{settings.database_url}".encode(), body.encode(), hashlib.sha256).hexdigest()
    assert verify_access_token(forged) is None
    path = settings.storage_dir / ".auth-signing-key"
    path.write_bytes(b"corrupt")
    _stored_secret.cache_clear()
    with pytest.raises(RuntimeError): _secret()


def test_password_upgrade_preserves_legacy_login(client, admin_headers):
    salt, password = "legacy-synthetic-salt", "TestPassword123!"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    old = f"pbkdf2_sha256${salt}${digest}"
    assert verify_password(password, old)
    assert not verify_password("incorrect", old)
    assert hash_password(password).startswith("pbkdf2_sha256$600000$")
    with database_factory()() as db:
        db.get(User, 1).password_hash = old; db.commit()
    assert client.post("/api/identity/login", json={"email": "admin@test.local", "password": password}).status_code == 200
    with database_factory()() as db:
        assert db.get(User, 1).password_hash.startswith("pbkdf2_sha256$600000$")


def test_admin_cannot_create_or_move_users_across_tenants(client, admin_headers):
    org_id, user_id, other_headers = second_tenant(client)
    assert client.post("/api/identity/users", headers=admin_headers, json={"name": "Injected", "email": "injected@test.local", "organization_id": org_id, "password": "StrongPassword123!"}).status_code == 403
    assert client.put("/api/identity/users/1", headers=admin_headers, json={"organization_id": org_id}).status_code == 403
    assert client.post("/api/identity/users", headers=admin_headers, json={"name": "No secret", "email": "no@test.local"}).status_code == 422
    assert client.post("/api/identity/organizations", headers=admin_headers, json={"name": "Injected", "slug": "injected"}).status_code == 403
    assert client.post("/api/identity/users/1/reset-password", headers=admin_headers, json={"password": "x" * 1025}).status_code == 422
    assert client.post(f"/api/identity/users/{user_id}/reset-password", headers=admin_headers, json={"password": "StrongPassword123!"}).status_code == 403
    assert [u["id"] for u in client.get("/api/identity/users", headers=admin_headers).json()] == [1]
    with database_factory()() as db:
        # An out-of-band account move must not turn an old session into a tenant switch.
        db.get(User, 1).organization_id = org_id; db.commit()
    assert client.get("/api/identity/me", headers=admin_headers).json()["authenticated"] is False
    assert client.get("/api/cases", headers=admin_headers).status_code == 401


def test_mind_files_unique_between_tenants_and_cross_case_links_rejected(client, admin_headers):
    org_id, user_id, other_headers = second_tenant(client)
    payload = {"title": "Identical title", "content": "First preserved content"}
    first = client.post("/api/mind/notes", headers=admin_headers, json=payload)
    second = client.post("/api/mind/notes", headers=other_headers, json={**payload, "content": "Other preserved content"})
    assert first.status_code == second.status_code == 200
    from operia.mind.vault import vault_root
    p1, p2 = (vault_root() / response.json()["vault_path"] for response in (first, second))
    assert p1 != p2 and "First preserved content" in p1.read_text(encoding="utf-8")
    assert "Other preserved content" in p2.read_text(encoding="utf-8")
    assert client.get(f"/api/mind/notes/{first.json()['id']}", headers=other_headers).status_code == 404
    cases = [client.post("/api/cases", headers=admin_headers, json={"case_code": "AUDIT-"+str(i), "title": "Synthetic"}).json()["id"] for i in (1, 2)]
    nodes = [client.post("/api/mind/graph/nodes", headers=admin_headers, json={"case_id": case, "node_type": "url", "label": "Same label"}).json()["node_key"] for case in cases]
    assert client.post("/api/mind/graph/edges", headers=admin_headers, json={"case_id": cases[0], "source_node_key": nodes[0], "target_node_key": nodes[1], "relation_type": "sostiene"}).status_code == 422
    evidence = client.post("/api/evidence", headers=admin_headers, json={"case_id": cases[1], "description": "Other case"}).json()
    assert client.post("/api/mind/notes", headers=admin_headers, json={"case_id": cases[0], "title": "Cross case", "linked_evidence": [evidence["id"]]}).status_code == 422


def test_vault_cannot_escape_or_overwrite_preserved_files(client):
    from operia.mind.vault import write_note
    from fastapi import HTTPException
    with pytest.raises(HTTPException): write_note("../escape.md", "text")
    path = write_note("organizations/1/test.md", "preserved", exclusive=True)
    with pytest.raises(FileExistsError): write_note("organizations/1/test.md", "overwrite", exclusive=True)
    assert path.read_text() == "preserved"


def test_connector_requires_org_and_purpose_policy_in_request_context(client, admin_headers, monkeypatch):
    org_id, user_id, other_headers = second_tenant(client)
    monkeypatch.setattr(settings, "connector_allowed_hosts", ["provider.example"])
    calls = []
    def fake(payload, timeout, maximum):
        scope = connector_scope.get(); calls.append((scope.organization_id, scope.actor_id, payload["url"]))
        return 200, b"synthetic metadata"
    monkeypatch.setattr(outbound, "_run_transport", fake)
    with database_factory()() as db:
        db.get(Organization, 1).settings_json = json.dumps({"connectors": {"legal_source": {"enabled": True, "hosts": ["provider.example"]}}})
        db.get(Organization, org_id).settings_json = json.dumps({"connectors": {"geo_ip": {"enabled": True, "hosts": ["provider.example"]}}})
        db.commit()
    url = "/api/legal-knowledge/sources/verify-url"
    assert client.post(url, headers=admin_headers, json={"url": "https://provider.example/"}).json()["reachable"] is True
    assert client.post(url, headers=other_headers, json={"url": "https://provider.example/"}).json()["reachable"] is False
    assert calls == [(1, 1, "https://provider.example/")]
    assert connector_scope.get() is None
    with pytest.raises(outbound.ConnectorRejected, match="scope_required"): outbound.fetch_bytes("https://provider.example/")


def test_connector_budget_deadline_and_tenant_bulkheads(monkeypatch):
    one, other = ConnectorScope(1, 1, 1), ConnectorScope(2, 2, 2)
    with outbound.connector_slot(one):
        with pytest.raises(outbound.ConnectorRejected, match="capacity"):
            with outbound.connector_slot(one): pass
        with outbound.connector_slot(other): pass
    assert not outbound._active
    token = connector_scope.set(ConnectorScope(1, 1, 1, frozenset({("generic", "provider.example")}), deadline=time.monotonic()-1))
    monkeypatch.setattr(settings, "connector_allowed_hosts", ["provider.example"])
    try:
        with pytest.raises(outbound.ConnectorRejected, match="deadline"): outbound.fetch_bytes("https://provider.example/")
    finally: connector_scope.reset(token)


def test_connector_dispatches_fixed_kind_and_bounds_pipe(monkeypatch):
    captured = {}
    monkeypatch.setenv("HTTP_PROXY", "http://not-used.invalid")
    monkeypatch.setenv("OPERIA_AUTH_SIGNING_KEY", "do-not-inherit-this-secret")
    class Process:
        returncode = 0
        def communicate(self, payload=None, timeout=None, maximum=None):
            captured["payload"] = json.loads(payload); captured["maximum"] = maximum
            return b'{"status":200,"body_base64":"b2s="}', None
        def kill(self): pass
        def close(self): captured["closed"] = True
    def spawn(kind): captured["kind"] = kind; return Process()
    monkeypatch.setattr(outbound, "spawn_worker", spawn)
    assert outbound._run_transport({"kind": "https", "url": "https://provider.example/"}, 1, 20) == (200, b"ok")
    assert captured["kind"] == "https" and captured["maximum"] == 4136 and captured["closed"]


def test_connector_timeout_kills_real_child(monkeypatch):
    from operia.security.sandbox_runtime import DEFAULT_ROOT, identity
    from operia.security.windows_sandbox import launch
    children = []
    def sleeping(kind):
        process = launch(DEFAULT_ROOT / identity(), "scripts.sandbox_probe")
        communicate = process.communicate
        process.communicate = lambda payload=None, **kwargs: communicate(b'{"action":"sleep"}', **kwargs)
        children.append(process); return process
    monkeypatch.setattr(outbound, "spawn_worker", sleeping)
    before = time.monotonic()
    with pytest.raises(outbound.ConnectorRejected, match="deadline"):
        outbound._run_transport({"kind": "https"}, .2, 20)
    assert children[0].poll() is not None and time.monotonic() - before < 5


def test_real_connector_child_refuses_private_destination(monkeypatch):
    monkeypatch.setattr(settings, "connector_allowed_hosts", ["127.0.0.1"])
    token = connector_scope.set(ConnectorScope(1, 1, 1, frozenset({("generic", "127.0.0.1")})))
    try:
        with pytest.raises(outbound.ConnectorRejected, match="destination_rejected"):
            outbound.fetch_bytes("https://127.0.0.1/")
    finally: connector_scope.reset(token)
