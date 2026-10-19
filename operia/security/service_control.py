"""Strict, non-secret service configuration and immutable release verification."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import ctypes
from ctypes import wintypes

from operia.forensic_engine.canonical import read_json
from operia.security.private_files import no_links

RELEASE = re.compile(r'^[a-f0-9]{24}$')


def integrity_rid():
    from operia.security.private_files import win_api, sid_string
    adv,kernel=win_api(); token=wintypes.HANDLE(); size=wintypes.DWORD()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):
        raise RuntimeError('service_integrity_unverifiable')
    try:
        adv.GetTokenInformation(token,25,None,0,ctypes.byref(size))
        buffer=ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token,25,buffer,size,ctypes.byref(size)):
            raise RuntimeError('service_integrity_unverifiable')
        sid=sid_string(ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p))[0],adv,kernel)
        if not sid.startswith('S-1-16-'): raise RuntimeError('service_integrity_unverifiable')
        return int(sid.rsplit('-',1)[1])
    finally: kernel.CloseHandle(token)


def verify_tree(root, expected):
    root = no_links(root)
    actual = {}
    for parent, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            path = Path(parent) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 1024:
                raise RuntimeError('service_release_link_rejected')
        for name in names:
            path = Path(parent) / name
            if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_nlink != 1:
                raise RuntimeError('service_release_hardlink_rejected')
            actual[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError('service_release_integrity_failed')


def load(root, verify=True):
    root = no_links(root).resolve()
    config = read_json((root/'config/service.json').read_bytes(),limit=16384)
    if (not isinstance(config,dict) or set(config) != {'schema','service_name','account_sid','port','synthetic_only'}
        or config['schema'] != 'operia-windows-service/1'
        or not re.fullmatch(r'Operia[A-Za-z0-9]{1,40}',config['service_name'])
        or not re.fullmatch(r'S-1-5-21-\d+-\d+-\d+-\d+',config['account_sid'])
        or type(config['port']) is not int or not 1024 <= config['port'] <= 65535
        or config['synthetic_only'] is not True):
        raise RuntimeError('service_configuration_rejected')
    release_id = (root/'config/active-release.txt').read_text(encoding='ascii').strip()
    if not RELEASE.fullmatch(release_id):
        raise RuntimeError('service_release_id_rejected')
    release = no_links(root/'releases'/release_id)
    if verify:
        code = read_json((release/'layout.json').read_bytes(),limit=2*1024*1024)
        runtime = read_json((release/'runtime-manifest.json').read_bytes(),limit=4*1024*1024)
        if code.get('schema') != 'operia-service-staging/1' or runtime.get('schema') != 'operia-service-runtime/1':
            raise RuntimeError('service_release_manifest_rejected')
        verify_tree(release/'code',code['code_files'])
        verify_tree(release/'runtime',runtime['files'])
    return root,config,release_id,release


def environment(root, config):
    storage=root/'data/storage'
    return {'OPERIA_ENV':'production','OPERIA_STORAGE_DIR':str(storage),
            'OPERIA_DATABASE_URL':'sqlite:///'+(storage/'e7-service-validation.db').as_posix(),
            'OPERIA_AUTH_SIGNING_KEY_FILE':str(root/'secrets/synthetic-signing-key.bin'),
            'OPERIA_CORS_ORIGINS':'["https://synthetic-gateway.invalid"]',
            'OPERIA_LOCAL_RECOVERY_ENABLED':'false','OPERIA_LOCAL_AI_ENABLED':'false',
            'OPERIA_LOCAL_AI_GATEWAY_ENABLED':'false','OPERIA_CONNECTOR_ALLOWED_HOSTS':'[]'}


def atomic_json(path, value):
    temporary=path.with_suffix('.new')
    with temporary.open('w',encoding='utf-8') as output:
        json.dump(value,output,sort_keys=True); output.flush(); os.fsync(output.fileno())
    os.replace(temporary,path)
