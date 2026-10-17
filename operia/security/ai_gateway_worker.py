"""Offline AI protocol validator. No network, DB, config or reusable conversation."""
import sys
import base64
from operia.forensic_engine.canonical import read_json, canonical_bytes
from operia.security.child_guard import require_containment

MAX_PROMPT = 64 * 1024
MAX_RESPONSE = 256 * 1024


def validate(payload):
    if payload["action"] == "validate_raw":
        raw = base64.b64decode(payload["raw"], validate=True)
        result = read_json(raw, limit=MAX_RESPONSE)
        return validate({"action": "validate", "result": result})
    if payload["action"] == "prepare":
        prompt, model = payload["prompt"], payload["model"]
        if not isinstance(prompt, str) or not 1 <= len(prompt.encode()) <= MAX_PROMPT:
            raise ValueError()
        if not isinstance(model, str) or not 1 <= len(model) <= 120:
            raise ValueError()
        return {"model": model, "prompt": prompt, "stream": False, "keep_alive": 0,
            "options": {"temperature": 0, "num_predict": 512, "num_ctx": 4096}}
    if payload["action"] == "validate":
        result = payload["result"]
        if not isinstance(result, dict) or result.get("done") is not True or result.get("error"):
            raise ValueError()
        text = result.get("response")
        if not isinstance(text, str) or not text.strip() or len(text.encode()) > MAX_RESPONSE:
            raise ValueError()
        # Ignore returned context/tokens, tools, reasoning and provider metadata.
        return {"response": text}
    raise ValueError()


def main():
    try:
        require_containment()
        data = read_json(sys.stdin.buffer.read(512 * 1024 + 1), limit=512 * 1024)
        sys.stdout.buffer.write(canonical_bytes(validate(data)))
    except Exception:
        sys.stdout.buffer.write(b'{"error":"connector_ai_invalid_protocol"}')
        raise SystemExit(2)


if __name__ == "__main__": main()
