"""Operator's SCM acceptance client. Fresh, synthetic-only deployment, loopback."""
import base64
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from operia.security.service_control import load, environment, atomic_json


def check(condition,code):
    if not condition: raise RuntimeError(code)


def run(root):
    root,config,release_id,release=load(root)
    os.environ.update(environment(root,config))
    address='http://127.0.0.1:'+str(config['port'])
    database=root/'data/storage/e7-service-validation.db'
    marker=root/'management/trial-history.json'
    check(not marker.exists(),'trial_requires_fresh_synthetic_database')

    def api(method,path,payload=None,auth=None,expected=200,raw=None,content_type=None):
        headers={}
        if raw is not None or payload is not None: headers['Content-Type']=content_type or 'application/json'
        if auth: headers['Authorization']='Bearer '+auth
        data=raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        try:
            with urlopen(Request(address+path,data=data,headers=headers,method=method),timeout=30) as response:
                status,body=response.status,response.read()
        except HTTPError as error: status,body=error.code,error.read()
        check(status==expected,'trial_http_'+str(status)+'_expected_'+str(expected)+'_'+path)
        return json.loads(body) if body else None

    check(api('GET','/')['status']=='ready','trial_api_not_ready')
    api('POST','/api/identity/bootstrap-admin',{},expected=403)
    from operia.core import bootstrap as registry
    from operia.core.database import SessionLocal
    from operia.identity.models import Organization,User,Membership
    from operia.identity.security import hash_password
    password=secrets.token_urlsafe(24)
    nonce=secrets.token_hex(5)
    with SessionLocal() as db:
        check(all(o.slug.startswith('e7-scm-') for o in db.query(Organization).all()),'trial_non_synthetic_organization')
        for i in (1,2):
            org=Organization(name=f'Synthetic SCM organization {nonce} {i}',slug=f'e7-scm-{nonce}-{i}'); db.add(org); db.flush()
            user=User(organization_id=org.id,name='Synthetic SCM admin',email=f'admin{i}-{nonce}@e7-scm.invalid',role='admin',status='active',password_hash=hash_password(password))
            db.add(user); db.flush(); db.add(Membership(organization_id=org.id,user_id=user.id,status='active'))
        db.commit()
    auth=api('POST','/api/identity/login',{'email':f'admin1-{nonce}@e7-scm.invalid','password':password})['access_token']
    other=api('POST','/api/identity/login',{'email':f'admin2-{nonce}@e7-scm.invalid','password':password})['access_token']
    case=api('POST','/api/cases',{'case_code':'E7-SCM-'+nonce,'title':'Synthetic service acceptance'},auth)['id']
    analyst=api('POST','/api/identity/users',{'name':'Synthetic reader','email':f'reader-{nonce}@e7-scm.invalid','password':password,'role':'analista'},auth)['id']
    reader=api('POST','/api/identity/login',{'email':f'reader-{nonce}@e7-scm.invalid','password':password})['access_token']
    path=f'/api/cases/{case}'
    api('GET',path,auth=reader,expected=404); api('GET',path,auth=other,expected=404)
    api('POST',path+'/access',{'user_id':analyst,'access':'read','reason':'SCM synthetic grant'},auth)
    api('GET',path,auth=reader)
    api('POST',path+'/access',{'user_id':analyst,'access':'revoked','reason':'SCM synthetic revoke'},auth)
    api('GET',path,auth=reader,expected=404)
    boundary='operia-scm-'+secrets.token_hex(12)
    raw=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.py"\r\nContent-Type: text/plain\r\n\r\n'
        'import math\ndef safe(a,b):\n    return a+b\nraise RuntimeError("MUST_NOT_EXECUTE")\n'+f'\r\n--{boundary}--\r\n').encode()
    evidence=api('POST',f'/api/evidence/case/{case}/upload?description=Synthetic%20SCM',auth=auth,raw=raw,content_type='multipart/form-data; boundary='+boundary)['id']
    api('POST',f'/api/reports/case/{case}/generate',auth=auth)
    history=historical(database)
    job=api('POST',f'/api/static-lab/cases/{case}/evidence/{evidence}/jobs',{'request_key':'synthetic-scm'},auth)
    job_path=f"/api/static-lab/cases/{case}/jobs/{job['id']}"
    api('GET',job_path,auth=other,expected=404)
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        value=api('GET',job_path,auth=auth)
        if value['state'] not in ('queued','preparing','running'): break
        time.sleep(.5)
    check(value['state']=='completed' and value['provider_execution_verified'],'trial_static_service_worker_failed')
    device=api('POST',f'/api/mobile-forensics/cases/{case}/devices',{'label':'Synthetic SCM','platform':'android'},auth)['id']
    native=f'/api/mobile-forensics/native/cases/{case}'
    acquisition=api('POST',native+'/acquisitions',{'device_id':device,'filename':'packages.txt','format':'android-pm-packages',
       'content_base64':base64.b64encode(b'package:com.example.safe\n').decode(),
       'metadata':{'authorization':'Synthetic SCM validation only','scope':'Synthetic text','provenance':'Generated E7 SCM',
           'acquisition_method':'synthetic','acquisition_date_original':'unknown','retention_policy':'Local test only',
           'restrictions':'Not a real acquisition','declared_os_version':'unknown'}},auth)
    job=api('POST',native+'/jobs',{'acquisition_id':acquisition['id']},auth)
    job_path=native+f"/jobs/{job['id']}"
    api('GET',job_path,auth=other,expected=404)
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        value=api('GET',job_path,auth=auth)
        if value['job']['state'] not in ('pendiente','preparando','ejecutando'): break
        time.sleep(.5)
    check(value['job']['state']=='completado_con_limitaciones','trial_native_service_worker_failed_'+value['job']['state'])
    check_history(database,history)
    # No plaintext tokens/passwords persist; rows contain synthetic metadata only.
    # A user-bound encrypted probe lets later restarts verify the same JWT and
    # revocations without keeping a synthetic password or plaintext bearer token.
    from operia.security.dpapi import crypt
    from operia.security.private_files import protect
    probe=root/'management/auth-probe.dpapi'
    with probe.open('xb') as stream:
        protect(probe)
        stream.write(crypt(json.dumps({'auth':auth,'other':other,'reader':reader,'case':case}).encode()))
    atomic_json(marker,history)
    return {'schema':'operia-scm-acceptance/1','http_api_ready':True,'case_default_deny_grant_revoke_verified':True,
            'tenant_isolation_verified':True,'static_service_worker_verified':True,'native_service_worker_verified':True,
            'custody_update_delete_denied':True,'synthetic_history_preserved':True}


def historical(database):
    with closing(sqlite3.connect(database)) as db:
        return {table:[list(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY id').fetchall()]
                for table in ('reports','report_sections','chain_of_custody_actions','custody_ledger_entries')}


def check_history(database,history):
    after=historical(database)
    check(all(after[t][:len(rows)]==rows for t,rows in history.items()),'trial_historical_rows_changed')
    with closing(sqlite3.connect(database)) as db:
        for sql in ("UPDATE chain_of_custody_actions SET action_type='tampered'",'DELETE FROM custody_ledger_entries'):
            try: db.execute(sql); db.rollback()
            except sqlite3.IntegrityError: db.rollback()
            else: raise RuntimeError('trial_custody_mutation_allowed')
        check(db.execute('PRAGMA integrity_check').fetchall()==[('ok',)],'trial_database_integrity')


if __name__=='__main__':
    root=Path(sys.argv[1])
    if len(sys.argv)>2 and sys.argv[2]=='history':
        check_history(root/'data/storage/e7-service-validation.db',json.loads((root/'management/trial-history.json').read_text()))
        from operia.security.dpapi import crypt
        config=load(root)[1]
        probe=json.loads(crypt((root/'management/auth-probe.dpapi').read_bytes(),decrypt=True))
        for label,expected in [('auth',200),('other',404),('reader',404)]:
            request=Request('http://127.0.0.1:'+str(config['port'])+'/api/cases/'+str(probe['case']),headers={'Authorization':'Bearer '+probe[label]})
            try:
                with urlopen(request,timeout=30) as response: status=response.status
            except HTTPError as error: status=error.code
            check(status==expected,'trial_restart_auth_or_scope_changed')
        print(json.dumps({'synthetic_history_preserved':True,'custody_update_delete_denied':True,
                          'jwt_and_revocations_preserved':True,'database_integrity':'ok'}))
    else:
        result=run(root); atomic_json(root/'management/acceptance.json',result); print(json.dumps(result))
