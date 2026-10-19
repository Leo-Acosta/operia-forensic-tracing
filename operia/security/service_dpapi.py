"""DPAPI migration in the actual SCM identity; only a local admin-owned pipe."""
import ctypes as c
from ctypes import wintypes as w
import hashlib


def migrate_if_requested(root):
    kernel=c.WinDLL('kernel32',use_last_error=True)
    advapi=c.WinDLL('advapi32',use_last_error=True)
    kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
    kernel.CreateFileW.restype=w.HANDLE
    kernel.ReadFile.argtypes=[w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p]
    kernel.WriteFile.argtypes=kernel.ReadFile.argtypes
    kernel.CloseHandle.argtypes=[w.HANDLE]
    kernel.LocalFree.argtypes=[c.c_void_p]
    name='\\\\.\\pipe\\OperiaDpapi-'+hashlib.sha256(str(root).rstrip('\\').lower().encode()).hexdigest()
    handle=kernel.CreateFileW(name,0xc0020000,0,None,3,0,None)
    if handle==c.c_void_p(-1).value:
        if c.get_last_error()==2: return None
        raise RuntimeError('service_migration_pipe_open_failed')
    sd=c.c_void_p(); owner=c.c_void_p(); text=w.LPWSTR()
    raw=None
    try:
        advapi.GetSecurityInfo.argtypes=[w.HANDLE,c.c_int,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p,c.c_void_p,c.c_void_p,c.POINTER(c.c_void_p)]
        advapi.ConvertSidToStringSidW.argtypes=[c.c_void_p,c.POINTER(w.LPWSTR)]
        if advapi.GetSecurityInfo(handle,6,1,c.byref(owner),None,None,None,c.byref(sd)):
            raise RuntimeError('service_migration_pipe_owner_unverifiable')
        if not advapi.ConvertSidToStringSidW(owner,c.byref(text)) or text.value!='S-1-5-32-544':
            raise RuntimeError('service_migration_pipe_owner_rejected')
        # Migration must prove preservation of an existing canary, never seed one.
        from operia.security.private_files import no_links
        canary=no_links(root/'data/control/credential-canary-v3.dpapi')
        if not canary.is_file() or canary.stat().st_nlink!=1:
            raise RuntimeError('service_existing_dpapi_canary_required')
        hello=c.create_string_buffer(b'OPERIA-DPAPI/1'); written=w.DWORD()
        if not kernel.WriteFile(handle,hello,len(hello.raw)-1,c.byref(written),None) or written.value!=len(hello.raw)-1:
            raise RuntimeError('service_migration_handshake_failed')
        def read_into(buffer,length):
            offset=0
            while offset<length:
                count=w.DWORD()
                if not kernel.ReadFile(handle,c.byref(buffer,offset),length-offset,c.byref(count),None) or not count.value:
                    raise RuntimeError('service_migration_short_read')
                offset+=count.value
        length=w.DWORD();read_into(length,4)
        if length.value<2 or length.value>2048 or length.value%2:
            raise RuntimeError('service_migration_size_rejected')
        raw=c.create_string_buffer(length.value+2);read_into(raw,length.value)
        api=c.WinDLL('crypt32',use_last_error=True)
        api.CryptUpdateProtectedState.argtypes=[c.c_void_p,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.POINTER(w.DWORD)]
        success,failure=w.DWORD(),w.DWORD()
        from operia.security.private_files import token_info
        sid=c.c_void_p()
        advapi.ConvertStringSidToSidW.argtypes=[w.LPCWSTR,c.POINTER(c.c_void_p)]
        if not advapi.ConvertStringSidToSidW(token_info()['sid'],c.byref(sid)):
            raise RuntimeError('service_dpapi_sid_unverifiable')
        try:
            if not api.CryptUpdateProtectedState(sid,raw,0,c.byref(success),c.byref(failure)):
                raise RuntimeError('service_dpapi_migration_failed')
        finally: kernel.LocalFree(sid)
        return {'migrated_master_keys':success.value,'stale_master_keys':failure.value}
    finally:
        if raw is not None: c.memset(raw,0,c.sizeof(raw))
        if text: kernel.LocalFree(c.cast(text,c.c_void_p))
        if sd: kernel.LocalFree(sd)
        kernel.CloseHandle(handle)
