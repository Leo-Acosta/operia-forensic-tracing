"""Session-0 USER32 initialization without opening an interactive desktop.

Grant only the fresh package SID read access to the service's noninteractive
station; create a separate low-integrity desktop and revoke that ACE on close.
Never alter WinSta0 or the service's default desktop. Job UI limits stay 0xff.
"""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import re
import uuid

from operia.security.private_files import token_info, win_api, sid_string


class Attributes(c.Structure):
    _fields_=[('size',w.DWORD),('descriptor',c.c_void_p),('inherit',w.BOOL)]


class Trustee(c.Structure):
    _fields_=[('multiple',c.c_void_p),('operation',c.c_int),('form',c.c_int),('type',c.c_int),('name',c.c_void_p)]


class Entry(c.Structure):
    _fields_=[('permissions',w.DWORD),('mode',c.c_int),('inheritance',w.DWORD),('trustee',Trustee)]


def check(value):
    if not value: raise RuntimeError('sandbox_desktop_win32_'+str(c.get_last_error()))
    return value


def apis():
    adv,kernel=win_api(); user=c.WinDLL('user32',use_last_error=True)
    for dll,name,args,result in [
        (kernel,'GetCurrentProcessId',[],w.DWORD),
        (kernel,'ProcessIdToSessionId',[w.DWORD,c.POINTER(w.DWORD)],w.BOOL),
        (kernel,'CreateMutexW',[c.POINTER(Attributes),w.BOOL,w.LPCWSTR],w.HANDLE),
        (kernel,'WaitForSingleObject',[w.HANDLE,w.DWORD],w.DWORD),
        (kernel,'ReleaseMutex',[w.HANDLE],w.BOOL),
        (user,'CreateDesktopW',[w.LPCWSTR,w.LPCWSTR,c.c_void_p,w.DWORD,w.DWORD,c.POINTER(Attributes)],w.HANDLE),
        (user,'GetProcessWindowStation',[],w.HANDLE),
        (user,'OpenWindowStationW',[w.LPCWSTR,w.BOOL,w.DWORD],w.HANDLE),
        (user,'GetUserObjectInformationW',[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)],w.BOOL),
        (user,'GetUserObjectSecurity',[w.HANDLE,c.POINTER(w.DWORD),c.c_void_p,w.DWORD,c.POINTER(w.DWORD)],w.BOOL),
        (user,'SetUserObjectSecurity',[w.HANDLE,c.POINTER(w.DWORD),c.c_void_p],w.BOOL),
        (user,'CloseDesktop',[w.HANDLE],w.BOOL),(user,'CloseWindowStation',[w.HANDLE],w.BOOL),
        (adv,'ConvertStringSidToSidW',[w.LPCWSTR,c.POINTER(c.c_void_p)],w.BOOL),
        (adv,'ConvertStringSecurityDescriptorToSecurityDescriptorW',[w.LPCWSTR,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p],w.BOOL),
        (adv,'GetSecurityDescriptorDacl',[c.c_void_p,c.POINTER(w.BOOL),c.POINTER(c.c_void_p),c.POINTER(w.BOOL)],w.BOOL),
        (adv,'SetEntriesInAclW',[w.ULONG,c.POINTER(Entry),c.c_void_p,c.POINTER(c.c_void_p)],w.DWORD),
        (adv,'InitializeSecurityDescriptor',[c.c_void_p,w.DWORD],w.BOOL),
        (adv,'SetSecurityDescriptorDacl',[c.c_void_p,w.BOOL,c.c_void_p,w.BOOL],w.BOOL)]:
        fn=getattr(dll,name); fn.argtypes=args; fn.restype=result
    return adv,kernel,user


def descriptor(adv,text):
    value=c.c_void_p()
    check(adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(text,1,c.byref(value),None))
    return value


def edit(adv,kernel,user,station,mutex_name,owner,package,mode):
    # Cross-process serialization of station ACL read/modify/write. Packages
    # cannot open the mutex. Only the one fresh package SID is granted/revoked.
    sd=descriptor(adv,'D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;'+owner+')')
    mutex=None; acquired=False; sid=c.c_void_p(); new_acl=c.c_void_p()
    try:
        attr=Attributes(c.sizeof(Attributes),sd,False)
        mutex=check(kernel.CreateMutexW(c.byref(attr),False,mutex_name))
        result=kernel.WaitForSingleObject(mutex,5000)
        if result not in (0,128): raise RuntimeError('sandbox_desktop_acl_lock_failed')
        acquired=True
        check(adv.ConvertStringSidToSidW(package,c.byref(sid)))
        info=w.DWORD(4); length=w.DWORD()
        user.GetUserObjectSecurity(station,c.byref(info),None,0,c.byref(length))
        if not 20 <= length.value <= 65536: raise RuntimeError('sandbox_desktop_acl_size_invalid')
        previous=c.create_string_buffer(length.value)
        check(user.GetUserObjectSecurity(station,c.byref(info),previous,length,c.byref(length)))
        acl=c.c_void_p(); present=w.BOOL(); defaulted=w.BOOL()
        check(adv.GetSecurityDescriptorDacl(previous,c.byref(present),c.byref(acl),c.byref(defaulted)))
        if not present.value or not acl: raise RuntimeError('sandbox_desktop_null_acl_rejected')
        # Read attributes/enumeration and resolve atom names for USER32 loading.
        # No clipboard, shutdown, write attributes or desktop creation rights.
        # Job UI limits give each worker its own atom table, isolating other jobs.
        entry=Entry(0x20123,mode,0,Trustee(None,0,0,0,sid))
        code=adv.SetEntriesInAclW(1,c.byref(entry),acl,c.byref(new_acl))
        if code: raise RuntimeError('sandbox_desktop_acl_failed_'+str(code))
        absolute=c.create_string_buffer(64)
        check(adv.InitializeSecurityDescriptor(absolute,1))
        check(adv.SetSecurityDescriptorDacl(absolute,True,new_acl,False))
        check(user.SetUserObjectSecurity(station,c.byref(info),absolute))
    finally:
        if new_acl: kernel.LocalFree(new_acl)
        if sid: kernel.LocalFree(sid)
        if acquired: kernel.ReleaseMutex(mutex)
        if mutex: kernel.CloseHandle(mutex)
        kernel.LocalFree(sd)


class Desktop:
    def __init__(self,adv,kernel,user,station,desktop,name,mutex,owner,package):
        self.adv,self.kernel,self.user=adv,kernel,user
        self.station,self.desktop,self.name=station,desktop,name
        self.mutex,self.owner,self.package=mutex,owner,package

    def close(self):
        try:
            if self.desktop:
                check(self.user.CloseDesktop(self.desktop)); self.desktop=None
            if self.station:
                edit(self.adv,self.kernel,self.user,self.station,self.mutex,self.owner,self.package,4)
        finally:
            if self.station: self.user.CloseWindowStation(self.station); self.station=None


def create(package_sid):
    adv,kernel,user=apis(); session=w.DWORD()
    check(kernel.ProcessIdToSessionId(kernel.GetCurrentProcessId(),c.byref(session)))
    if session.value!=0: return None  # Existing interactive isolation unchanged.
    package=sid_string(package_sid,adv,kernel); owner=token_info()['sid']
    if not re.fullmatch(r'S-1-15-2-(?:\d+-){6}\d+',package): raise RuntimeError('sandbox_desktop_package_invalid')
    borrowed=check(user.GetProcessWindowStation())
    length=w.DWORD(); buffer=c.create_unicode_buffer(1024)
    check(user.GetUserObjectInformationW(borrowed,2,buffer,c.sizeof(buffer),c.byref(length)))
    station_name=buffer.value
    flags=(w.DWORD*3)()
    check(user.GetUserObjectInformationW(borrowed,1,flags,c.sizeof(flags),c.byref(length)))
    if not station_name.lower().startswith('service-') or flags[2]&1:
        raise RuntimeError('sandbox_noninteractive_service_station_required')
    station=check(user.OpenWindowStationW(station_name,False,0x60002))
    mutex='Local\\OperiaDesktopAcl-'+hashlib.sha256(station_name.encode()).hexdigest()[:32]
    desktop=None; granted=False
    try:
        edit(adv,kernel,user,station,mutex,owner,package,1); granted=True
        sd=descriptor(adv,'D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;'+owner+')(A;;0x201ff;;;'+package+')S:(ML;;NW;;;LW)')
        try:
            attr=Attributes(c.sizeof(Attributes),sd,False)
            name='OperiaJob-'+uuid.uuid4().hex
            desktop=check(user.CreateDesktopW(name,None,None,0,0xf01ff,c.byref(attr)))
        finally: kernel.LocalFree(sd)
        value=Desktop(adv,kernel,user,station,desktop,station_name+'\\'+name,mutex,owner,package)
        station=desktop=None; return value
    finally:
        if desktop: user.CloseDesktop(desktop)
        if station:
            if granted: edit(adv,kernel,user,station,mutex,owner,package,4)
            user.CloseWindowStation(station)
