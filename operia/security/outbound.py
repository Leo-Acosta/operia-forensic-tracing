"""HTTPS only, explicit destinations, pinned public DNS answers, bounded responses."""
import http.client
import ipaddress
import json
import socket
import ssl
import time
from urllib.parse import urlsplit
from operia.core.config import settings

class ConnectorRejected(RuntimeError):
    pass


def approved_destination(url):
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower()
        if len(url) > 4096 or any(ord(c) < 33 or ord(c) == 127 for c in url) or "\\" in url or parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443):
            raise ValueError()
        if not host or host not in settings.connector_allowed_hosts or host.endswith("."):
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


def fetch_bytes(url, timeout=8, maximum=256 * 1024):
    host, addresses, path, query = approved_destination(url)
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


def fetch_json(url, timeout=8):
    status, raw = fetch_bytes(url, timeout)
    if status != 200:
        raise ConnectorRejected("connector_http_error")
    from operia.forensic_engine.canonical import read_json
    try:
        data = read_json(raw, limit=256 * 1024)
    except ValueError:
        raise ConnectorRejected("connector_invalid_json") from None
    if not isinstance(data, dict):
        raise ConnectorRejected("connector_invalid_schema")
    return data
