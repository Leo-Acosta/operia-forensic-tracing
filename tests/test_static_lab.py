import json
import importlib
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations
from operia.static_lab.contracts import parse_report, digest
from operia.static_lab.models import StaticImport
from test_case_access import new_case, analyst, grant
from test_native_mobile_workflow import database_factory
from test_security_audit import second_tenant


def report(**updates):
    value={'schema_version':'operia-static-report/1','sample_sha256':digest(b'benign synthetic sample'),
      'provider':'synthetic-fixture','provider_version':'1','provider_revision':'fixture-1',
      'operation':'static-observations','coverage':'partial','limitations':'Synthetic observation, no execution or attribution',
      'observations':[{'id':'o1','member':'classes/example.txt','offset':0,'text':'A string mentions example.test; no network activity is established'}]}
    return {**value, **updates}

def setup(client, headers, code='STATIC'):
    case=new_case(client,headers,code)
    evidence=client.post(f'/api/evidence/case/{case}/upload?description=Benign%20synthetic%20static%20sample',headers=headers,files={'file':('sample.txt',b'benign synthetic sample','application/octet-stream')})
    assert evidence.status_code==200,evidence.text
    return case,evidence.json()['id'],f"/api/static-lab/cases/{case}/evidence/{evidence.json()['id']}/imports"

def test_passive_import_idempotency_original_and_custody(client,admin_headers):
    case,evidence,url=setup(client,admin_headers)
    raw=json.dumps(report(),indent=2).encode()
    result=client.post(url,headers={**admin_headers,'Content-Type':'application/json'},content=raw)
    assert result.status_code==200,result.text
    value=result.json(); path=f"/api/static-lab/cases/{case}/imports/{value['id']}"
    assert value['origin']=='external-import' and value['review_status']=='pending'
    assert value['provider_execution_verified'] is False
    assert client.post(url,headers={**admin_headers,'Content-Type':'application/json'},content=raw).json()==value
    saved=client.get(path,headers=admin_headers)
    assert saved.status_code==200 and 'no-store' in saved.headers['cache-control']
    assert saved.json()['report']==report()
    assert client.get(f'/api/static-lab/cases/{case}/imports',headers=admin_headers).json()==[value]
    assert client.get(f'/api/static-lab/cases/{case}/imports?limit=101',headers=admin_headers).status_code==422
    original=client.get(path+'/original',headers=admin_headers)
    assert original.content==raw and digest(raw)==value['raw_sha256']
    assert original.headers['x-content-type-options']=='nosniff'
    assert client.put(path,headers=admin_headers,json={}).status_code==405
    assert client.delete(path,headers=admin_headers).status_code==405
    with database_factory()() as db:
        from operia.evidence.models import ChainOfCustodyAction
        assert db.query(StaticImport).count()==1
        events=db.query(ChainOfCustodyAction).filter_by(evidence_id=evidence).all()
        assert len(events)>=2 and events[-1].action_type=='importacion_resultado_estatico'
        assert events[-1].hash_before==events[-1].hash_after==report()['sample_sha256']
        with pytest.raises(IntegrityError):
            db.execute(text('UPDATE static_lab_imports SET raw_bytes=:b'),{'b':b'changed'})
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(text('DELETE FROM static_lab_imports'))
        db.rollback()
    assert client.delete(f'/api/cases/{case}',headers=admin_headers).status_code==409
    assert client.delete(f'/api/evidence/{evidence}',headers=admin_headers).status_code==409
    assert client.get(f'/api/static-lab/cases/{case}/providers',headers=admin_headers).json()['execution_enabled'] is False

def test_strict_contract_hostile_inputs():
    raw=json.dumps(report()).encode()
    assert parse_report(raw).provider=='synthetic-fixture'
    for value in [raw.replace(b'"provider":',b'"provider":"other","provider":'),b'['*1200,b'\xff',b'{}'*150000]:
        with pytest.raises(ValueError): parse_report(value)
    for updates in [{'provider_version':'\ud800'}, {'provider_revision':'\x00'}, {'operation':'execute'}, {'command':'whoami'}, {'sample_sha256':'bad'}, {'coverage':'empty'}, {'observations':report()['observations']*201}]:
        with pytest.raises(ValueError): parse_report(json.dumps(report(**updates)).encode())
    for member in ['../escape','C:/secret','https://example.test','a\\b','/etc/passwd','a//b','a/./b']:
        item={**report()['observations'][0],'member':member}
        with pytest.raises(ValueError): parse_report(json.dumps(report(observations=[item])).encode())

def test_permissions_revocation_cross_case_tenant_and_bounds(client,admin_headers):
    case,evidence,url=setup(client,admin_headers)
    uid,headers=analyst(client,admin_headers)
    assert client.post(url,json=report()).status_code==401
    assert client.post(url,headers=headers,json=report()).status_code==404
    assert grant(client,admin_headers,case,uid,permissions=['read','analysis']).status_code==200
    assert client.post(url,headers=headers,json=report()).status_code==404
    assert grant(client,admin_headers,case,uid,permissions=['read','analysis','evidence']).status_code==200
    result=client.post(url,headers=headers,json=report()); assert result.status_code==200,result.text
    path=f"/api/static-lab/cases/{case}/imports/{result.json()['id']}"
    assert client.get(path,headers=headers).status_code==200
    assert client.get(path+'/original',headers=headers).status_code==404
    other,other_evidence,other_url=setup(client,admin_headers,'OTHER-STATIC')
    assert client.get(f"/api/static-lab/cases/{other}/imports/{result.json()['id']}",headers=admin_headers).status_code==404
    _,_,tenant=second_tenant(client)
    assert client.get(path,headers=tenant).status_code==404
    assert client.post(url,headers=tenant,json=report()).status_code==404
    assert client.post(url,headers=admin_headers,json=report(sample_sha256='b'*64)).status_code==409
    assert client.post(url,headers={**admin_headers,'Content-Type':'application/json'},content=b'{"padding":"'+b'x'*262145+b'"}').status_code==413
    assert client.post(url,headers=admin_headers,content=b'{}').status_code==415
    assert grant(client,admin_headers,case,uid,'revoked').status_code==200
    assert client.get(path,headers=headers).status_code==404
    assert client.post(url,headers=headers,json=report()).status_code==404

def test_additive_migration_preserves_existing_rows(tmp_path):
    from sqlalchemy import create_engine
    engine=create_engine('sqlite:///'+str(tmp_path/'copy.db'))
    migration=importlib.import_module('migrations.versions.20261018_0008_static_lab')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE old_records(id INTEGER PRIMARY KEY, value TEXT)'))
        connection.execute(text("INSERT INTO old_records VALUES(1,'preserved')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade(); migration.upgrade(); migration.downgrade()
        assert connection.execute(text('SELECT * FROM old_records')).fetchall()==[(1,'preserved')]
        assert connection.execute(text("SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'static_lab_no_%'")).scalar()==2
def test_new_revision_quota_restart_and_tamper(client,admin_headers,monkeypatch):
    case,evidence,url=setup(client,admin_headers)
    first=client.post(url,headers=admin_headers,json=report()).json()
    changed=report(provider_revision='fixture-2')
    second=client.post(url,headers=admin_headers,json=changed)
    assert second.status_code==200 and second.json()['id']!=first['id']
    path=f"/api/static-lab/cases/{case}/imports/{first['id']}"
    assert client.get(path,headers=admin_headers).json()['report']==report()
    import operia.static_lab.router as router_module
    monkeypatch.setattr(router_module,'MAX_IMPORTS_PER_ORGANIZATION',2)
    denied=client.post(url,headers=admin_headers,json=report(provider_revision='fixture-3'))
    assert denied.status_code==409
    assert client.post(url,headers=admin_headers,json=report()).json()['id']==first['id']
    with database_factory()() as db:
        assert db.get(StaticImport,first['id']).raw_sha256==first['raw_sha256']
        db.execute(text('DROP TRIGGER static_lab_no_update'))
        db.execute(text('UPDATE static_lab_imports SET raw_bytes=:value WHERE id=:id'),{'value':b'corrupted','id':first['id']})
        db.commit()
    assert client.get(path,headers=admin_headers).status_code==409
    assert client.get(path+'/original',headers=admin_headers).status_code==409

def test_missing_or_changed_sample_and_unknown_evidence(client,admin_headers):
    from pathlib import Path
    from operia.evidence.models import Evidence
    case,evidence,url=setup(client,admin_headers)
    assert client.post(url.replace(f'/evidence/{evidence}/', '/evidence/99999/'),headers=admin_headers,json=report()).status_code==404
    with database_factory()() as db:
        path=Path(db.get(Evidence,evidence).file_location)
    path.write_bytes(b'changed synthetic sample')
    assert client.post(url,headers=admin_headers,json=report()).status_code==409
    with database_factory()() as db:
        assert db.query(StaticImport).count()==0
