"""Operator-only, fresh synthetic deployment trial under a real service token.

No live DB, key, acquisition or HTTP destination is accepted as an argument.
"""
import argparse
import base64
from contextlib import closing
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def check(condition, code):
    if not condition:
        raise RuntimeError(code)


def denied(path, existing=False):
    try:
        with path.open('r+b' if existing else 'xb'):
            pass
    except PermissionError:
        return True
    return False


def run_trial(root):
    from operia.security.private_files import token_info, read_key, assert_private
    from operia.security.production import enforce_production
    from operia.core.config import settings
    token = token_info()
    check(token['sid'] == os.environ['OPERIA_EXPECTED_SERVICE_SID'], 'trial_identity_mismatch')
    check(not any(token[k] for k in ('elevated','system','administrator_member')), 'trial_privileged_token')
    check(settings.env == 'production', 'trial_production_policy_required')
    database = root / 'data/storage/e7-runtime-validation.db'
    check(settings.storage_dir.resolve() == database.parent, 'trial_storage_mismatch')
    check(settings.database_url == 'sqlite:///' + database.as_posix(), 'trial_database_mismatch')
    check(not database.exists(), 'trial_requires_fresh_synthetic_database')
    check(settings.auth_signing_key_file.resolve() == root / 'secrets/synthetic-signing-key.bin', 'trial_secret_mismatch')
    read_key(settings.auth_signing_key_file)
    assert_private(settings.auth_signing_key_file.parent)
    enforce_production(settings)
    check(sys.flags.isolated == 1 and sys.flags.no_site == 1, 'trial_python_not_isolated')
    check(Path(sys.base_prefix).resolve() == root / 'runtime', 'trial_external_python_base')
    check(all(Path(p).resolve().is_relative_to(root / 'runtime') or Path(p).resolve() == root / 'code'
              for p in sys.path), 'trial_search_path_escape')
    manifest = json.loads((root / 'runtime-manifest.json').read_text())
    check(all(metadata.version(n) == v for n,v in manifest['packages'].items()), 'trial_dependency_version_mismatch')
    for path in (root/'code/readonly-canary.txt', root/'runtime/python.exe',
                 root/'runtime/Lib/site-packages/fastapi/__init__.py', settings.auth_signing_key_file):
        check(denied(path, True), 'trial_readonly_file_writable')
    for directory in (root/'code',root/'runtime',root/'runtime/Lib/site-packages',root/'secrets',
                      settings.storage_dir/'sandbox-runtime', settings.storage_dir/'static-lab-runtime'):
        check(denied(directory/'forbidden.tmp'), 'trial_readonly_tree_writable')

    import uvicorn
    listener = socket.socket()
    listener.bind(('127.0.0.1',0))
    address = 'http://127.0.0.1:' + str(listener.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config('apps.api.main:app', log_level='warning', access_log=False,
                                          proxy_headers=False, workers=1))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic()+40
    while not server.started and thread.is_alive() and time.monotonic()<deadline:
        time.sleep(.1)
    check(server.started, 'trial_api_startup_failed')

    def api(method, path, payload=None, auth=None, expected=200, raw=None, content_type=None):
        headers = {}
        if raw is not None or payload is not None:
            headers['Content-Type'] = content_type or 'application/json'
        if auth: headers['Authorization'] = 'Bearer ' + auth
        data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        request = Request(address+path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response: status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, error.read()
        check(status==expected, 'trial_http_status_'+str(status)+'_expected_'+str(expected)+'_'+path)
        return json.loads(body) if body else None

    def worker(module, *args):
        completed = subprocess.run([sys.executable,'-B','-m',module,*args], cwd=root/'code',
                                   capture_output=True, timeout=60)
        check(completed.returncode==0, 'trial_worker_cli_failed_'+module)

    try:
        check(api('GET','/')['status']=='ready', 'trial_http_not_ready')
        api('POST','/api/identity/bootstrap-admin',{},expected=403)
        # Fresh synthetic DB only: seed identities, then use normal authentication
        # and case authorization for all evidence/job operations.
        from operia.core.database import SessionLocal
        from operia.identity.models import Organization, User, Membership
        from operia.identity.security import hash_password
        password = secrets.token_urlsafe(24)
        with SessionLocal() as db:
            for index in (1,2):
                org=Organization(name=f'Synthetic runtime organization {index}',slug=f'e7-runtime-{index}')
                db.add(org); db.flush()
                user=User(organization_id=org.id,name='Synthetic runtime admin',email=f'admin{index}@e7.invalid',
                          role='admin',status='active',password_hash=hash_password(password))
                db.add(user); db.flush()
                db.add(Membership(organization_id=org.id,user_id=user.id,status='active'))
            db.commit()
        auth = api('POST','/api/identity/login',{'email':'admin1@e7.invalid','password':password})['access_token']
        other = api('POST','/api/identity/login',{'email':'admin2@e7.invalid','password':password})['access_token']
        case = api('POST','/api/cases',{'case_code':'E7-SYNTHETIC','title':'Synthetic runtime trial'},auth)['id']
        analyst = api('POST','/api/identity/users',{'name':'Synthetic analyst','email':'analyst@e7.invalid',
                      'password':password,'role':'analista'},auth)['id']
        reader = api('POST','/api/identity/login',{'email':'analyst@e7.invalid','password':password})['access_token']
        case_path = f'/api/cases/{case}'
        api('GET',case_path,auth=reader,expected=404)
        api('GET',case_path,auth=other,expected=404)
        api('POST',case_path+'/access',{'user_id':analyst,'access':'read','reason':'Synthetic grant'},auth)
        api('GET',case_path,auth=reader)
        api('POST',case_path+'/access',{'user_id':analyst,'access':'revoked','reason':'Synthetic revocation'},auth)
        api('GET',case_path,auth=reader,expected=404)

        source=b'import math\ndef add(a,b):\n    return a+b\nraise RuntimeError("MUST_NOT_EXECUTE")\n'
        boundary='operia-synthetic-'+secrets.token_hex(12)
        raw=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.py"\r\n'
             'Content-Type: text/plain\r\n\r\n').encode()+source+f'\r\n--{boundary}--\r\n'.encode()
        evidence=api('POST',f'/api/evidence/case/{case}/upload?description=Synthetic%20runtime%20trial',auth=auth,
                     raw=raw,content_type='multipart/form-data; boundary='+boundary)['id']
        report=api('POST',f'/api/reports/case/{case}/generate',auth=auth)['id']
        def historical_rows():
            with closing(sqlite3.connect(database)) as db:
                return {table: db.execute('SELECT * FROM '+table+' ORDER BY id').fetchall()
                        for table in ('reports','report_sections','chain_of_custody_actions','custody_ledger_entries')}
        history = historical_rows()
        static=api('POST',f'/api/static-lab/cases/{case}/evidence/{evidence}/jobs',{'request_key':'synthetic-runtime'},auth)
        static_path=f"/api/static-lab/cases/{case}/jobs/{static['id']}"
        api('GET',static_path,auth=other,expected=404)
        worker('operia.static_lab.worker')
        value=api('GET',static_path,auth=auth)
        check(value['state']=='completed' and value['provider_execution_verified'], 'trial_static_worker_not_verified')
        check(value['report']['provider']=='cpython-ast', 'trial_static_provider_mismatch')

        device=api('POST',f'/api/mobile-forensics/cases/{case}/devices',{'label':'Synthetic','platform':'android'},auth)['id']
        native=f'/api/mobile-forensics/native/cases/{case}'
        acquisition=api('POST',native+'/acquisitions',{'device_id':device,'filename':'packages.txt',
            'format':'android-pm-packages','content_base64':base64.b64encode(b'package:com.example.safe\n').decode(),
            'metadata':{'authorization':'Synthetic runtime validation only','scope':'Synthetic package text',
              'provenance':'Generated for E7 trial','acquisition_method':'synthetic','acquisition_date_original':'unknown',
              'retention_policy':'Local test only','restrictions':'Not a real acquisition','declared_os_version':'unknown'}},auth)
        job=api('POST',native+'/jobs',{'acquisition_id':acquisition['id']},auth)
        worker('operia.forensic_jobs.worker','--once')
        completed=api('GET',native+f"/jobs/{job['id']}",auth=auth)
        check(completed['job']['state']=='completado_con_limitaciones', 'trial_native_worker_not_completed')
        api('GET',native+f"/jobs/{job['id']}",auth=other,expected=404)
        after=historical_rows()
        check(all(after[t][:len(rows)]==rows for t,rows in history.items()), 'trial_historical_rows_changed')
        with closing(sqlite3.connect(database)) as db:
            for sql in ('UPDATE chain_of_custody_actions SET action_type=\'tampered\'', 'DELETE FROM custody_ledger_entries'):
                try:
                    db.execute(sql); db.rollback()
                except sqlite3.IntegrityError:
                    db.rollback()
                else:
                    raise RuntimeError('trial_custody_mutation_allowed')
            check(db.execute('PRAGMA integrity_check').fetchall()==[('ok',)], 'trial_database_integrity')
        return {'schema':'operia-service-runtime-trial/1','identity_verified':True,'production_minimum_policy_passed':True,
                'python_isolated':True,'packages_verified':len(manifest['packages']),'readonly_checks_passed':True,
                'http_api_started':True,'native_worker_completed':True,'static_worker_verified':True,
                'case_default_deny_grant_revoke_verified':True,'tenant_isolation_verified':True,
                'custody_update_delete_denied':True,'synthetic_historical_rows_preserved':True,
                'database_integrity':'ok','production_deployed':False}
    finally:
        server.should_exit=True
        thread.join(timeout=15)
        listener.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.prepare:
        from operia.security.sandbox_runtime import prepare
        from operia.static_lab.runtime import prepare as lab
        prepare(); lab()
        print(json.dumps({'isolated_runtimes_prepared':True}))
    else:
        result=run_trial(root)
        (root/'data/logs/runtime-trial.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
