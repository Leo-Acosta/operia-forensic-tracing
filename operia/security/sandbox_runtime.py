"""Operator-built, stdlib-only, non-secret runtime for Windows AppContainers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from operia.security.windows_sandbox import SandboxUnavailable, launch

PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = PROJECT / "storage" / "sandbox-runtime"
MODULES = ("operia/__init__.py", "operia/security/__init__.py",
    "operia/security/connector_worker.py", "operia/security/transport.py", "operia/security/errors.py",
    "operia/security/child_guard.py", "operia/security/ai_gateway_worker.py", "scripts/sandbox_probe.py")


def sources():
    return sorted([PROJECT / name for name in MODULES] + list((PROJECT / "operia/forensic_engine").glob("*.py")))


def identity():
    digest = hashlib.sha256(b"operia-appcontainer-runtime/2\0" + sys.version.encode())
    policy = [Path(__file__), PROJECT / "operia/security/windows_sandbox.py"]
    for file in sorted(sources() + policy):
        digest.update(file.relative_to(PROJECT).as_posix().encode()); digest.update(file.read_bytes())
    return digest.hexdigest()[:24]


def prepare(root=DEFAULT_ROOT):
    if os.name != "nt":
        raise SandboxUnavailable("sandbox_windows_required")
    if sys.version_info[:2] != (3, 12):
        raise SandboxUnavailable("sandbox_runtime_requires_python_312")
    root = Path(root).resolve()
    target = root / identity()
    if target.exists():
        verify(target)
        return target
    target.mkdir(parents=True, exist_ok=False)
    base = Path(sys.base_prefix)
    # Explicit runtime files; no site-packages, .pth, .env, DB, API or user config.
    for file in [base / "python.exe", base / "LICENSE.txt", *base.glob("*.dll")]:
        shutil.copy2(file, target / file.name)
    shutil.copytree(base / "DLLs", target / "DLLs", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(base / "Lib", target / "Lib", ignore=shutil.ignore_patterns(
        "site-packages", "__pycache__", "test", "tests", "ensurepip", "idlelib", "tkinter"))
    (target / "python312._pth").write_text("Lib\nDLLs\napp\n", encoding="ascii")
    for source in sources():
        dest = target / "app" / source.relative_to(PROJECT)
        dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest)
    files = {f.relative_to(target).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted(target.rglob("*")) if f.is_file()}
    (target / "manifest.json").write_text(json.dumps({"schema": 1, "identity": identity(), "files": files}, indent=2), encoding="utf-8")
    # Grant only RX to AppContainers on this dedicated non-secret runtime tree.
    tool = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/icacls.exe"
    result = subprocess.run([str(tool), str(target), "/grant", "*S-1-15-2-1:(OI)(CI)(RX)", "/T", "/Q"],
        capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise SandboxUnavailable("sandbox_runtime_acl_failed")
    verify(target)
    return target


def verify(target):
    target = Path(target)
    try:
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema"] != 1 or manifest["identity"] != identity() or not isinstance(manifest["files"], dict):
            raise ValueError()
        actual = {f.relative_to(target).as_posix() for f in target.rglob("*") if f.is_file()}
        if actual != set(manifest["files"]) | {"manifest.json"}: raise ValueError()
        for name, expected in manifest["files"].items():
            file = target / name
            if file.is_symlink() or not file.resolve().is_relative_to(target.resolve()) or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
                raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise SandboxUnavailable("sandbox_runtime_integrity_failed") from None


def spawn_worker(kind):
    if kind not in ("native", "https", "local_ai", "ai_gateway"):
        raise SandboxUnavailable("sandbox_kind_rejected")
    if kind == "local_ai":
        # AppContainer intentionally has no loopback exemption. Never bypass it.
        raise SandboxUnavailable("sandbox_local_ai_requires_separate_gateway")
    target = DEFAULT_ROOT / identity()
    if not target.is_dir():
        raise SandboxUnavailable("sandbox_runtime_not_prepared")
    verify(target)
    module = {"native": "operia.forensic_engine.worker_entry", "https": "operia.security.connector_worker",
        "ai_gateway": "operia.security.ai_gateway_worker"}[kind]
    child = launch(target, module, internet=kind == "https")
    child.sandbox_identity = target.name
    return child


def status():
    info = {"required": True, "backend": "windows_appcontainer_job_v1", "runtime_verified": False,
        "launch_verified_per_job": True, "local_ai_direct_loopback": False}
    try:
        if os.name != "nt": raise SandboxUnavailable("sandbox_windows_required")
        verify(DEFAULT_ROOT / identity())
        info["runtime_verified"] = True
    except SandboxUnavailable as error:
        info["reason"] = str(error)
    return info
