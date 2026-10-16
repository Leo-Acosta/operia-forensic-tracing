"""Private subprocess protocol, invoked only by the fixed local worker."""
import base64
import sys

from operia.forensic_engine import ENGINE_VERSION
from operia.forensic_engine.analysis import analyze
from operia.forensic_engine.canonical import canonical_bytes, read_json
from operia.forensic_engine.contracts import Source
from operia.security.child_guard import require_containment


def main():
    try:
        require_containment()
        raw = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
        payload = read_json(raw, limit=8 * 1024 * 1024)
        if payload["engine_version"] != ENGINE_VERSION:
            raise ValueError("version mismatch")
        source = Source(str(payload["acquisition_id"]), payload["filename"], payload["platform"], payload["format"],
                        base64.b64decode(payload["input"], validate=True))
        indicators = base64.b64decode(payload["indicators"], validate=True) if payload["indicators"] is not None else None
        sys.stdout.buffer.write(canonical_bytes(analyze(source, indicators, payload["demo_rules"])))
    except Exception:
        # Exception messages can contain evidence. Persist only a controlled code.
        sys.stderr.write("analysis_rejected")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
