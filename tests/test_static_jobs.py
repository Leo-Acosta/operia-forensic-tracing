import json
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import pytest
from operia.static_lab import worker, runtime
from operia.static_lab.models import StaticJob
from test_case_access import new_case, analyst, grant
from test_native_mobile_workflow import database_factory
from test_security_audit import second_tenant

SAMPLE=b'import math\nfrom collections import Counter\ndef add(a,b):\n    return a+b\nclass Example:\n    pass\nraise RuntimeError("SAMPLE_MUST_NOT_EXECUTE")\n'

def setup(client,headers,key='job-one',source=SAMPLE):
    case=new_case(client,headers,key)
    evidence=client.post(f'/api/evidence/case/{case}/upload?description=Synthetic%20Python%20source',headers=headers,
        files={'file':('sample.py',source,'text/plain')}).json()['id']
    url=f'/api/static-lab/cases/{case}/evidence/{evidence}/jobs'
    result=client.post(url,headers=headers,json={'request_key':key})
    assert result.status_code==200,result.text
    job=result.json(); path=f"/api/static-lab/cases/{case}/jobs/{job['id']}"
    return case,evidence,url,path,job

def test_real_cpython_provider_in_appcontainer_and_versioned_review(client,admin_headers):
    case,evidence,url,path,job=setup(client,admin_headers)
    assert client.post(url,headers=admin_headers,json={'request_key':'job-one'}).json()==job
    assert worker.run_once(database_factory(),timeout=10)
    result=client.get(path,headers=admin_headers).json()
    assert result['state']=='completed',result
    assert result['provider_execution_verified'] is True
    from pathlib import Path
    Path('storage/test_runs/e5-provider-real-validation.json').write_text(json.dumps({
        'provider':result['report']['provider'],'provider_version':result['report']['provider_version'],
        'provider_revision':result['report']['provider_revision'],'runtime_identity':result['runtime_identity'],
        'sample_sha256':result['source_sha256'],'result_sha256':result['result_sha256'],
        'observations':result['report']['observations'],'state':result['state'],
        'method':'real CPython AST process with required AppContainer and Job Object; manual benign source comparison',
        'sample_execution':False},indent=2),encoding='utf-8')
    uid,headers=analyst(client,admin_headers)
    assert grant(client,admin_headers,case,uid,permissions=['read','analysis','evidence']).status_code==200
    assert client.post(path+'/reviews',headers=headers,json={'expected_version':0,'decision':'accepted','rationale':'Analysis capability alone must not authorize review'}).status_code==404
    assert client.get(f'/api/static-lab/cases/{case}/jobs',headers=headers).status_code==200
    assert client.get(f'/api/static-lab/cases/{case+999}/jobs',headers=headers).status_code==404
    assert result['report']['provider']=='cpython-ast'
    assert [o['text'] for o in result['report']['observations']]==['Import: math','ImportFrom: collections','FunctionDef: add','ClassDef: Example']
    assert [o['offset'] for o in result['report']['observations']]==[0,SAMPLE.index(b'from '),SAMPLE.index(b'def '),SAMPLE.index(b'class ')]
    for expected,decision in [(0,'needs_corroboration'),(1,'accepted')]:
        review=client.post(path+'/reviews',headers=admin_headers,json={'expected_version':expected,'decision':decision,'rationale':'Benign syntax verified by manual source comparison'})
        assert review.status_code==200,review.text
        assert review.json()['version']==expected+1
    assert client.post(path+'/reviews',headers=admin_headers,json={'expected_version':0,'decision':'rejected','rationale':'Outdated review must be rejected'}).status_code==409
    result2=client.get(path,headers=admin_headers).json()
    assert [r['version'] for r in result2['reviews']]==[1,2]
    assert result2['report']==result['report']
    with database_factory()() as db:
        from operia.evidence.models import ChainOfCustodyAction, CustodyLedgerEntry
        action=db.query(ChainOfCustodyAction).filter_by(evidence_id=evidence,action_type='analisis_estatico').one()
        ledger=db.query(CustodyLedgerEntry).filter_by(action_id=action.id).one()
        assert ledger.actor_user_id==db.get(StaticJob,job['id']).actor_id
        assert ledger.organization_id==db.get(StaticJob,job['id']).organization_id
        for query in ('DELETE FROM static_lab_reviews','UPDATE static_lab_reviews SET rationale=\'changed\'','DELETE FROM static_lab_job_events','DELETE FROM static_lab_jobs','UPDATE static_lab_jobs SET source_bytes=\'changed\''):
            with pytest.raises(IntegrityError): db.execute(text(query))
            db.rollback()
    assert client.delete(f'/api/cases/{case}',headers=admin_headers).status_code==409

def test_pending_cancel_revocation_and_restart(client,admin_headers):
    case,evidence,url,path,job=setup(client,admin_headers)
    assert client.post(path+'/cancel',headers=admin_headers).json()['state']=='cancelled'
    assert worker.run_once(database_factory()) is False
    assert client.post(path+'/reviews',headers=admin_headers,json={'expected_version':0,'decision':'accepted','rationale':'Cannot review an uncompleted analysis'}).status_code==409
    with database_factory()() as db:
        db.execute(text('DROP TRIGGER static_jobs_preserve'))
        row=db.get(StaticJob,job['id']); row.state='running'; row.claim='lost-worker'; db.commit()
        from operia.static_lab.models import install_job_protection
        install_job_protection(db.connection()); db.commit()
    assert worker.run_once(database_factory()) is False
    assert client.get(path,headers=admin_headers).json()['state']=='interrupted'
    uid,headers=analyst(client,admin_headers)
    case2,evidence2,url2,path2,job2=setup(client,admin_headers,'job-two')
    assert grant(client,admin_headers,case2,uid,permissions=['read','analysis','evidence']).status_code==200
    created=client.post(url2,headers=headers,json={'request_key':'analyst-job'}).json()
    assert grant(client,admin_headers,case2,uid,'revoked').status_code==200
    # Admin's queued job completes first, revoked operator's job fails closed.
    assert worker.run_once(database_factory())
    assert worker.run_once(database_factory())
    assert client.get(f"/api/static-lab/cases/{case2}/jobs/{created['id']}",headers=admin_headers).json()['error_code']=='access_revoked'
    assert client.get(path2,headers=headers).status_code==404
    _,_,other=second_tenant(client)
    assert client.get(path2,headers=other).status_code==404
    assert client.post(path2+'/cancel',headers=other).status_code==404

def test_invalid_syntax_missing_provider_and_input_limit(client,admin_headers,monkeypatch):
    case,evidence,url,path,job=setup(client,admin_headers,source=b'def invalid(:')
    worker.run_once(database_factory())
    assert client.get(path,headers=admin_headers).json()['state']=='failed'
    case,evidence,url,path,job=setup(client,admin_headers,'missing-provider')
    def missing(): raise RuntimeError('not-prepared')
    monkeypatch.setattr(runtime,'spawn',missing)
    worker.run_once(database_factory())
    value=client.get(path,headers=admin_headers).json()
    assert value['error_code']=='sandbox_or_provider_failed' and value['report'] is None

@pytest.mark.parametrize('mode,expected',[('timeout','timeout'),('overflow','output_limit'),('cancel','cancelled'),('revoke','access_revoked')])
def test_active_job_limits_and_scope(client,admin_headers,monkeypatch,mode,expected):
    import io
    case,evidence,url,path,job=setup(client,admin_headers,key='negative-'+mode)
    uid,headers=analyst(client,admin_headers)
    grant(client,admin_headers,case,uid,permissions=['read','analysis','evidence'])
    client.post(path+'/cancel',headers=admin_headers)
    created=client.post(url,headers=headers,json={'request_key':'negative-worker'}).json()
    worker_path=f"/api/static-lab/cases/{case}/jobs/{created['id']}"
    class Child:
        def __init__(self):
            self.stdout=io.BytesIO(b'x'*262145 if mode=='overflow' else b'')
            self.stdin=io.BytesIO(); self.returncode=None; self.killed=False; self.changed=False
        def poll(self):
            if mode in ('cancel','revoke') and not self.changed:
                self.changed=True
                if mode=='cancel':
                    client.post(worker_path+'/cancel',headers=admin_headers)
                else:
                    grant(client,admin_headers,case,uid,'revoked')
            return self.returncode
        def kill(self): self.killed=True; self.returncode=137
        def wait(self,timeout=None): return self.returncode
        def close(self): pass
    child=Child(); monkeypatch.setattr(runtime,'spawn',lambda:child)
    worker.run_once(database_factory(),timeout=0 if mode=='timeout' else 2)
    value=client.get(worker_path,headers=admin_headers).json()
    assert child.killed and value['report'] is None
    assert value['error_code']==expected
    assert value['state']==('cancelled' if mode=='cancel' else 'failed')

def test_provider_coverage_limits_and_no_unrestricted_entry(monkeypatch):
    from operia.static_lab import provider_entry
    assert provider_entry.analyze(b'# benign empty source')['coverage']=='empty'
    for source in (b'x'*131073,b'\xff',b'('*10000):
        with pytest.raises((ValueError,SyntaxError,UnicodeError)):
            provider_entry.analyze(source)
    def denied(): raise RuntimeError('sandbox_required')
    monkeypatch.setattr(provider_entry,'require_containment',denied)
    with pytest.raises(RuntimeError,match='sandbox_required'):
        provider_entry.main()

def test_fresh_worker_process_consumes_durable_queue_and_attributes_custody(client,admin_headers):
    import os,sys,subprocess
    from pathlib import Path
    from operia.core.config import settings
    from operia.evidence.models import ChainOfCustodyAction,CustodyLedgerEntry
    case,evidence,url,path,job=setup(client,admin_headers,key='fresh-process')
    with database_factory()() as db:
        database_url=str(db.bind.url)
    environment={**os.environ,'OPERIA_DATABASE_URL':database_url,'OPERIA_STORAGE_DIR':str(settings.storage_dir.resolve()),
        'OPERIA_LOCAL_AI_ENABLED':'false','OPERIA_LOCAL_AI_GATEWAY_ENABLED':'false','OPERIA_CONNECTOR_ALLOWED_HOSTS':'[]'}
    process=subprocess.run([sys.executable,'-m','operia.static_lab.worker'],cwd=Path(__file__).resolve().parents[1],
        env=environment,capture_output=True,timeout=40)
    assert process.returncode==0,process.stderr.decode('utf-8',errors='replace')[-1000:]
    assert client.get(path,headers=admin_headers).json()['state']=='completed'
    with database_factory()() as db:
        action=db.query(ChainOfCustodyAction).filter_by(evidence_id=evidence,action_type='analisis_estatico').one()
        assert db.query(CustodyLedgerEntry).filter_by(action_id=action.id).one().actor_user_id==db.get(StaticJob,job['id']).actor_id
