import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import ctypes
import pytest

from operia.security.service_control import load, verify_tree, environment


@pytest.mark.skipif(os.name!='nt',reason='Windows USER object protection')
@pytest.mark.parametrize('sid,reason',[
    ('S-1-15-2-1','package_invalid'),
    ('S-1-15-2-1-2-3-4-5-6-7','noninteractive_service_station_required')])
def test_service_desktop_never_modifies_interactive_station_or_grants_all_packages(monkeypatch,sid,reason):
    from operia.security import private_desktop as desktop
    adv,kernel,user=desktop.apis()
    session=ctypes.wintypes.DWORD()
    assert kernel.ProcessIdToSessionId(kernel.GetCurrentProcessId(),ctypes.byref(session))
    if session.value==0: pytest.skip('This negative control requires an interactive operator session')
    class Kernel:
        def __getattr__(self,key): return getattr(kernel,key)
        def ProcessIdToSessionId(self,pid,pointer): pointer._obj.value=0; return True
    monkeypatch.setattr(desktop,'apis',lambda:(adv,Kernel(),user))
    monkeypatch.setattr(desktop,'edit',lambda *args:pytest.fail('Interactive station ACL must never be modified'))
    pointer=ctypes.c_void_p()
    assert adv.ConvertStringSidToSidW(sid,ctypes.byref(pointer))
    try:
        with pytest.raises(RuntimeError,match=reason): desktop.create(pointer)
    finally: kernel.LocalFree(pointer)


@pytest.mark.skipif(os.name!='nt',reason='Windows operator boundaries')
def test_manager_requires_elevation_before_touching_any_root(tmp_path):
    if ctypes.windll.shell32.IsUserAnAdmin(): pytest.skip('Negative control needs a non-elevated operator')
    root=Path(__file__).resolve().parents[1]
    target=tmp_path/'must-not-be-created'
    result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-NonInteractive','-File',str(root/'scripts/manage-windows-service.ps1'),
                           '-Root',str(target),'-Action','Start'],capture_output=True,text=True,timeout=30)
    assert result.returncode!=0 and 'service_administrator_required' in result.stderr
    assert not target.exists()


@pytest.mark.skipif(os.name!='nt',reason='Windows operator boundaries')
def test_fault_injection_requires_explicit_opt_in_before_any_operation(tmp_path):
    root=Path(__file__).resolve().parents[1]
    target=tmp_path/'must-not-be-created'
    result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-NonInteractive','-File',str(root/'scripts/validate-windows-service.ps1'),
                           '-Root',str(target)],capture_output=True,text=True,timeout=30)
    assert result.returncode!=0 and 'service_validation_requires_explicit_synthetic_fault_injection_switch' in result.stderr
    assert not target.exists()


def layout(tmp_path):
    (tmp_path/'config').mkdir()
    release=tmp_path/'releases'/('a'*24)
    (release/'code').mkdir(parents=True); (release/'runtime').mkdir()
    (release/'code/app.py').write_text('# benign')
    (release/'runtime/python.exe').write_bytes(b'placeholder')
    for name,tree,schema,key in [('layout.json','code','operia-service-staging/1','code_files'),
                                 ('runtime-manifest.json','runtime','operia-service-runtime/1','files')]:
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (release/tree).iterdir()}
        (release/name).write_text(json.dumps({'schema':schema,key:files}))
    config={'schema':'operia-windows-service/1','service_name':'OperiaTest','account_sid':'S-1-5-21-1-2-3-4','port':29876,'synthetic_only':True}
    (tmp_path/'config/service.json').write_text(json.dumps(config))
    (tmp_path/'config/active-release.txt').write_text('a'*24)
    return release,config


def test_release_selection_rejects_traversal_and_unexpected_config(tmp_path):
    release,config=layout(tmp_path)
    assert load(tmp_path)[2]=='a'*24
    (tmp_path/'config/active-release.txt').write_text('../outside')
    with pytest.raises(RuntimeError,match='release_id_rejected'): load(tmp_path)
    (tmp_path/'config/active-release.txt').write_text('a'*24)
    config['password']='must never be accepted'
    (tmp_path/'config/service.json').write_text(json.dumps(config))
    with pytest.raises(RuntimeError,match='configuration_rejected'): load(tmp_path)


@pytest.mark.parametrize('mutation',['changed','extra','hardlink','missing'])
def test_release_inventory_fails_closed(tmp_path,mutation):
    release,_=layout(tmp_path)
    file=release/'code/app.py'
    if mutation=='changed': file.write_text('tampered')
    elif mutation=='extra': (release/'code/extra.py').write_text('tampered')
    elif mutation=='hardlink': os.link(file,release/'code/link.py')
    else: file.unlink()
    with pytest.raises(RuntimeError,match='service_release_'): load(tmp_path)


def test_shared_data_and_secret_path_do_not_follow_release(tmp_path):
    release,config=layout(tmp_path)
    env=environment(tmp_path,config)
    assert str(release) not in str(env)
    assert env['OPERIA_LOCAL_RECOVERY_ENABLED']=='false'
    assert Path(env['OPERIA_AUTH_SIGNING_KEY_FILE']).parent==tmp_path/'secrets'
    assert not any('PASSWORD' in k for k in env)


@pytest.mark.skipif(os.name!='nt',reason='Windows SCM host compilation')
def test_framework_service_host_and_native_helper_compile(tmp_path):
    root=Path(__file__).resolve().parents[1]
    compiler=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    result=subprocess.run([str(compiler),'/nologo','/target:exe','/reference:System.ServiceProcess.dll',
                           '/reference:System.Runtime.Serialization.dll','/out:'+str(tmp_path/'host.exe'),str(root/'scripts/OperiaService.cs')],
                          capture_output=True,text=True,timeout=40)
    assert result.returncode==0,result.stdout+result.stderr
    result=subprocess.run([str(compiler),'/nologo','/target:library','/out:'+str(tmp_path/'pipe.dll'),str(root/'scripts/ServiceMigrationPipe.cs')],
                          capture_output=True,text=True,timeout=40)
    assert result.returncode==0,result.stdout+result.stderr
    result=subprocess.run([str(compiler),'/nologo','/target:library','/out:'+str(tmp_path/'native.dll'),str(root/'scripts/ServiceNative.cs')],
                          capture_output=True,text=True,timeout=40)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.skipif(os.name!='nt',reason='Windows Credential Manager')
def test_native_vault_roundtrip_and_missing_credential(tmp_path):
    source=Path(__file__).resolve().parents[1]/'scripts/ServiceNative.cs'
    script=tmp_path/'vault.ps1'
    script.write_text("""param([string]$Source)
$ErrorActionPreference='Stop'
Add-Type -Path $Source
$target='OPERIA/test/'+[Guid]::NewGuid().ToString('N')
$password=[OperiaServiceNative]::NewPassword()
if ($password.Length -lt 48 -or $password.Length -gt 63) {throw 'test_password_length_not_compatible_with_local_change'}
$copy=$null
try {
    if ($null -ne [OperiaServiceNative]::Read($target)) {throw 'test_target_already_exists'}
    [OperiaServiceNative]::Store($target,'.\\OperiaSvc',$password)
    $copy=[OperiaServiceNative]::Read($target)
    if ($copy.Length -ne $password.Length) {throw 'test_credential_length_changed'}
    $a=[Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($password)
    $b=[Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($copy)
    try {
        for($i=0;$i -lt $password.Length*2;$i++) {
            if ([Runtime.InteropServices.Marshal]::ReadByte($a,$i) -ne [Runtime.InteropServices.Marshal]::ReadByte($b,$i)) {throw 'test_credential_changed'}
        }
    } finally {[Runtime.InteropServices.Marshal]::ZeroFreeGlobalAllocUnicode($a); [Runtime.InteropServices.Marshal]::ZeroFreeGlobalAllocUnicode($b)}
} finally {
    [OperiaServiceNative]::Delete($target)
    $password.Dispose(); if ($copy) {$copy.Dispose()}
}
if ($null -ne [OperiaServiceNative]::Read($target)) {throw 'test_credential_not_deleted'}
Write-Output 'vault_roundtrip_ok'
""",encoding='utf-8')
    result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-NonInteractive','-File',str(script),str(source)],
                          capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='vault_roundtrip_ok'


@pytest.mark.skipif(os.name!='nt',reason='Windows named pipe ownership')
def test_dpapi_migration_rejects_unprivileged_pipe_owner(tmp_path):
    import ctypes as c
    from ctypes import wintypes as w
    from operia.security.service_dpapi import migrate_if_requested
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.CreateNamedPipeW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,c.c_void_p]
    kernel.CreateNamedPipeW.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    name='\\\\.\\pipe\\OperiaDpapi-'+hashlib.sha256(str(tmp_path).rstrip('\\').lower().encode()).hexdigest()
    handle=kernel.CreateNamedPipeW(name,0x80003,8,1,4096,128,1000,None)
    assert handle!=c.c_void_p(-1).value
    try:
        with pytest.raises(RuntimeError,match='pipe_owner_rejected'):
            migrate_if_requested(tmp_path)
    finally: kernel.CloseHandle(handle)
