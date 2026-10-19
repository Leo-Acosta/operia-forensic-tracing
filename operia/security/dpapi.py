"""Windows user-bound DPAPI; no machine-wide scope or plaintext fallback."""
import ctypes as c
from ctypes import wintypes as w
import os

class Blob(c.Structure):
    _fields_ = [('size', w.DWORD), ('data', c.c_void_p)]


def crypt(data, *, decrypt=False):
    if os.name != 'nt': raise RuntimeError('backup_windows_dpapi_required')
    source = c.create_string_buffer(data)
    incoming = Blob(len(data), c.cast(source,c.c_void_p)); outgoing = Blob()
    api = c.WinDLL('crypt32', use_last_error=True); kernel = c.WinDLL('kernel32', use_last_error=True)
    fn = api.CryptUnprotectData if decrypt else api.CryptProtectData
    fn.argtypes = [c.POINTER(Blob),c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p,w.DWORD,c.POINTER(Blob)]
    kernel.LocalFree.argtypes = [c.c_void_p]; kernel.LocalFree.restype = c.c_void_p
    if not fn(c.byref(incoming),None,None,None,None,1,c.byref(outgoing)):
        raise RuntimeError('backup_dpapi_decrypt_failed' if decrypt else 'backup_dpapi_encrypt_failed')
    try: return c.string_at(outgoing.data,outgoing.size)
    finally: kernel.LocalFree(outgoing.data)
