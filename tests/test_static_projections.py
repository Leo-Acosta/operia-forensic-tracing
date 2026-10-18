import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import pytest
from operia.static_lab import worker
from operia.static_lab.models import StaticProjection
from test_static_jobs import setup
from test_case_access import analyst,grant
from test_native_mobile_workflow import database_factory
from test_security_audit import second_tenant

def prepare(client,headers):
    case,evidence,url,path,job=setup(client,headers)
    worker.run_once(database_factory())
    value=client.get(path,headers=headers).json()
    assert value['state']=='completed',value
    payload={'review_version':1,'observation_ids':[o['id'] for o in value['report']['observations'][:2]]}
    return case,path,payload

def review(client,headers,path,version=0,decision='accepted'):
    result=client.post(path+'/reviews',headers=headers,json={'expected_version':version,'decision':decision,'rationale':'Compared static declarations with benign original source; no behavior established.'})
    assert result.status_code==200,result.text

def test_projection_review_required_idempotent_preserved_and_exportable(client,admin_headers):
    case,path,payload=prepare(client,admin_headers)
    assert client.post(path+'/projections',headers=admin_headers,json=payload).status_code==409
    review(client,admin_headers,path)
    result=client.post(path+'/projections',headers=admin_headers,json=payload)
    assert result.status_code==200,result.text
    value=result.json()
    assert client.post(path+'/projections',headers=admin_headers,json={**payload,'observation_ids':list(reversed(payload['observation_ids']))}).json()==value
    finding=client.get(f"/api/cases/{case}/findings",headers=admin_headers).json()[0]
    assert finding['id']==value['finding_id'] and finding['status']=='requiere corroboracion'
    report=client.get(f"/api/reports/{value['report_id']}",headers=admin_headers)
    assert report.status_code==200 and report.json()['status']=='borrador'
    original=report.json()['markdown_content']
    exported=client.get(f"/api/reports/{value['report_id']}/export/markdown",headers=admin_headers)
    assert exported.status_code==200 and exported.content.decode('utf-8')==original
    assert 'Observaciones seleccionadas' in exported.text and 'cpython-ast' in exported.text
    assert client.get(f"/api/reports/{value['report_id']}/export/pdf",headers=admin_headers).status_code==200
    assert client.delete(f"/api/legal-report/findings/{value['finding_id']}",headers=admin_headers).status_code==409
    assert client.put(f"/api/reports/{value['report_id']}",headers=admin_headers,json={'markdown_content':'overwrite attempt'}).status_code==409
    review(client,admin_headers,path,1,'rejected')
    assert client.post(path+'/projections',headers=admin_headers,json={**payload,'review_version':2}).status_code==409
    assert client.get(f"/api/reports/{value['report_id']}",headers=admin_headers).json()['markdown_content']==original
    review(client,admin_headers,path,2,'accepted')
    assert client.post(path+'/projections',headers=admin_headers,json=payload).status_code==409
    corrected=client.post(path+'/projections',headers=admin_headers,json={**payload,'review_version':3})
    assert corrected.status_code==200 and corrected.json()['report_id']!=value['report_id']
    assert client.get(f"/api/reports/{value['report_id']}",headers=admin_headers).json()['markdown_content']==original
    assert len(client.get(path+'/projections',headers=admin_headers).json())==2
    with database_factory()() as db:
        from operia.static_lab.contracts import digest
        item=db.get(StaticProjection,value['id'])
        assert digest(item.snapshot_bytes)==value['snapshot_sha256']
        snapshot=json.loads(item.snapshot_bytes)
        assert snapshot['review']['version']==1 and len(snapshot['observations'])==2
        with pytest.raises(IntegrityError): db.execute(text('DELETE FROM static_lab_projections'))
        db.rollback()
        with pytest.raises(IntegrityError): db.execute(text("UPDATE static_lab_projections SET snapshot_sha256='altered'"))
        db.rollback()

def test_projection_selection_caps_tenant_and_revocation(client,admin_headers):
    case,path,payload=prepare(client,admin_headers); review(client,admin_headers,path)
    for ids in (['unknown'],payload['observation_ids']*2):
        assert client.post(path+'/projections',headers=admin_headers,json={**payload,'observation_ids':ids}).status_code==422
    uid,headers=analyst(client,admin_headers)
    grant(client,admin_headers,case,uid,permissions=['read','analysis','evidence'])
    assert client.post(path+'/projections',headers=headers,json=payload).status_code==404
    grant(client,admin_headers,case,uid,permissions=['read','analysis','evidence','reports'])
    assert client.post(path+'/projections',headers=headers,json=payload).status_code==200
    grant(client,admin_headers,case,uid,'revoked')
    assert client.get(path+'/projections',headers=headers).status_code==404
    _,_,other=second_tenant(client)
    assert client.get(path+'/projections',headers=other).status_code==404
    assert client.post(path+'/projections',headers=other,json=payload).status_code==404
