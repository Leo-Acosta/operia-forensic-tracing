"""Private files and Windows token checks; no shell, secret values or ACL fallbacks."""
import ctypes as c
from ctypes import wintypes as w
import os
from pathlib import Path
import stat
import struct


def no_links(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
                raise RuntimeError('private_path_link_rejected')
    return path


def win_api():
    if os.name != 'nt': raise RuntimeError('windows_security_required')
    adv = c.WinDLL('advapi32', use_last_error=True); kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.LocalFree.argtypes = [c.c_void_p]; kernel.LocalFree.restype = c.c_void_p
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(c.c_void_p)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    return adv, kernel


def sid_string(pointer, adv, kernel):
    value = c.c_void_p()
    if not adv.ConvertSidToStringSidW(pointer, c.byref(value)): raise RuntimeError('security_sid_failed')
    try: return c.wstring_at(value)
    finally: kernel.LocalFree(value)


def token_info():
    adv, kernel = win_api(); token = w.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)): raise RuntimeError('security_token_failed')
    try:
        size = w.DWORD(); adv.GetTokenInformation(token, 1, None, 0, c.byref(size))
        buffer = c.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size, c.byref(size)): raise RuntimeError('security_token_failed')
        sid = sid_string(c.cast(buffer, c.POINTER(c.c_void_p))[0], adv, kernel)
        elevated = w.DWORD()
        if not adv.GetTokenInformation(token, 20, c.byref(elevated), c.sizeof(elevated), c.byref(size)):
            raise RuntimeError('security_token_failed')
        class Group(c.Structure):
            _fields_ = [('sid',c.c_void_p),('attributes',w.DWORD)]
        adv.GetTokenInformation(token,2,None,0,c.byref(size))
        groups=c.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token,2,groups,size,c.byref(size)): raise RuntimeError('security_token_failed')
        count=c.cast(groups,c.POINTER(w.DWORD))[0]
        offset=c.alignment(Group)
        admin=False
        for index in range(count):
            group=Group.from_buffer(groups,offset+index*c.sizeof(Group))
            admin |= sid_string(group.sid,adv,kernel)=='S-1-5-32-544'
        return {'sid': sid, 'elevated': bool(elevated.value), 'administrator_member':admin,
                'system': sid in ('S-1-5-18','S-1-5-19','S-1-5-20')}
    finally: kernel.CloseHandle(token)


def protect(path):
    path = no_links(path)
    if os.name != 'nt':
        path.chmod(0o700 if path.is_dir() else 0o600); return
    adv, kernel = win_api(); sid = token_info()['sid']
    flags = 'OICI' if path.is_dir() else ''
    sddl = 'D:P'+''.join(f'(A;{flags};FA;;;{s})' for s in (sid,'S-1-5-18','S-1-5-32-544'))
    sd = c.c_void_p(); dacl = c.c_void_p(); present = w.BOOL(); defaulted = w.BOOL()
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p]
    adv.GetSecurityDescriptorDacl.argtypes = [c.c_void_p,c.POINTER(w.BOOL),c.POINTER(c.c_void_p),c.POINTER(w.BOOL)]
    adv.SetNamedSecurityInfoW.argtypes = [w.LPWSTR,c.c_int,w.DWORD,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p]
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,c.byref(sd),None): raise RuntimeError('private_acl_failed')
    try:
        if not adv.GetSecurityDescriptorDacl(sd,c.byref(present),c.byref(dacl),c.byref(defaulted)):
            raise RuntimeError('private_acl_failed')
        if adv.SetNamedSecurityInfoW(str(path),1,0x80000004,None,None,dacl,None): raise RuntimeError('private_acl_failed')
    finally: kernel.LocalFree(sd)
    assert_private(path)


def assert_private(path):
    path = no_links(path)
    if os.name != 'nt':
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077: raise RuntimeError('private_acl_required')
        return
    adv, kernel = win_api(); sd = c.c_void_p(); dacl = c.c_void_p(); owner = c.c_void_p()
    adv.GetNamedSecurityInfoW.argtypes = [w.LPWSTR,c.c_int,w.DWORD,c.c_void_p,c.c_void_p,c.POINTER(c.c_void_p),c.c_void_p,c.POINTER(c.c_void_p)]
    adv.GetAce.argtypes = [c.c_void_p,w.DWORD,c.POINTER(c.c_void_p)]
    if adv.GetNamedSecurityInfoW(str(path),1,5,c.byref(owner),None,c.byref(dacl),None,c.byref(sd)):
        raise RuntimeError('private_acl_unreadable')
    try:
        if not dacl: raise RuntimeError('private_acl_required')
        allowed = {token_info()['sid'],'S-1-5-18','S-1-5-32-544'}
        if not owner or sid_string(owner,adv,kernel) not in allowed: raise RuntimeError('private_owner_required')
        count = struct.unpack('<BBHHH', c.string_at(dacl,8))[3]
        own = False
        for index in range(count):
            ace = c.c_void_p()
            if not adv.GetAce(dacl,index,c.byref(ace)): raise RuntimeError('private_acl_unreadable')
            kind = c.string_at(ace,1)[0]
            if kind == 1: continue  # Deny ACE cannot grant access.
            if kind != 0: raise RuntimeError('private_acl_unsupported')
            principal = sid_string(ace.value+8,adv,kernel)
            if principal not in allowed: raise RuntimeError('private_acl_required')
            own |= principal == token_info()['sid']
        if not own: raise RuntimeError('private_acl_required')
    finally: kernel.LocalFree(sd)


def read_key(path):
    path = no_links(path)
    if not path.is_file(): raise RuntimeError('auth_key_file_missing')
    if path.stat().st_nlink != 1: raise RuntimeError('auth_key_file_link_rejected')
    assert_private(path)
    with path.open('rb') as stream: value = stream.read(33)
    if len(value) != 32: raise RuntimeError('auth_key_file_invalid')
    return value
