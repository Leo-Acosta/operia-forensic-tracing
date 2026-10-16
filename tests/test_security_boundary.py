import asyncio
import socket
import pytest
from fastapi import HTTPException
from operia.core.config import settings
from operia.security import outbound
from operia.security.limits import reset_limits
from operia.security.middleware import SecurityBoundary


@pytest.mark.parametrize("url", ["http://provider.example/a", "https://127.0.0.1/", "https://[::1]/", "https://metadata.google.internal/", "file:///etc/passwd", "https://provider.example@evil.invalid/", "https://provider.example:444/", "https://provider.example/a#fragment", "https://provider.example/\r\nX:a", "https://provider.example.evil.invalid/"])
def test_unapproved_connector_is_rejected_before_dns(monkeypatch, url):
    monkeypatch.setattr(settings, "connector_allowed_hosts", ["provider.example"])
    def fail(*args, **kwargs):
        raise AssertionError("No DNS for unapproved URL")
    monkeypatch.setattr(outbound.socket, "getaddrinfo", fail)
    with pytest.raises(outbound.ConnectorRejected):
        outbound.fetch_bytes(url)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "192.168.1.1", "::1", "fe80::1", "::ffff:8.8.8.8", "224.0.0.1", "2002:0808:0808::1"])
def test_connector_blocks_internal_special_and_mixed_dns(monkeypatch, address):
    monkeypatch.setattr(settings, "connector_allowed_hosts", ["provider.example"])
    monkeypatch.setattr(outbound.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", (address, 443))])
    with pytest.raises(outbound.ConnectorRejected):
        outbound.fetch_bytes("https://provider.example/")


def test_connector_pins_dns_rejects_redirects_and_bounds_bytes(monkeypatch):
    monkeypatch.setattr(settings, "connector_allowed_hosts", ["provider.example"])
    calls = []
    monkeypatch.setattr(outbound.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443))])
    class Response:
        status = 200
        data = b'{"ok":true}'
        def getheader(self, name, default=None): return default
        def read1(self, size):
            result, self.data = self.data[:size], self.data[size:]
            return result
    response = Response()
    class Connection:
        sock = None
        def __init__(self, host, address, timeout): calls.append((host, address))
        def request(self, *a, **k): pass
        def getresponse(self): return response
        def close(self): pass
    monkeypatch.setattr(outbound, "PinnedHTTPS", Connection)
    assert outbound.fetch_json("https://provider.example/data") == {"ok": True}
    assert calls == [("provider.example", "8.8.8.8")]
    response.status = 302
    with pytest.raises(outbound.ConnectorRejected, match="redirect"):
        outbound.fetch_bytes("https://provider.example/data")
    response.status, response.data = 200, b"x" * 100
    with pytest.raises(outbound.ConnectorRejected, match="too_large"):
        outbound.fetch_bytes("https://provider.example/data", maximum=10)


def test_rate_limit_headers_origin_and_recovery_default(client, monkeypatch):
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"
    assert client.post("/api/identity/login", headers={"Origin": "https://evil.invalid"}, json={}).status_code == 403
    assert client.post("/api/identity/local-admin-recovery", json={}).status_code == 403
    reset_limits()
    monkeypatch.setattr(settings, "http_requests_per_minute", 3)
    for _ in range(3): assert client.get("/api/health").status_code == 200
    response = client.get("/api/health", headers={"X-Forwarded-For": "8.8.8.8"})
    assert response.status_code == 429 and response.headers["retry-after"] == "60"


def test_streamed_body_limit_before_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "http_max_body_bytes", 16)
    reset_limits()
    called, sent = [], []
    async def app(scope, receive, send): called.append(True)
    async def run():
        messages = iter([{"type": "http.request", "body": b"a"*10, "more_body": True}, {"type": "http.request", "body": b"b"*10, "more_body": False}])
        async def receive(): return next(messages)
        async def send(message): sent.append(message)
        await SecurityBoundary(app)({"type": "http", "path": "/api/test", "method": "POST", "headers": [], "client": ("peer", 1)}, receive, send)
    asyncio.run(run())
    assert not called and sent[0]["status"] == 413


def test_shell_ai_and_geo_evidence_urls_are_not_executed(monkeypatch):
    from operia.cybercrime.services import run_lab_command
    from operia.ai_assistant.ollama_client import generate_with_ollama, OllamaUnavailable
    from operia.geo_trace.services import analyze_url, create_target_map
    from operia.legal_knowledge.service import verify_source_url
    monkeypatch.setattr(settings, "connector_allowed_hosts", [])
    monkeypatch.setattr(settings, "local_ai_enabled", False)
    with pytest.raises(HTTPException): run_lab_command("echo user && arbitrary-command")
    with pytest.raises(OllamaUnavailable): generate_with_ollama("prompt", base_url="http://169.254.169.254")
    monkeypatch.setattr(socket, "gethostbyname", lambda *a: pytest.fail("No DNS"))
    assert analyze_url("http://127.0.0.1:8000/private")["ip"] is None
    assert not verify_source_url("http://127.0.0.1:8000/private")["reachable"]


def test_geo_map_inert_and_connector_limits(client, admin_headers):
    from operia.geo_trace.services import create_target_map
    path = create_target_map([{"lat": -34, "lon": -58, "host": "<script>alert(1)</script>"}], "../../escape.html")
    text = path.read_text(encoding="utf-8")
    assert "<script>" not in text and "&lt;script&gt;" in text
    assert str(path.resolve()).startswith(str(settings.maps_dir.resolve()))
    assert "https://" not in text
    case = client.post("/api/cases", headers=admin_headers, json={"case_code": "SECURITY-GEO", "title": "Synthetic"}).json()
    response = client.post("/api/geo/trace/analyze", headers=admin_headers, json={"case_id": case["id"], "input_text": "http://127.0.0.1/private"})
    assert response.status_code == 200, response.text
    assert any(t["target_type"] == "observado_no_enriquecido" for t in response.json()["targets"])
    assert client.post("/api/geo/trace/analyze", headers=admin_headers, json={"case_id": case["id"], "input_text": "a"*16385}).status_code == 422


def test_concurrency_bound_is_released(monkeypatch):
    monkeypatch.setattr(settings, "http_max_concurrent_requests", 1)
    reset_limits()
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def app(scope, receive, send):
            entered.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        middleware = SecurityBoundary(app)
        scope = {"type": "http", "path": "/api/test", "method": "GET", "headers": [], "client": ("peer", 1)}
        async def receive(): return {"type": "http.request", "body": b""}
        first, second = [], []
        async def send_first(message): first.append(message)
        async def send_second(message): second.append(message)
        task = asyncio.create_task(middleware(scope, receive, send_first))
        await entered.wait()
        await middleware(scope, receive, send_second)
        assert second[0]["status"] == 503
        release.set()
        await task
        second.clear()
        await middleware(scope, receive, send_second)
        assert second[0]["status"] == 200
    asyncio.run(run())


def test_reader_cannot_use_write_aliases(client, admin_headers):
    from apps.api.main import app
    from operia.identity.dependencies import get_optional_user, CurrentUser
    case = client.post("/api/cases", headers=admin_headers, json={"case_code": "READER-GUARD", "title": "Fixture"}).json()
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 1, "Reader", None, "lector")
    assert client.post(f"/api/legal/cases/{case['id']}/analysis?apply=true").status_code == 403
    app.dependency_overrides.pop(get_optional_user)


@pytest.mark.parametrize("raw", [b'{"email":"a","email":"b"}', b'{"x":NaN}', b'['*25 + b']'*25])
def test_ambiguous_json_rejected(client, raw):
    assert client.post("/api/identity/login", content=raw, headers={"Content-Type": "application/json"}).status_code == 422


def test_connector_network_calls_remain_centralized():
    import ast
    from pathlib import Path
    approved = {"operia/security/outbound.py", "operia/ai_assistant/ollama_client.py"}
    forbidden = []
    for file in Path("operia").rglob("*.py"):
        if file.as_posix() in approved:
            continue
        tree = ast.parse(file.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                forbidden.append(str(file))
            target = ast.unparse(node.func)
            if target.startswith(("requests.get", "requests.post", "httpx.get", "httpx.post", "urllib.request.urlopen", "socket.gethostbyname", "socket.create_connection")) or target == "urlopen":
                forbidden.append(str(file))
    assert not forbidden
