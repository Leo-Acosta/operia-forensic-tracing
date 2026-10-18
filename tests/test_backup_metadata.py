import dataclasses
import json
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest
from operia.forensic_engine.analysis import analyze, capabilities
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_engine.contracts import Source, EngineInputError
from test_native_mobile_workflow import setup, enqueue, database_factory, native_review
from operia.forensic_jobs import worker

FIXTURES = Path(__file__).parent / 'fixtures/native_mobile'

def source(kind='info', raw=None):
    name=f'backup-{kind}.plist'
    return Source('synthetic', name, 'ios', f'apple-backup-{kind}-plist', raw if raw is not None else (FIXTURES/name).read_bytes())

@pytest.mark.parametrize('kind,expected', [('info',5),('manifest',1)])
@pytest.mark.parametrize('binary',[False,True])
def test_original_metadata_manual_oracle(kind,expected,binary):
    src=source(kind)
    if binary: src=dataclasses.replace(src,raw=plistlib.dumps(plistlib.loads(src.raw),fmt=plistlib.FMT_BINARY))
    result=analyze(src)
    assert len(result['artifacts'])==expected
    assert result['source_manifest'][0]['sha256']==sha256(src.raw)
    assert result['coverage']['sources'][0]['status']=='analizado'
    assert canonical_bytes(result)==canonical_bytes(analyze(src))
    assert b'SYNTHETIC-DO-NOT-REPLICATE' not in canonical_bytes(result)
    assert b'SYNTHETIC-PRIVATE' not in canonical_bytes(result) and b'SYNTHETIC-KEY' not in canonical_bytes(result)
    if kind=='info':
        assert [a['locator'] for a in result['artifacts']]==['/Product Type','/Product Version','/Last Backup Date','/Installed Applications/0','/Installed Applications/1']
        assert result['timeline'][0]['normalized_utc']=='2024-01-02T03:04:05.000000Z'
        assert result['timeline'][0]['event_type']=='fecha_de_backup_declarada'
        assert result['artifacts'][-1]['normalized']=={'bundle_identifier':'com.example.second'}
    else:
        assert result['artifacts'][0]['normalized']=={'declared_encrypted':True}
        assert not result['timeline']

@pytest.mark.parametrize('kind',['info','manifest'])
@pytest.mark.parametrize('raw',[b'', b'not a plist', b'bplist00broken', b'<?xml version="1.0"?><plist><dict>',
    b'<?xml version="1.0"?><!DOCTYPE plist [<!ENTITY x "boom">]><plist version="1.0"><dict><key>Product Type</key><string>&x;</string><key>Product Version</key><string>18.0</string><key>IsEncrypted</key><true/></dict></plist>'])
def test_empty_corrupt_and_hostile(kind,raw):
    result=analyze(source(kind,raw))
    assert not result['artifacts'] and result['detection_status']=='sin_datos_analizables'
    assert result['coverage']['sources'][0]['status'] in ('corrupto','sin_registros')

def test_schema_types_duplicates_limits_and_partial_inventory():
    for value in (1,'false',None):
        assert analyze(source('manifest',plistlib.dumps({'IsEncrypted':value}) if value is not None else plistlib.dumps({})))['artifacts']==[]
    duplicate=b'<plist><dict><key>IsEncrypted</key><true/><key>IsEncrypted</key><false/></dict></plist>'
    assert not analyze(source('manifest',duplicate))['artifacts']
    assert analyze(source('manifest',plistlib.dumps({'IsEncrypted':False})))['artifacts'][0]['normalized']=={'declared_encrypted':False}
    tree=plistlib.loads(source().raw); tree['Installed Applications']=['com.example.benign','../../private']
    result=analyze(source(raw=plistlib.dumps(tree)))
    assert len(result['artifacts'])==4 and result['coverage']['sources'][0]['excluded'][0]['locator']=='/Installed Applications/1'
    tree['Last Backup Date']='2024-01-02'
    assert not analyze(source(raw=plistlib.dumps(tree)))['artifacts']
    bounded=plistlib.loads(source().raw)
    bounded['Ignored field']=[str(i) for i in range(20001)]
    assert not analyze(source(raw=plistlib.dumps(bounded,fmt=plistlib.FMT_BINARY)))['artifacts']
    bounded.pop('Ignored field'); bounded['Installed Applications']=['com.example.benign']*5000
    assert not analyze(source(raw=plistlib.dumps(bounded,fmt=plistlib.FMT_BINARY)))['artifacts']
    with pytest.raises(EngineInputError): analyze(source(raw=b' '*(1024*1024+1)))
    deep=b'<plist>'+b'<array>'*60+b'<string>x</string>'+b'</array>'*60+b'</plist>'
    assert not analyze(source(raw=deep))['artifacts']

def test_core_remains_standalone_and_capabilities_are_versioned(tmp_path):
    assert capabilities()['version']=='0.2.0' and len(capabilities()['readers'])==5
    for kind,expected in [('info',5),('manifest',1)]:
        target=tmp_path/(kind+'.json')
        subprocess.run([sys.executable,'-S','-m','operia.forensic_engine',str(FIXTURES/f'backup-{kind}.plist'),
            '--platform','ios','--format',f'apple-backup-{kind}-plist','--output',str(target)],capture_output=True,timeout=10,check=True)
        result=json.loads(target.read_bytes())
        assert len(result['artifacts'])==expected
        if kind=='info': assert result['timeline'][0]['normalized_utc']=='2024-01-02T03:04:05.000000Z'

def test_previous_version_pending_job_is_preserved_and_new_job_is_explicit(client,admin_headers):
    from operia.forensic_jobs.models import ExaminationJob
    root,acquisition,original=setup(client,admin_headers)
    job=enqueue(client,admin_headers,root,acquisition)
    # Reproduce a pending 0.1.0 configuration in the disposable fixture only.
    with database_factory()() as db:
        row=db.get(ExaminationJob,job['id'])
        config=json.loads(row.configuration_json); config['engine_version']='0.1.0'
        raw=canonical_bytes(config)
        row.configuration_json=raw.decode(); row.configuration_sha256=sha256(raw); db.commit()
    assert worker.run_once(database_factory(),timeout=15)
    previous=client.get(root+f"/jobs/{job['id']}",headers=admin_headers).json()['job']
    assert previous['error_code']=='engine_version_or_configuration_mismatch'
    assert previous['configuration']['engine_version']=='0.1.0'
    new=enqueue(client,admin_headers,root,acquisition)
    assert new['id']!=job['id']
    assert worker.run_once(database_factory(),timeout=15)
    current=client.get(root+f"/jobs/{new['id']}",headers=admin_headers).json()
    assert current['result']['engine']['version']=='0.2.0'
    assert client.get(root+f"/jobs/{job['id']}",headers=admin_headers).json()['job']==previous
    assert client.get(root+f"/acquisitions/{acquisition['id']}/original",headers=admin_headers).content==original

@pytest.mark.parametrize('kind,expected',[('info',5),('manifest',1)])
def test_new_readers_real_isolated_worker_and_history(client,admin_headers,kind,expected):
    root,acquisition,original=setup(client,admin_headers,platform='ios',filename=f'backup-{kind}.plist',format=f'apple-backup-{kind}-plist')
    job=enqueue(client,admin_headers,root,acquisition)
    assert worker.run_once(database_factory(),timeout=15)
    path=root+f"/jobs/{job['id']}"
    result=client.get(path,headers=admin_headers)
    assert result.status_code==200,result.text
    detail=result.json()
    assert detail['job']['state']=='completado_con_limitaciones',detail
    report=detail['result']
    assert len(report['artifacts'])==expected
    ids=[a['id'] for a in report['artifacts']]
    reviewed=client.post(path+'/reviews',headers=admin_headers,json=native_review(ids))
    assert reviewed.status_code==200,reviewed.text
    link=client.post(path+f"/integrations?review_id={reviewed.json()['id']}",headers=admin_headers)
    assert link.status_code==200,link.text
    report_path=f"/api/reports/{link.json()['report_id']}"
    preserved=client.get(report_path,headers=admin_headers).json()['markdown_content']
    assert sha256(original) in preserved
    assert client.put(report_path,headers=admin_headers,json={'title':'overwrite'}).status_code==409
    exported=client.post(path+'/exports',headers=admin_headers,json={'format':'json'})
    assert exported.status_code==200,exported.text
    export_url=path+f"/exports/{exported.json()['id']}"
    export_bytes=client.get(export_url,headers=admin_headers).content
    assert sha256(export_bytes)==exported.json()['sha256']
    second=client.post(path+'/reviews',headers=admin_headers,json=native_review(ids,rationale='Rectificación sintética independiente del original'))
    assert second.status_code==200
    assert client.get(report_path,headers=admin_headers).json()['markdown_content']==preserved
    assert client.get(export_url,headers=admin_headers).content==export_bytes
    from test_case_access import analyst, grant
    uid,headers=analyst(client,admin_headers)
    assert client.get(path,headers=headers).status_code==404
    grant(client,admin_headers,acquisition['case_id'],uid,permissions=['read'])
    assert client.get(path,headers=headers).status_code==200
    assert client.post(path+'/reviews',headers=headers,json=native_review(ids)).status_code==404
    grant(client,admin_headers,acquisition['case_id'],uid,'revoked')
    assert client.get(path,headers=headers).status_code==404
    assert client.get(root+f"/acquisitions/{acquisition['id']}/original",headers=admin_headers).content==original
    assert client.get(path,headers=admin_headers).json()['result']==report
