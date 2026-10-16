"""Local pentest helper: deliberately exit a disposable supervisor, no evidence."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operia.security.sandbox_runtime import DEFAULT_ROOT, identity
from operia.security.windows_sandbox import launch

if __name__ == "__main__":
    child = launch(DEFAULT_ROOT / identity(), "scripts.sandbox_probe")
    child.stdin.write(b'{"action":"sleep"}'); child.stdin.close()
    print(json.dumps({"pid": child.pid, "profile": child._profile}), flush=True)
    sys.stdin.buffer.read(1)
    os._exit(0)  # Intentionally bypass finally/destructors to test the kernel Job.
