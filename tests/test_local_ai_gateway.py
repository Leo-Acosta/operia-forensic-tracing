"""Gateway tests use synthetic HTTP provider and real no-network AppContainers."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import threading
import time

import pytest
from operia.core.config import settings
from operia.security import ai_gateway as gateway, outbound
from operia.security.context import ConnectorScope, connector_scope
from operia.security.errors import ConnectorRejected
from operia.security.sandbox_runtime import prepare, spawn_worker
from test_native_mobile_workflow import database_factory
from test_security_audit import second_tenant


@pytest.fixture(scope="module", autouse=True)
def runtime(): prepare()


@pytest.fixture()
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "local_ai_enabled", True)
    monkeypatch.setattr(settings, "local_ai_gateway_enabled", True)
    monkeypatch.setattr(settings, "local_ai_allowed_models", ["mistral"])
    token = connector_scope.set(ConnectorScope(1, 1, 7, local_ai=True, local_ai_models=frozenset({"mistral"})))
    with outbound._lock: outbound._calls.clear(); outbound._active.clear()
    yield
    connector_scope.reset(token)


@pytest.fixture()
def provider(monkeypatch):
    state = {"raw": b'{"response":"synthetic reply","done":true,"context":[1,2]}', "status": 200,
        "type": "application/json", "encoding": "identity", "calls": [], "slow": False, "slow_body": False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            state["calls"].append((self.path, dict(self.headers), json.loads(raw)))
            try:
                if state["slow"]:
                    self.wfile.write(b"HTTP/1.1 200 OK\r\nX-Trickle: ")
                    for _ in range(100): self.wfile.write(b"x"); self.wfile.flush(); time.sleep(.03)
                    return
                self.send_response(state["status"])
                self.send_header("Content-Type", state["type"])
                self.send_header("Content-Encoding", state["encoding"])
                self.send_header("Content-Length", "100" if state["slow_body"] else str(len(state["raw"])))
                self.end_headers()
                if state["slow_body"]:
                    for _ in range(100): self.wfile.write(b"x"); self.wfile.flush(); time.sleep(.03)
                else: self.wfile.write(state["raw"])
            except OSError: pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True); thread.start()
    original = http.client.HTTPConnection
    def connection(host, port, timeout):
        assert host == "127.0.0.1" and port == 11434
        return original(host, server.server_port, timeout=timeout)
    monkeypatch.setattr(gateway.http.client, "HTTPConnection", connection)
    try: yield state
    finally: server.shutdown(); server.server_close(); thread.join(2)


def test_real_gateway_uses_fixed_protocol_and_never_reuses_provider_context(enabled, provider, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://not-used.invalid")
    for text in ("first case prompt", "second case prompt"):
        assert gateway.generate(text, "mistral", 10) == "synthetic reply"
    assert len(provider["calls"]) == 2
    for path, headers, data in provider["calls"]:
        assert path == "/api/generate" and "Authorization" not in headers and "Cookie" not in headers
        assert set(data) == {"model", "prompt", "stream", "keep_alive", "options"}
        assert data["keep_alive"] == 0 and data["stream"] is False
        assert data["options"] == {"temperature": 0, "num_ctx": 4096, "num_predict": 512}
    assert provider["calls"][1][2]["prompt"] == "second case prompt"


@pytest.mark.parametrize("missing", ["global", "gateway", "organization", "actor", "case", "models", "scope"])
def test_authorization_fails_before_provider(enabled, provider, monkeypatch, missing):
    scope = ConnectorScope(1, 1, 7, local_ai=True, local_ai_models=frozenset({"mistral"}))
    if missing == "global": monkeypatch.setattr(settings, "local_ai_enabled", False)
    elif missing == "gateway": monkeypatch.setattr(settings, "local_ai_gateway_enabled", False)
    elif missing == "organization": scope = ConnectorScope(1, 1, 7)
    elif missing == "actor": scope = ConnectorScope(0, 1, 7, local_ai=True)
    elif missing == "case": scope = ConnectorScope(1, 1, None, local_ai=True)
    elif missing == "models": scope = ConnectorScope(1, 1, 7, local_ai=True)
    elif missing == "scope": scope = None
    token = connector_scope.set(scope)
    try:
        with pytest.raises(ConnectorRejected): gateway.generate("synthetic", "mistral", 5)
    finally: connector_scope.reset(token)
    assert provider["calls"] == []


@pytest.mark.parametrize("model", ["../mistral", "https://host.invalid/mistral", "mistral-cloud", "other", "x" * 121])
def test_model_injection_denied(enabled, provider, model):
    with pytest.raises(ConnectorRejected, match="model_rejected"): gateway.generate("synthetic", model, 5)
    assert provider["calls"] == []


@pytest.mark.parametrize("raw", [b'{"response":"a","response":"b","done":true}', b'{"response":NaN,"done":true}', b'{"response":"partial","done":false}', b'{"response":{},"done":true}', b'{"response":"","done":true}', b'{"response":"x","done":true,"error":"no"}', b'[' * 25 + b']' * 25])
def test_hostile_provider_responses_rejected_in_appcontainer(enabled, provider, raw):
    provider["raw"] = raw
    with pytest.raises(ConnectorRejected): gateway.generate("synthetic", "mistral", 10)


@pytest.mark.parametrize("field,value", [("status", 302), ("status", 500), ("type", "text/html"), ("encoding", "gzip"), ("raw", b"x" * (256 * 1024 + 1))], ids=["redirect", "server-error", "html", "compressed", "oversize"])
def test_http_boundary_rejects_redirect_encoding_and_volume(enabled, provider, field, value):
    provider[field] = value
    with pytest.raises(ConnectorRejected): gateway.generate("synthetic", "mistral", 10)


@pytest.mark.parametrize("field", ["slow", "slow_body"])
def test_deadline_interrupts_trickling_headers_and_releases_capacity(enabled, provider, field):
    provider[field] = True
    before = time.monotonic()
    with pytest.raises(ConnectorRejected): gateway._exchange(b"{}", time.monotonic() + .3)
    assert time.monotonic() - before < 2
    provider[field] = False
    assert gateway.generate("after timeout", "mistral", 10) == "synthetic reply"


def test_prompt_limit_capacity_and_no_sandbox_fallback(enabled, provider, monkeypatch):
    with pytest.raises(ConnectorRejected): gateway.generate("x" * (64 * 1024 + 1), "mistral", 10)
    assert gateway._capacity.acquire(blocking=False)
    try:
        with pytest.raises(ConnectorRejected, match="capacity"): gateway.generate("synthetic", "mistral", 10)
    finally: gateway._capacity.release()
    from operia.security.windows_sandbox import SandboxUnavailable
    monkeypatch.setattr(gateway, "spawn_worker", lambda kind: (_ for _ in ()).throw(SandboxUnavailable("synthetic denial")))
    with pytest.raises(ConnectorRejected, match="validation_unavailable"): gateway.generate("synthetic", "mistral", 10)
    assert provider["calls"] == []


def test_compromised_validator_cannot_change_model_or_add_tools(enabled, provider, monkeypatch):
    monkeypatch.setattr(gateway, "_validate", lambda payload, deadline: {"model": "remote-cloud", "tools": ["shell"]})
    with pytest.raises(ConnectorRejected, match="invalid_protocol"): gateway.generate("synthetic", "mistral", 10)
    assert provider["calls"] == []


def test_gateway_api_scopes_and_minimal_context_preserves_history(client, admin_headers, provider, monkeypatch):
    from operia.identity.models import Organization
    from operia.ai_assistant.models import AIInteraction
    from operia.cases.models import Case
    monkeypatch.setattr(settings, "local_ai_enabled", True)
    monkeypatch.setattr(settings, "local_ai_gateway_enabled", True)
    with outbound._lock: outbound._calls.clear(); outbound._active.clear()
    org, _, other_headers = second_tenant(client)
    with database_factory()() as db:
        db.get(Organization, 1).settings_json = json.dumps({"connectors": {"local_ai": {"enabled": True, "models": ["mistral"]}}})
        db.commit()
    own = client.post("/api/cases", headers=admin_headers, json={"case_code": "AI-ONE", "title": "First", "description": "SENSITIVE_CASE_ONE"}).json()["id"]
    other = client.post("/api/cases", headers=other_headers, json={"case_code": "AI-TWO", "title": "Other", "description": "SENSITIVE_CASE_TWO"}).json()["id"]
    response = client.post("/api/ai/assist", headers=admin_headers, json={"case_id": own, "prompt": "Synthetic"})
    assert response.status_code == 200 and response.json()["status"] == "completed"
    first_id = response.json()["id"]
    assert "SENSITIVE_CASE_ONE" not in provider["calls"][-1][2]["prompt"]
    response = client.post("/api/ai/assist", headers=admin_headers, json={"case_id": own, "prompt": "Synthetic", "include_case_context": True})
    assert response.json()["status"] == "completed"
    assert "SENSITIVE_CASE_ONE" in provider["calls"][-1][2]["prompt"] and "SENSITIVE_CASE_TWO" not in provider["calls"][-1][2]["prompt"]
    assert client.post("/api/ai/assist", headers=admin_headers, json={"case_id": other, "prompt": "Cross"}).status_code == 404
    denied = client.post("/api/ai/assist", headers=other_headers, json={"case_id": other, "prompt": "Disabled tenant"})
    assert denied.json()["status"] == "ollama_unavailable"
    missing = client.post(f"/api/ai/assist?case_id={own}", headers=admin_headers, json={"prompt": "Missing case"})
    assert missing.status_code == 422
    health = client.get("/api/ai/health", headers=admin_headers).json()
    assert health["gateway_ready"] and not health["provider_probed"]
    assert len(provider["calls"]) == 2
    with database_factory()() as db:
        db.get(Organization, org).settings_json = json.dumps({"connectors": {"local_ai": {"enabled": True, "models": ["mistral"]}}})
        db.commit()
    allowed_other = client.post("/api/ai/assist", headers=other_headers, json={"case_id": other, "prompt": "Synthetic", "include_case_context": True})
    assert allowed_other.json()["status"] == "completed"
    assert "SENSITIVE_CASE_TWO" in provider["calls"][-1][2]["prompt"] and "SENSITIVE_CASE_ONE" not in provider["calls"][-1][2]["prompt"]
    from apps.api.main import app
    from operia.identity.dependencies import get_optional_user, CurrentUser
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 1, "Reader", None, "lector")
    try:
        assert client.post("/api/ai/assist", json={"case_id": own, "prompt": "Denied role"}).status_code == 403
    finally: app.dependency_overrides.pop(get_optional_user)
    assert len(provider["calls"]) == 3
    with database_factory()() as db:
        first = db.get(AIInteraction, first_id)
        assert first.response == "synthetic reply" and first.case_id == own and first.organization_id == 1
        assert first.requires_human_review
        assert db.get(Case, own).description == "SENSITIVE_CASE_ONE"


def test_new_gateway_worker_has_no_network_capability(monkeypatch):
    import operia.security.sandbox_runtime as sandbox
    observed = []
    original = sandbox.launch
    def launch(*args, **kwargs): observed.append(kwargs["internet"]); return original(*args, **kwargs)
    monkeypatch.setattr(sandbox, "launch", launch)
    child = spawn_worker("ai_gateway")
    try:
        data, _ = child.communicate(b'{"action":"prepare","model":"mistral","prompt":"synthetic"}', timeout=5)
        assert child.returncode == 0 and json.loads(data)["keep_alive"] == 0
    finally: child.close()
    assert observed == [False]


def test_case_context_is_bounded_without_rewriting_records(client, admin_headers):
    from operia.ai_assistant.service import case_context_for_prompt, bounded_context
    from operia.cases.models import Case
    from operia.evidence.models import Evidence
    case_id = client.post("/api/cases", headers=admin_headers, json={"case_code": "LONG-AI", "title": "Synthetic"}).json()["id"]
    original = "漢" * 10000
    with database_factory()() as db:
        case = db.get(Case, case_id); case.description = original
        for index in range(10):
            db.add(Evidence(case_id=case_id, organization_id=1, description=f"ROW_{index}_" + original))
        db.commit()
        context = case_context_for_prompt(case, db)
        assert len(context.encode()) <= 8192 and "ROW_9_" not in context
        assert db.get(Case, case_id).description == original
        assert len(bounded_context(original, 4096).encode()) <= 4096


def test_invalid_context_consent_and_missing_case_do_not_generate(client, admin_headers, provider):
    assert client.post("/api/ai/assist", headers=admin_headers, json={"prompt": "x", "include_case_context": "false"}).status_code == 422
    assert client.post("/api/ai/assist", headers=admin_headers, json={"prompt": "x", "include_case_context": True}).status_code == 422
    assert client.post("/api/ai/assist", headers=admin_headers, json={"prompt": "x" * 32769}).status_code == 422
    assert not provider["calls"]
