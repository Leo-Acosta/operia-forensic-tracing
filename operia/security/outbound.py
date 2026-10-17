"""Tenant/purpose grants, process isolation, per-tenant budgets and bounded output."""
import base64
from contextlib import contextmanager
import json
import logging
import re
import subprocess
from threading import Lock
import time
from urllib.parse import urlsplit
from operia.core.config import settings
from operia.security.context import connector_scope
from operia.security.errors import ConnectorRejected
from operia.forensic_engine.canonical import read_json
from operia.security.sandbox_runtime import spawn_worker
from operia.security.windows_sandbox import SandboxUnavailable

_lock = Lock()
_active = {}
_calls = {}

@contextmanager
def connector_slot(scope):
    now = time.monotonic()
    with _lock:
        for key in list(_calls):
            if now - _calls[key][0] >= 60:
                del _calls[key]
        if sum(_active.values()) >= 4 or _active.get(scope.organization_id, 0) >= 1:
            raise ConnectorRejected("connector_capacity_exceeded")
        if len(_calls) >= 1024 and scope.organization_id not in _calls:
            raise ConnectorRejected("connector_capacity_exceeded")
        since, count = _calls.get(scope.organization_id, (now, 0))
        if count >= 20:
            raise ConnectorRejected("connector_rate_exceeded")
        _calls[scope.organization_id] = (since, count + 1)
        _active[scope.organization_id] = _active.get(scope.organization_id, 0) + 1
    try:
        yield
    finally:
        with _lock:
            _active[scope.organization_id] -= 1
            if not _active[scope.organization_id]:
                del _active[scope.organization_id]


def _run_transport(payload, timeout, maximum):
    started = time.monotonic()
    try:
        process = spawn_worker(payload["kind"])
        try:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise ConnectorRejected("connector_deadline_exceeded")
            output, _ = process.communicate(json.dumps(payload, ensure_ascii=True).encode(),
                timeout=remaining, maximum=maximum * 2 + 4096)
        except subprocess.TimeoutExpired:
            raise ConnectorRejected("connector_deadline_exceeded") from None
        finally:
            process.close()
    except SandboxUnavailable:
        raise ConnectorRejected("connector_sandbox_unavailable") from None
    if process.returncode != 0 or len(output) > maximum * 2 + 4096:
        raise ConnectorRejected("connector_worker_error")
    try:
        result = read_json(output, limit=maximum * 2 + 4096)
        if "error" in result:
            code = result["error"]
            raise ConnectorRejected(code if isinstance(code, str) and re.fullmatch(r"connector_[a-z_]{1,60}", code) else "connector_worker_error")
        raw = base64.b64decode(result["body_base64"], validate=True)
        status = result["status"]
        if len(raw) > maximum or not isinstance(status, int) or not 100 <= status <= 599:
            raise ValueError()
        return status, raw
    except (ValueError, KeyError, TypeError):
        raise ConnectorRejected("connector_invalid_response") from None


def _invoke(payload, maximum):
    scope = connector_scope.get()
    if scope is None or not scope.organization_id or not scope.actor_id:
        raise ConnectorRejected("connector_scope_required")
    remaining = min(scope.deadline - time.monotonic(), float(payload.get("timeout", 8)) + 2, 12)
    if remaining <= 0:
        raise ConnectorRejected("connector_deadline_exceeded")
    outcome = "rejected"
    try:
        with connector_slot(scope):
            result = _run_transport(payload, remaining, maximum)
        outcome = "completed"
        return result
    finally:
        logging.getLogger("operia.security").info("connector_operation org=%s actor=%s case=%s purpose=%s outcome=%s request_id=%s", scope.organization_id, scope.actor_id, scope.case_id, payload["kind"], outcome, scope.request_id)


def fetch_bytes(url, timeout=8, maximum=256 * 1024, *, purpose="generic"):
    scope = connector_scope.get()
    if scope is None:
        raise ConnectorRejected("connector_scope_required")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower()
        if len(url) > 4096 or parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443) or "\\" in url or any(ord(c) < 33 or ord(c) == 127 for c in url):
            raise ValueError()
        if host not in settings.connector_allowed_hosts or (purpose, host) not in scope.grants or not 1 <= maximum <= 256 * 1024:
            raise ValueError()
    except (ValueError, UnicodeError, TypeError):
        raise ConnectorRejected("connector_destination_rejected") from None
    return _invoke({"kind": "https", "url": url, "timeout": timeout, "maximum": maximum, "allowed_hosts": [host]}, maximum)


def fetch_json(url, timeout=8, *, purpose="generic"):
    status, raw = fetch_bytes(url, timeout, purpose=purpose)
    if status != 200:
        raise ConnectorRejected("connector_http_error")
    try:
        result = read_json(raw, limit=256 * 1024)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except ValueError:
        raise ConnectorRejected("connector_invalid_json") from None


def local_ai(prompt, model, timeout):
    from operia.security.ai_gateway import generate
    return generate(prompt, model, timeout)
