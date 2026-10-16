"""Controlled local containment probe. Synthetic paths only, no real secrets.

Not exposed through HTTP or worker dispatch. Used by the local pentest suite.
"""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def attempt(function):
    try:
        function()
        return "allowed"
    except (OSError, PermissionError) as error:
        return {"denied": type(error).__name__, "winerror": getattr(error, "winerror", None)}


def main():
    data = json.loads(sys.stdin.buffer.read(16384))
    action = data.get("action", "boundary")
    if action == "sleep":
        time.sleep(60)
    elif action == "flood":
        for _ in range(512): sys.stdout.buffer.write(b"x" * 16384)
    elif action == "cpu":
        while True: pass
    elif action == "memory":
        try:
            value = bytearray(512 * 1024 * 1024)
            print(json.dumps({"allocation": len(value)}))
        except MemoryError:
            print(json.dumps({"allocation": "denied"}))
    else:
        k, a = C.WinDLL("kernel32", use_last_error=True), C.WinDLL("advapi32", use_last_error=True)
        k.GetCurrentProcess.restype = W.HANDLE
        k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]; k.OpenProcess.restype = W.HANDLE
        k.CloseHandle.argtypes = [W.HANDLE]
        a.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
        a.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
        token, contained, size = W.HANDLE(), W.DWORD(), W.DWORD()
        if not a.OpenProcessToken(k.GetCurrentProcess(), 8, C.byref(token)): raise C.WinError(C.get_last_error())
        try:
            if not a.GetTokenInformation(token, 29, C.byref(contained), C.sizeof(contained), C.byref(size)):
                raise C.WinError(C.get_last_error())
        finally: k.CloseHandle(token)
        def parent_memory():
            handle = k.OpenProcess(0x10, False, data["parent_pid"])
            if not handle: raise C.WinError(C.get_last_error())
            k.CloseHandle(handle)
        def network():
            with socket.socket() as sock:
                sock.settimeout(.5); sock.connect(("127.0.0.1", data["port"]))
        def spawn():
            child = subprocess.Popen([sys.executable, "-I", "-S", "-B", "-c", "pass"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            child.wait(timeout=2)
        result = {"appcontainer": bool(contained.value),
            "read_private_canary": attempt(lambda: Path(data["private_canary"]).read_bytes()),
            "write_private_canary": attempt(lambda: Path(data["private_canary"]).write_bytes(b"probe")),
            "write_runtime": attempt(lambda: Path(data["runtime_canary"]).write_bytes(b"probe")),
            "spawn_descendant": attempt(spawn), "parent_memory": attempt(parent_memory),
            "loopback": attempt(network),
            "secrets_absent": not any(key in os.environ for key in ("OPERIA_AUTH_SIGNING_KEY", "HTTP_PROXY", "HTTPS_PROXY", "PYTHONPATH")),
            "site_packages_absent": not any("site-packages" in path.lower() for path in sys.path)}
        print(json.dumps(result))


if __name__ == "__main__": main()
