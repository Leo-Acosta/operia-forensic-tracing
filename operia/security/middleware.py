"""Ingress body/origin/rate limits and safe response defaults, before routing."""
import asyncio
import logging
from uuid import uuid4
from threading import BoundedSemaphore
from starlette.responses import JSONResponse
from operia.core.config import settings
from operia.security.limits import admit

class SecurityBoundary:
    def __init__(self, app):
        self.app = app
        self.slots = BoundedSemaphore(settings.http_max_concurrent_requests)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if not self.slots.acquire(blocking=False):
            request_id = uuid4().hex
            logging.getLogger("operia.security").warning("security_rejected code=request_capacity_exceeded request_id=%s", request_id)
            return await JSONResponse({"detail": "request_capacity_exceeded", "request_id": request_id}, status_code=503,
                headers={"Retry-After": "1", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})(scope, receive, send)
        try:
            return await self._handle(scope, receive, send)
        finally:
            self.slots.release()

    async def _handle(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        async def safe_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [(b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"), (b"x-frame-options", b"SAMEORIGIN"),
                    (b"x-request-id", request_id.encode()), (b"permissions-policy", b"camera=(), microphone=(), geolocation=()")]
                if scope["path"].startswith(settings.api_prefix):
                    message["headers"].append((b"cache-control", b"no-store"))
            await send(message)
        async def reject(code, status):
            logging.getLogger("operia.security").warning("security_rejected code=%s request_id=%s", code, request_id)
            response = JSONResponse({"detail": code, "request_id": request_id}, status_code=status,
                headers={"Retry-After": "60"} if status == 429 else None)
            await response(scope, receive, safe_send)
        raw_headers = scope.get("headers", [])
        headers = dict(raw_headers)
        if sum(key.lower() == b"content-length" for key, value in raw_headers) > 1 or (b"content-length" in headers and b"transfer-encoding" in headers):
            return await reject("ambiguous_body_framing", 400)
        if headers.get(b"content-encoding", b"identity").lower() != b"identity":
            return await reject("compressed_request_rejected", 415)
        peer = (scope.get("client") or ("unknown", 0))[0]  # Never trust X-Forwarded-For here.
        auth_path = scope["path"].startswith(settings.api_prefix + "/identity/") and scope["method"] == "POST"
        if not admit(peer, authentication=auth_path):
            return await reject("request_rate_exceeded", 429)
        origin = headers.get(b"origin")
        if scope["method"] not in ("GET", "HEAD", "OPTIONS") and origin and origin.decode("latin1") not in settings.cors_origins:
            return await reject("origin_rejected", 403)
        if b"content-length" in headers:
            try:
                length = int(headers[b"content-length"])
                if length < 0:
                    raise ValueError()
            except ValueError:
                return await reject("invalid_content_length", 400)
            if length > settings.http_max_body_bytes:
                return await reject("request_body_too_large", 413)
        body = bytearray()
        try:
            async with asyncio.timeout(15):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > settings.http_max_body_bytes:
                        return await reject("request_body_too_large", 413)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await reject("request_body_timeout", 408)
        if headers.get(b"content-type", b"").split(b";", 1)[0].lower() == b"application/json":
            from operia.forensic_engine.canonical import read_json
            from operia.forensic_engine.contracts import EngineInputError
            try:
                read_json(bytes(body), limit=settings.http_max_body_bytes)
            except EngineInputError:
                return await reject("invalid_or_ambiguous_json", 422)
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(scope, replay, safe_send)
