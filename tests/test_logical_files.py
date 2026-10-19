import json
from datetime import datetime
from pathlib import Path
import plistlib
import sqlite3
import subprocess
import sys

import pytest

from operia.forensic_engine.analysis import analyze
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_engine.contracts import Source, EngineInputError
from operia.forensic_engine.logical_files import component, pack_logical, MANIFEST_FORMATS
from operia.forensic_engine.wal_readers import pack_set
from test_manifest_sqlite import image, SCHEMA

IDS = [c*40 for c in 'abcdef']
PATHS = ['Library/sample.plist','Library/sample.txt','Library/sample.db','Library/unknown.bin','Library/omitted.txt','Library']
ROWS = [(file_id,'HomeDomain',path,2 if i==5 else 1,b'MANIFEST-BLOB-PRIVATE') for i,(file_id,path) in enumerate(zip(IDS,PATHS))]


def source(raw):
    return Source('synthetic','logical-set.json','ios','apple-backup-logical-set',raw)


def fixtures(binary=False):
    plist = plistlib.dumps({'flag':True,'count':2,'nested':{'id':'benign'},'blob':b'PLIST-BLOB-PRIVATE'},
                          fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML)
    db=sqlite3.connect(':memory:')
    try:
        db.execute('CREATE TABLE Example(secret TEXT)')
        db.execute("INSERT INTO Example VALUES('SQL-ROW-PRIVATE')")
        db.commit(); sql=db.serialize()
    finally: db.close()
    return image(rows=ROWS), [(IDS[0],plist),(IDS[1],b'first line\nsecond line\n'),(IDS[2],sql),(IDS[3],b'BINARY-PRIVATE')]


@pytest.mark.parametrize('binary',[False,True])
def test_manual_oracle_hashes_selection_and_reproducibility(binary):
    manifest,files=fixtures(binary)
    raw=pack_logical(manifest,files); result=analyze(source(raw))
    assert len(result['artifacts'])==11 and not result['timeline']
    assert result['source_manifest'][0]['sha256']==sha256(raw)
    provenance=result['artifacts'][0]['normalized']
    assert provenance['selected_files']==4 and provenance['manifest_regular_files']==5
    assert provenance['omitted_regular_files']==1 and provenance['manifest_directories']==1
    scalar={a['locator'].split('/plist/',1)[1]:a['normalized']['value'] for a in result['artifacts'] if a['kind']=='logical_plist_scalar'}
    assert scalar=={'count':2,'flag':True,'nested/id':'benign'}
    assert [a['normalized']['text'] for a in result['artifacts'] if a['kind']=='logical_text_line']==['first line','second line']
    assert [a['normalized']['name'] for a in result['artifacts'] if a['kind']=='sqlite_schema_metadata']==['Example']
    metadata=[a['normalized'] for a in result['artifacts'] if a['kind']=='logical_file_preservation']
    assert {r['file_id']:r['sha256'] for r in metadata}=={fid:sha256(data) for fid,data in files}
    for canary in (b'MANIFEST-BLOB-PRIVATE',b'PLIST-BLOB-PRIVATE',b'SQL-ROW-PRIVATE',b'BINARY-PRIVATE'):
        assert canary not in canonical_bytes(result)
    assert len(result['coverage']['sources'][0]['excluded'])==4
    assert canonical_bytes(result)==canonical_bytes(analyze(source(raw)))
    assert pack_logical(manifest,files[::-1])==raw


def test_plist_pointer_escaping_and_declared_date_without_timeline():
    data=plistlib.dumps({'a/b~c':['safe',datetime(2024,1,2,3,4,5)]})
    result=analyze(source(pack_logical(image(rows=ROWS),[(IDS[0],data)])))
    values=[a for a in result['artifacts'] if a['kind']=='logical_plist_scalar']
    assert values[0]['locator'].endswith('/plist/a~1b~0c/0')
    assert values[1]['normalized']=={'value_type':'datetime','value':'2024-01-02T03:04:05Z',
                                     'file_id':IDS[0],'file_sha256':sha256(data),
                                     'content_locator':'plist/a~1b~0c/1'}
    assert not result['timeline']


def test_identical_content_in_distinct_files_keeps_independent_file_context():
    raw=pack_logical(image(rows=ROWS),[(IDS[1],b'same line\n'),(IDS[4],b'same line\n')])
    result=analyze(source(raw))
    lines=[a for a in result['artifacts'] if a['kind']=='logical_text_line']
    assert len(lines)==2 and all(a['duplicate_of'] is None for a in lines)
    assert {a['normalized']['file_id'] for a in lines}=={IDS[1],IDS[4]}
    assert all(a['normalized']['file_sha256']==sha256(b'same line\n') for a in lines)


def test_equal_values_in_distinct_keys_and_lines_keep_observed_positions():
    manifest=image(rows=ROWS)
    for file_id,data,kind in ((IDS[0],plistlib.dumps({'first':True,'second':True}),'logical_plist_scalar'),
                              (IDS[1],b'same\nsame\n','logical_text_line')):
        records=[a for a in analyze(source(pack_logical(manifest,[(file_id,data)])))['artifacts'] if a['kind']==kind]
        assert len(records)==2 and all(a['duplicate_of'] is None for a in records)
        assert len({a['normalized']['content_locator'] for a in records})==2


@pytest.mark.parametrize('raw',[
    b'not plist', b'<?xml version="1.0"?><plist><dict><key>x</key><unknown>bad</unknown></dict></plist>',
    b'<?xml version="1.0"?><!DOCTYPE plist [<!ENTITY x "SECRET">]><plist><dict><key>x</key><string>&x;</string></dict></plist>',
    b'<plist><dict><key>x</key><string>one</string><key>x</key><string>two</string></dict></plist>',
    plistlib.dumps({'$archiver':'NSKeyedArchiver','$objects':['ARCHIVER-PRIVATE']}),
    plistlib.dumps({'nested':{'$objects':['ARCHIVER-PRIVATE']}}),
    plistlib.dumps({str(i):i for i in range(129)}),
    plistlib.dumps({'x':[[[[[[[[[[[[[[[[[[[[[[[[[[1]]]]]]]]]]]]]]]]]]]]]]]]]]}),
], ids=['invalid','unknown-xml','entity','duplicate-key','archiver','nested-archiver','too-many-values','deep-tree'])
def test_invalid_active_or_excessive_plists_preserve_hash_without_partial_content(raw):
    result=analyze(source(pack_logical(image(rows=ROWS),[(IDS[0],raw)])))
    assert [a['kind'] for a in result['artifacts']]==['logical_selection_provenance','logical_file_preservation']
    assert result['artifacts'][1]['normalized']['sha256']==sha256(raw)
    assert any(e['locator'].endswith('/content') for e in result['coverage']['sources'][0]['excluded'])
    assert b'ARCHIVER-PRIVATE' not in canonical_bytes(result)


@pytest.mark.parametrize('raw',[b'\xff',b'bad\0text',b'bad\x1btext',b'bad\x7ftext',b'x'*65537,b'x'*2049,b'line\n'*129],
                         ids=['encoding','nul','escape','del','byte-budget','line-budget','line-count'])
def test_invalid_or_excessive_text_is_not_silently_truncated(raw):
    result=analyze(source(pack_logical(image(rows=ROWS),[(IDS[1],raw)])))
    assert len(result['artifacts'])==2
    assert any(e['locator'].endswith('/content') for e in result['coverage']['sources'][0]['excluded'])


@pytest.mark.parametrize('mutation',['hash','manifest_hash','extra_key','duplicate_id','unknown_id','directory','bad_id','unsafe_path','empty','too_many','oversize'])
def test_invalid_package_or_association_rejects_all_artifacts(mutation):
    manifest,files=fixtures()
    value=json.loads(pack_logical(manifest,files[:1]))
    if mutation=='hash': value['files'][0]['sha256']='0'*64
    elif mutation=='manifest_hash': value['manifest']['sha256']='0'*64
    elif mutation=='extra_key': value['files'][0]['path']='../../private'
    elif mutation=='duplicate_id': value['files'].append(value['files'][0])
    elif mutation=='unknown_id': value['files'][0]['file_id']='0'*40
    elif mutation=='directory': value['files'][0]['file_id']=IDS[5]
    elif mutation=='bad_id': value['files'][0]['file_id']='../escape'
    elif mutation=='unsafe_path':
        rows=list(ROWS); rows[0]=(IDS[0],'HomeDomain','../../private.plist',1,b'x')
        value['manifest'].update(component(image(rows=rows)))
    elif mutation=='empty': value['files']=[]
    elif mutation=='too_many': value['files']*=33
    else: value['files'][0].update(component(b'x'*(256*1024+1)))
    result=analyze(source(canonical_bytes(value)))
    assert not result['artifacts'] and result['detection_status']=='sin_datos_analizables'


def wal_manifest(tmp_path, first_path=PATHS[0]):
    path=tmp_path/'manifest-source.db'; db=sqlite3.connect(path)
    try:
        db.execute(SCHEMA)
        rows=list(ROWS); rows[0]=(IDS[0],'HomeDomain','Library/old.plist',1,b'x')
        db.executemany('INSERT INTO Files VALUES(?,?,?,?,?)',rows); db.commit()
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        db.execute('UPDATE Files SET relativePath=? WHERE fileID=?',(first_path,IDS[0])); db.commit()
        return pack_set(path.read_bytes(),Path(str(path)+'-wal').read_bytes(),Path(str(path)+'-shm').read_bytes())
    finally: db.close()


def test_wal_manifest_correlates_current_declaration_and_retains_exclusions(tmp_path):
    _,files=fixtures()
    raw=pack_logical(wal_manifest(tmp_path),files,MANIFEST_FORMATS[1])
    result=analyze(source(raw))
    assert len(result['artifacts'])==11
    assert result['artifacts'][1]['normalized']['relative_path']==PATHS[0]
    assert result['artifacts'][0]['normalized']['manifest_format']==MANIFEST_FORMATS[1]
    snapshot=result['artifacts'][0]['normalized']['manifest_snapshot']
    assert snapshot['commits']==1 and snapshot['last_commit_frame']>0


def test_logical_sqlite_wal_or_active_schema_not_combined_or_executed():
    manifest,files=fixtures(); data=files[2][1]
    changed=data[:18]+b'\2\2'+data[20:]
    assert len(analyze(source(pack_logical(manifest,[(IDS[2],changed)])))['artifacts'])==2
    db=sqlite3.connect(':memory:')
    try:
        db.execute('CREATE TABLE normal(a TEXT)'); db.execute('CREATE VIEW active AS SELECT * FROM normal'); db.commit()
        data=db.serialize()
    finally: db.close()
    assert len(analyze(source(pack_logical(manifest,[(IDS[2],data)])))['artifacts'])==2


def test_pack_helper_limits():
    manifest,files=fixtures()
    for selected in ([],files*9,[(IDS[0],b'x'*(256*1024+1))]):
        with pytest.raises(EngineInputError): pack_logical(manifest,selected)


def test_cli_explicit_files_preserves_copies_and_never_discovers_omitted_files(tmp_path):
    manifest,files=fixtures(); mp=tmp_path/'Manifest.db'; fp=tmp_path/'selected.plist'
    mp.write_bytes(manifest); fp.write_bytes(files[0][1]); (tmp_path/'decoy.txt').write_bytes(b'DO-NOT-DISCOVER')
    package=tmp_path/'logical-set.json'; output=tmp_path/'result.json'
    command=[sys.executable,'-S','scripts/preserve_ios_logical.py','--manifest',str(mp),'--file',IDS[0]+'='+str(fp),'--output',str(package)]
    subprocess.run(command,check=True,capture_output=True,timeout=15)
    assert package.read_bytes()==pack_logical(manifest,files[:1]) and b'DO-NOT-DISCOVER' not in package.read_bytes()
    subprocess.run([sys.executable,'-S','-m','operia.forensic_engine',str(package),'--platform','ios',
                    '--format','apple-backup-logical-set','--output',str(output)],check=True,capture_output=True,timeout=15)
    assert len(json.loads(output.read_bytes())['artifacts'])==5
    assert mp.read_bytes()==manifest and fp.read_bytes()==files[0][1]
    assert subprocess.run(command,capture_output=True).returncode!=0
    assert not list(tmp_path.glob('*.db-wal')) and not list(tmp_path.glob('*.db-shm'))


@pytest.mark.parametrize('with_wal',[False,True])
@pytest.mark.parametrize('with_json',[False,True])
def test_real_logical_worker_permissions_custody_and_historical_reports(tmp_path,client,admin_headers,with_wal,with_json):
    from test_native_mobile_workflow import setup,enqueue,database_factory,native_review
    from test_case_access import analyst,grant
    from test_security_audit import second_tenant
    from operia.forensic_jobs import worker
    manifest,files=fixtures()
    first_path = 'Library/sample.json' if with_json else PATHS[0]
    if with_json:
        rows = list(ROWS); rows[0] = (IDS[0], 'HomeDomain', first_path, 1, b'private')
        manifest = image(rows=rows)
        files[0] = (IDS[0], canonical_bytes({'flag': True, 'count': 2, 'nested': {'id': 'benign'}}))
    if with_wal: manifest=wal_manifest(tmp_path, first_path)
    raw=pack_logical(manifest,files,MANIFEST_FORMATS[int(with_wal)])
    root,acquisition,_=setup(client,admin_headers,platform='ios',filename='logical-set.json',format='apple-backup-logical-set',raw=raw)
    job=enqueue(client,admin_headers,root,acquisition)
    assert worker.run_once(database_factory(),timeout=15)
    path=root+f"/jobs/{job['id']}"; detail=client.get(path,headers=admin_headers).json()
    assert detail['job']['state']=='completado_con_limitaciones',detail
    assert len(detail['result']['artifacts'])==11
    if with_json:
        assert len([a for a in detail['result']['artifacts'] if a['kind'] == 'logical_json_scalar']) == 3
    ids=[a['id'] for a in detail['result']['artifacts']]
    review=client.post(path+'/reviews',headers=admin_headers,json=native_review(ids)).json()
    exported=client.post(path+'/exports',headers=admin_headers,json={'format':'json'}).json()
    export_path=path+f"/exports/{exported['id']}"; original_export=client.get(export_path,headers=admin_headers).content
    integration=client.post(path+f"/integrations?review_id={review['id']}",headers=admin_headers)
    assert integration.status_code==200,integration.text
    report_path=f"/api/reports/{integration.json()['report_id']}"; report=client.get(report_path,headers=admin_headers).json()
    assert client.put(report_path,headers=admin_headers,json={'title':'overwrite'}).status_code==409
    assert client.post(path+'/reviews',headers=admin_headers,json=native_review(ids,rationale='Nueva revisión sintética')).status_code==200
    assert client.get(report_path,headers=admin_headers).json()==report
    assert client.get(export_path,headers=admin_headers).content==original_export
    uid,headers=analyst(client,admin_headers)
    assert client.get(path,headers=headers).status_code==404
    grant(client,admin_headers,acquisition['case_id'],uid,permissions=['read'])
    assert client.get(path,headers=headers).status_code==200
    assert client.post(path+'/reviews',headers=headers,json=native_review(ids)).status_code==404
    assert len(client.get(path,headers=admin_headers).json()['reviews'])==2
    grant(client,admin_headers,acquisition['case_id'],uid,'revoked')
    assert client.get(path,headers=headers).status_code==404
    _,_,foreign=second_tenant(client)
    assert client.get(path,headers=foreign).status_code==404
    assert client.get(root+f"/acquisitions/{acquisition['id']}/original",headers=admin_headers).content==raw
