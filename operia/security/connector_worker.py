"""One bounded connector operation. Stdlib only; no API, ORM, .env or plugins."""
import base64
import json
import sys
from operia.security.transport import fetch_bytes, local_ai_bytes
from operia.security.errors import ConnectorRejected
from operia.security.child_guard import require_containment


def main():
    try:
        require_containment()
        raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 4097)
        if len(raw) > 2 * 1024 * 1024 + 4096:
            raise ConnectorRejected("connector_request_too_large")
        payload = json.loads(raw)
        timeout = min(max(float(payload.get("timeout", 8)), 0.1), 10)
        if payload["kind"] == "https":
            maximum = payload["maximum"]
            if not isinstance(maximum, int) or not 1 <= maximum <= 256 * 1024:
                raise ConnectorRejected("connector_invalid_limit")
            status, body = fetch_bytes(payload["url"], timeout, maximum, payload["allowed_hosts"])
        elif payload["kind"] == "local_ai":
            status, body = local_ai_bytes(payload["prompt"], payload["model"], timeout)
        else:
            raise ConnectorRejected("connector_kind_rejected")
        result = {"status": status, "body_base64": base64.b64encode(body).decode("ascii")}
    except ConnectorRejected as error:
        result = {"error": str(error)}
    except Exception:
        result = {"error": "connector_worker_error"}
    sys.stdout.write(json.dumps(result, separators=(",", ":")))

if __name__ == "__main__":
    main()
