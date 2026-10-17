"""Trusted fixed-destination loopback broker. Not an HTTP proxy or worker escape.

No listener, user URL, credentials, chat state, file access or tool dispatch.
Untrusted protocol validation runs in disposable no-network AppContainers.
"""
import http.client
import logging
import re
import socket
import subprocess
import threading
import time

from operia.core.config import settings
from operia.forensic_engine.canonical import canonical_bytes, read_json
from operia.security.context import connector_scope
from operia.security.errors import ConnectorRejected
from operia.security.sandbox_runtime import spawn_worker
from operia.security.windows_sandbox import SandboxUnavailable

MAX_RESPONSE = 256 * 1024
_capacity = threading.BoundedSemaphore(1)  # One model operation across tenants/process.


def _validate(payload, deadline):
    process = None
    try:
        process = spawn_worker("ai_gateway")
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise ConnectorRejected("connector_deadline_exceeded")
        raw, _ = process.communicate(canonical_bytes(payload), timeout=remaining, maximum=512 * 1024)
        if process.returncode != 0: raise ConnectorRejected("connector_ai_invalid_protocol")
        result = read_json(raw, limit=512 * 1024)
        if not isinstance(result, dict) or "error" in result: raise ConnectorRejected("connector_ai_invalid_protocol")
        return result
    except (SandboxUnavailable, subprocess.TimeoutExpired, ValueError):
        raise ConnectorRejected("connector_ai_validation_unavailable") from None
    finally:
        if process:
            try: process.close()
            except SandboxUnavailable:
                raise ConnectorRejected("connector_ai_validation_unavailable") from None


def _exchange(body, deadline):
    # Connect to a numeric address: no DNS, proxy environment, configurable port,
    # redirects, cookies or Authorization. This is the only loopback capability.
    remaining = deadline - time.monotonic()
    if remaining <= 0: raise ConnectorRejected("connector_deadline_exceeded")
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=min(remaining, 2))
    expired = threading.Event()
    connected = {}
    def interrupt():
        expired.set()
        sock = connected.get("socket")
        if sock:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            sock.close()
    timer = threading.Timer(remaining, interrupt); timer.daemon = True
    timer.start()
    response = None
    try:
        connection.connect()
        connected["socket"] = connection.sock
        if expired.is_set(): raise ConnectorRejected("connector_deadline_exceeded")
        # The short connect budget must not become a two-second inference limit.
        # The watchdog still bounds the complete exchange, including trickle I/O.
        connection.sock.settimeout(max(.001, deadline - time.monotonic()))
        connection.request("POST", "/api/generate", body=body,
            headers={"Content-Type": "application/json", "Accept-Encoding": "identity", "Connection": "close"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ConnectorRejected("connector_ai_http_rejected")
        if response.getheader("Content-Type", "").split(";", 1)[0].lower() != "application/json":
            raise ConnectorRejected("connector_ai_content_type_rejected")
        data = bytearray()
        while True:
            if expired.is_set(): raise ConnectorRejected("connector_deadline_exceeded")
            chunk = response.read1(min(16384, MAX_RESPONSE + 1 - len(data)))
            if not chunk: break
            data.extend(chunk)
            if len(data) > MAX_RESPONSE: raise ConnectorRejected("connector_ai_response_too_large")
        if expired.is_set(): raise ConnectorRejected("connector_deadline_exceeded")
        return bytes(data)
    except (OSError, http.client.HTTPException):
        raise ConnectorRejected("connector_deadline_exceeded" if expired.is_set() else "connector_ai_unavailable") from None
    finally:
        timer.cancel()
        if response: response.close()
        connection.close(); timer.join(timeout=1)


def generate(prompt, model, timeout):
    scope = connector_scope.get()
    if not settings.local_ai_enabled or not settings.local_ai_gateway_enabled or scope is None or not scope.local_ai:
        raise ConnectorRejected("connector_local_ai_rejected")
    if not scope.actor_id or not scope.organization_id or not scope.case_id:
        raise ConnectorRejected("connector_ai_case_required")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}", model) or model not in settings.local_ai_allowed_models or model not in scope.local_ai_models or "cloud" in model.lower():
        raise ConnectorRejected("connector_ai_model_rejected")
    if not isinstance(prompt, str) or not 1 <= len(prompt.encode()) <= 64 * 1024:
        raise ConnectorRejected("connector_request_too_large")
    deadline = min(scope.deadline, time.monotonic() + min(max(float(timeout), .1), 60))
    from operia.security.outbound import connector_slot
    if not _capacity.acquire(blocking=False): raise ConnectorRejected("connector_ai_capacity_exceeded")
    outcome = "rejected"
    try:
        with connector_slot(scope):
            prepared = _validate({"action": "prepare", "prompt": prompt, "model": model}, deadline)
            expected = {"model": model, "prompt": prompt, "stream": False, "keep_alive": 0,
                "options": {"temperature": 0, "num_predict": 512, "num_ctx": 4096}}
            if prepared != expected: raise ConnectorRejected("connector_ai_invalid_protocol")
            raw = _exchange(canonical_bytes(prepared), deadline)
            # Parse hostile provider JSON inside the second sandbox, not here.
            import base64
            answer = _validate({"action": "validate_raw", "raw": base64.b64encode(raw).decode()}, deadline)
        text = answer.get("response")
        if set(answer) != {"response"} or not isinstance(text, str) or not text.strip() or len(text.encode()) > MAX_RESPONSE:
            raise ConnectorRejected("connector_ai_invalid_protocol")
        outcome = "completed"
        return text
    finally:
        _capacity.release()
        logging.getLogger("operia.security").info("ai_gateway org=%s actor=%s case=%s outcome=%s request_id=%s", scope.organization_id, scope.actor_id, scope.case_id, outcome, scope.request_id)
