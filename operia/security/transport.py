"""HTTPS only, explicit destinations, pinned public DNS answers, bounded responses."""
import http.client
import ipaddress
import json
import socket
import ssl
import time
from urllib.parse import urlsplit
from operia.security.errors import ConnectorRejected


def approved_destination(url, allowed_hosts):
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower()
        if len(url) > 4096 or any(ord(c) < 33 or ord(c) == 127 for c in url) or "\\" in url or parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443):
            raise ValueError()
        if not host or host not in allowed_hosts or host.endswith("."):
            raise ValueError()
        # Do not resolve unapproved destinations or trust HTTP proxy environment variables.
        addresses = sorted({record[4][0] for record in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        if not addresses:
            raise ValueError()
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global or ip.is_multicast or ip.is_reserved:
                raise ValueError()
            if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo or ip.scope_id):
                raise ValueError()
        return host, addresses, parsed.path or "/", parsed.query
    except (ValueError, UnicodeError, OSError):
        raise ConnectorRejected("connector_destination_rejected") from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, 443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch_bytes(url, timeout=8, maximum=256 * 1024, allowed_hosts=()):
    host, addresses, path, query = approved_destination(url, allowed_hosts)
    connection = PinnedHTTPS(host, addresses[0], min(max(timeout, 1), 10))
    started = time.monotonic()
    try:
        connection.request("GET", path + ("?" + query if query else ""), headers={"Accept": "application/json, text/plain", "Accept-Encoding": "identity", "User-Agent": "OPERIA-Connector/1"})
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise ConnectorRejected("connector_redirect_rejected")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ConnectorRejected("connector_encoding_rejected")
        chunks = bytearray()
        while True:
            remaining = 10 - (time.monotonic() - started)
            if remaining <= 0:
                raise ConnectorRejected("connector_deadline_exceeded")
            if connection.sock:
                connection.sock.settimeout(min(remaining, 5))
            chunk = response.read1(min(16384, maximum + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > maximum:
                raise ConnectorRejected("connector_response_too_large")
        return response.status, bytes(chunks)
    except (OSError, http.client.HTTPException):
        raise ConnectorRejected("connector_unavailable") from None
    finally:
        connection.close()



def local_ai_bytes(prompt, model, timeout):
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    if len(payload) > 2 * 1024 * 1024:
        raise ConnectorRejected("connector_request_too_large")
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=timeout)
    try:
        connection.request("POST", "/api/generate", body=payload, headers={"Content-Type": "application/json", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Encoding", "identity") != "identity":
            raise ConnectorRejected("connector_http_error")
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ConnectorRejected("connector_response_too_large")
        return response.status, raw
    except (OSError, http.client.HTTPException):
        raise ConnectorRejected("connector_unavailable") from None
    finally:
        connection.close()
