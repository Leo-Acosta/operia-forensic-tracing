"""Actual SCM child supervisor: API, two bounded workers and graceful stop."""
import ctypes
import base64
import json
from ctypes import wintypes
import hashlib
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from operia.security.service_control import load,environment,atomic_json,integrity_rid


def credential_visible(target):
    api=ctypes.WinDLL('advapi32',use_last_error=True)
    api.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p)]
    api.CredFree.argtypes=[ctypes.c_void_p]
    pointer=ctypes.c_void_p()
    if api.CredReadW(target,1,0,ctypes.byref(pointer)):
        api.CredFree(pointer); return True
    if ctypes.get_last_error()!=1168: raise RuntimeError('service_credential_visibility_unverifiable')
    return False


def main(root):
    root,config,release_id,release=load(root)
    os.environ.update(environment(root,config))
    from operia.security.private_files import token_info
    from operia.security.production import enforce_production
    from operia.core.config import settings
    from operia.security.dpapi import crypt
    identity=token_info()
    identity['integrity_rid']=integrity_rid()
    atomic_json(root/'data/logs/service-token.json',identity)
    if identity['sid']!=config['account_sid']: raise RuntimeError('service_wrong_identity')
    if any(identity[k] for k in ('elevated','system','administrator_member')): raise RuntimeError('service_privileged_identity')
    if identity['integrity_rid']!=8192: raise RuntimeError('service_medium_integrity_required')
    for path in (release/'code/readonly-canary.txt',release/'runtime/python.exe',root/'secrets/synthetic-signing-key.bin',root/'config/active-release.txt'):
        try:
            with path.open('r+b'): pass
        except PermissionError: continue
        raise RuntimeError('service_protected_file_writable')
    enforce_production(settings)
    from operia.static_lab.runtime import DEFAULT_ROOT,identity as sandbox_identity,verify
    from operia.security.windows_sandbox import launch
    target=DEFAULT_ROOT/sandbox_identity(); verify(target)
    probe=launch(target,'operia.static_lab.provider_entry',memory_mb=128,cpu_seconds=5,diagnostic_stderr=True)
    try:
        output,_=probe.communicate(json.dumps({'source':base64.b64encode(b'import math\n').decode()}).encode(),timeout=15,maximum=16384)
        diagnostic={'schema':'operia-service-sandbox-selftest/1','exit_code':probe.returncode,
                    'private_service_desktop':bool(probe._desktop),
                    'profile':{k:os.environ.get(k,'') for k in ('USERPROFILE','APPDATA','LOCALAPPDATA')}}
        if probe.returncode:
            diagnostic['synthetic_probe_output']=output.decode('utf-8',errors='replace')[:4096]
        atomic_json(root/'data/logs/sandbox-selftest.json',diagnostic)
        if probe.returncode!=0: raise RuntimeError('service_sandbox_selftest_failed')
        from operia.static_lab.contracts import parse_report
        parse_report(output)
    finally: probe.close()
    from operia.security.sandbox_runtime import DEFAULT_ROOT as native_root,identity as native_identity,verify as native_verify
    native_target=native_root/native_identity(); native_verify(native_target)
    private_canary=root/'data/control/sandbox-private-canary.txt'
    private_canary.write_bytes(b'OPERIA synthetic boundary canary')
    with socket.socket() as boundary_listener:
        boundary_listener.bind(('127.0.0.1',0)); boundary_listener.listen()
        port=boundary_listener.getsockname()[1]
        with socket.create_connection(('127.0.0.1',port),timeout=2): pass  # Positive control.
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GlobalAddAtomW.argtypes=[wintypes.LPCWSTR]; kernel.GlobalAddAtomW.restype=wintypes.WORD
        kernel.GlobalFindAtomW.argtypes=[wintypes.LPCWSTR]; kernel.GlobalFindAtomW.restype=wintypes.WORD
        kernel.GlobalDeleteAtom.argtypes=[wintypes.WORD]
        parent_name='OperiaSvcBoundary-'+str(os.getpid())+'-'+str(time.monotonic_ns())
        parent_atom=kernel.GlobalAddAtomW(parent_name)
        if not parent_atom or kernel.GlobalFindAtomW(parent_name)!=parent_atom:
            raise RuntimeError('service_atom_positive_control_failed')
        probe=None
        try:
            probe=launch(native_target,'scripts.sandbox_probe',memory_mb=128,cpu_seconds=5,diagnostic_stderr=True)
            payload={'parent_pid':os.getpid(),'private_canary':str(private_canary),
                     'runtime_canary':str(native_target/'forbidden-write-canary.txt'),'port':port,'parent_atom':parent_name}
            output,_=probe.communicate(json.dumps(payload).encode(),timeout=15,maximum=16384)
            if probe.returncode!=0: raise RuntimeError('service_boundary_probe_failed')
            boundary=json.loads(output)
            boundary['generation']=os.environ['OPERIA_SERVICE_GENERATION']
            atomic_json(root/'data/logs/sandbox-boundary-selftest.json',boundary)
            fields=('read_private_canary','write_private_canary','write_runtime','spawn_descendant',
                    'parent_memory','loopback','clipboard','default_desktop')
            if (not boundary.get('appcontainer') or not boundary.get('secrets_absent') or not boundary.get('site_packages_absent')
                or boundary.get('parent_atom_isolated') is not True
                or any(not isinstance(boundary.get(k),dict) or 'denied' not in boundary[k] for k in fields)
                or private_canary.read_bytes()!=b'OPERIA synthetic boundary canary'):
                raise RuntimeError('service_boundary_policy_failed')
        finally:
            try:
                if probe: probe.close()
            finally: kernel.GlobalDeleteAtom(parent_atom)
    if credential_visible('OPERIA/service/'+config['service_name']+'/active'):
        raise RuntimeError('service_can_read_operator_credential')
    generation=os.environ['OPERIA_SERVICE_GENERATION']
    if len(generation)!=32 or any(c not in '0123456789abcdef' for c in generation): raise RuntimeError('service_generation_invalid')
    stop=root/'data/control'/('stop-'+generation)
    state=root/'data/logs/service-state.json'
    canary=root/'data/control/credential-canary-v3.dpapi'
    from operia.security.service_dpapi import migrate_if_requested
    migration=migrate_if_requested(root)
    if migration is not None:
        atomic_json(root/'data/logs/dpapi-migration.json',{'generation':generation,**migration})
    raw=b'OPERIA service credential rotation preservation canary/1'
    if canary.exists():
        if crypt(canary.read_bytes(),decrypt=True)!=raw: raise RuntimeError('service_dpapi_canary_changed')
    else: canary.write_bytes(crypt(raw))
    legacy={}
    for name in ('credential-canary.dpapi','credential-canary-v2.dpapi'):
        path=root/'data/control'/name
        if path.exists():
            encrypted=path.read_bytes()
            try: accessible=crypt(encrypted,decrypt=True)==raw
            except RuntimeError: accessible=False
            legacy[name]={'ciphertext_sha256':hashlib.sha256(encrypted).hexdigest(),'decrypts_as_service':accessible}
    atomic_json(root/'data/logs/dpapi-history-check.json',{'generation':generation,'canaries':legacy})
    processes=[]; streams=[]; server=None; thread=None; listener=None
    try:
        import uvicorn
        listener=socket.socket(); listener.bind(('127.0.0.1',config['port']))
        logging_config={'version':1,'disable_existing_loggers':False,
          'handlers':{'file':{'class':'logging.FileHandler','filename':str(root/'data/logs/api.log'),'encoding':'utf-8'}},
          'root':{'handlers':['file'],'level':'WARNING'}}
        server=uvicorn.Server(uvicorn.Config('apps.api.main:app',log_level='warning',access_log=False,
                                            proxy_headers=False,log_config=logging_config))
        thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True); thread.start()
        deadline=time.monotonic()+45
        while not server.started and thread.is_alive() and time.monotonic()<deadline: time.sleep(.1)
        if not server.started: raise RuntimeError('service_api_start_failed')
        for kind in ('native','static'):
            env={**os.environ,'OPERIA_SERVICE_WORKER_KIND':kind,'OPERIA_SERVICE_STOP_FILE':str(stop)}
            stream=(root/'data/logs'/(kind+'.log')).open('ab'); streams.append(stream)
            processes.append(subprocess.Popen([sys.executable,'-B','-m','scripts.windows_service_worker'],
                cwd=release/'code',env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream))
        time.sleep(1)
        if any(p.poll() is not None for p in processes): raise RuntimeError('service_worker_start_failed')
        atomic_json(state,{'schema':'operia-service-state/1','state':'ready','generation':generation,
                          'pid':os.getpid(),'release':release_id,'identity_verified':True,'readonly_checks_passed':True,
                          'credential_vault_visible':False,'dpapi_canary_sha256':hashlib.sha256(raw).hexdigest(),
                          'workers':[p.pid for p in processes]})
        while not stop.exists():
            if not thread.is_alive() or any(p.poll() is not None for p in processes):
                raise RuntimeError('service_child_unexpected_exit')
            time.sleep(.2)
    finally:
        stop.touch(exist_ok=True)
        if server: server.should_exit=True
        if thread: thread.join(timeout=15)
        for p in processes:
            try: p.wait(timeout=35)
            except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=10)
        if listener: listener.close()
        for stream in streams: stream.close()
    atomic_json(state,{'schema':'operia-service-state/1','state':'stopped','generation':generation,'release':release_id})


if __name__=='__main__':
    try:
        root=Path(os.environ['OPERIA_SERVICE_ROOT'])
        _,config,_,_=load(root)
        os.environ.update(environment(root,config))
        from operia.forensic_jobs.worker import worker_lock
        # Settings are configured before importing the existing worker module.
        with worker_lock(Path(os.environ['OPERIA_SERVICE_ROOT'])/'data/control/service-supervisor.lock'):
            main(Path(os.environ['OPERIA_SERVICE_ROOT']))
    except BaseException as error:
        root=Path(os.environ['OPERIA_SERVICE_ROOT'])
        atomic_json(root/'data/logs/supervisor-failure.json',{'schema':'operia-service-failure/1',
                     'error_type':type(error).__name__,'code':str(error) if isinstance(error,RuntimeError) else 'service_internal_error'})
        raise SystemExit(17)
