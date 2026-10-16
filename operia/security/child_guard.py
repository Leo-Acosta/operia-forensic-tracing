"""Fail closed before reading untrusted input unless Windows containment exists."""
import ctypes as C
from ctypes import wintypes as W
import os


def require_containment():
    if os.name != "nt":
        raise RuntimeError("sandbox_required")
    kernel, security = C.WinDLL("kernel32", use_last_error=True), C.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.IsProcessInJob.argtypes = [W.HANDLE, W.HANDLE, C.POINTER(W.BOOL)]
    security.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    security.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    process, token, contained, size, job = kernel.GetCurrentProcess(), W.HANDLE(), W.DWORD(), W.DWORD(), W.BOOL()
    if not security.OpenProcessToken(process, 8, C.byref(token)):
        raise RuntimeError("sandbox_token_unavailable")
    try:
        valid = security.GetTokenInformation(token, 29, C.byref(contained), C.sizeof(contained), C.byref(size))
        valid = valid and kernel.IsProcessInJob(process, None, C.byref(job))
        if not valid or not contained.value or not job.value:
            raise RuntimeError("sandbox_required")
    finally:
        kernel.CloseHandle(token)
