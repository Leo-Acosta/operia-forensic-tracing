import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from operia.forensic_engine import ENGINE_VERSION
from operia.forensic_engine.analysis import analyze
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_engine.contracts import Source
from operia.forensic_engine.sqlite_readers import preserved_copy

SCHEMA = 'CREATE TABLE Files(fileID TEXT PRIMARY KEY,domain TEXT,relativePath TEXT,flags INTEGER,file BLOB)'
ROWS = [('a'*40,'HomeDomain','Library/benign.txt',1,b'SYNTHETIC-PRIVATE-BLOB'),
        ('b'*40,'HomeDomain','Library',2,b'NSKeyedArchiver-not-interpreted')]

def image(schema=SCHEMA, rows=ROWS, extra=()):
    db=sqlite3.connect(':memory:')
    try:
        db.execute(schema)
        if rows: db.executemany('INSERT INTO Files VALUES(?,?,?,?,?)',rows)
        for sql in extra: db.execute(sql)
        db.commit()
        return db.serialize()
    finally: db.close()

def source(raw,format='apple-backup-manifest-sqlite',platform='ios'):
    return Source('synthetic','Manifest.db',platform,format,raw)

def test_manifest_fixed_query_oracle_and_preserved_copy(tmp_path):
    raw=image(); path=tmp_path/'Manifest.db'; path.write_bytes(raw)
    result=analyze(source(path.read_bytes()))
    assert len(result['artifacts'])==2 and not result['timeline']
    assert [r['locator'] for r in result['artifacts']]==['Files/fileID:'+'a'*40,'Files/fileID:'+'b'*40]
    assert result['artifacts'][0]['normalized']==dict(file_id='a'*40,domain='HomeDomain',relative_path='Library/benign.txt',flags=1)
    assert result['source_manifest'][0]['sha256']==sha256(raw)
    assert path.read_bytes()==raw and not (tmp_path/'Manifest.db-wal').exists() and not (tmp_path/'Manifest.db-journal').exists()
    assert b'SYNTHETIC-PRIVATE-BLOB' not in canonical_bytes(result)
    assert canonical_bytes(result)==canonical_bytes(analyze(source(raw)))

@pytest.mark.parametrize('platform',['ios','android'])
def test_catalog_ignores_row_values_sql_and_names_as_code(platform):
    raw=image(extra=('CREATE TABLE "odd; DROP TABLE Files;--"(secret TEXT)',
                     'INSERT INTO "odd; DROP TABLE Files;--" VALUES("PRIVATE-ROW")',
                     'CREATE INDEX FilesDomainIdx ON Files(domain)'))
    result=analyze(source(raw,'sqlite-schema-catalog',platform))
    assert len(result['artifacts'])==3
    assert any(a['normalized']['name']=='odd; DROP TABLE Files;--' for a in result['artifacts'])
    assert b'PRIVATE-ROW' not in canonical_bytes(result) and b'SYNTHETIC-PRIVATE-BLOB' not in canonical_bytes(result)
    assert all(set(a['normalized'])=={'object_type','name','table'} for a in result['artifacts'])

@pytest.mark.parametrize('sql',[
    'UPDATE Files SET flags=2','DELETE FROM Files','DROP TABLE Files',
    "ATTACH DATABASE 'should-not-exist.db' AS external",'VACUUM',
    'PRAGMA writable_schema=ON','PRAGMA query_only=OFF','PRAGMA journal_mode=WAL',
    "SELECT load_extension('bad')",'SELECT randomblob(10)','SELECT file FROM Files'])
def test_allowlist_blocks_write_attach_extensions_functions_and_blob(sql):
    raw=image()
    with preserved_copy(raw) as db:
        with pytest.raises(sqlite3.DatabaseError): db.execute(sql).fetchall()
        assert db.execute('SELECT flags FROM Files ORDER BY fileID').fetchall()==[(1,),(2,)]
    assert len(analyze(source(raw))['artifacts'])==2

@pytest.mark.parametrize('extra',[
    ('CREATE VIEW v AS SELECT * FROM Files',),
    ('CREATE TRIGGER tr AFTER INSERT ON Files BEGIN DELETE FROM Files; END',),
    ('CREATE VIRTUAL TABLE vt USING fts5(data)',),
    ('CREATE TABLE computed(a TEXT,b TEXT AS (upper(a)))',),
    ('CREATE TABLE checks(a TEXT CHECK(length(a)>0))',),
    ('CREATE INDEX expr ON Files(length(domain))',),
    ('CREATE INDEX partial ON Files(domain) WHERE flags=1',)])
def test_active_or_expression_schema_rejected_without_partial_output(extra):
    for format in ('apple-backup-manifest-sqlite','sqlite-schema-catalog'):
        result=analyze(source(image(extra=extra),format))
        assert not result['artifacts'] and result['coverage']['sources'][0]['status']=='no_compatible'

@pytest.mark.parametrize('raw',[b'',b'not sqlite',b'SQLite format 3\0'+b'\0'*84])
def test_empty_invalid_and_encrypted_looking_images(raw):
    result=analyze(source(raw))
    assert not result['artifacts'] and result['detection_status']=='sin_datos_analizables'

def test_header_wal_truncation_trailing_and_encoding_are_not_repaired():
    raw=image()
    variants=[raw[:-1],raw+b'extra',raw[:18]+b'\x02\x02'+raw[20:],raw[:56]+b'\0\0\0\2'+raw[60:]]
    for changed in variants:
        assert not analyze(source(changed))['artifacts']
    assert len(analyze(source(raw))['artifacts'])==2

def test_schema_variant_row_exclusions_empty_and_overflow(monkeypatch):
    assert not analyze(source(image(schema='CREATE TABLE Files(fileID TEXT,domain TEXT,relativePath TEXT,flags INTEGER,file BLOB)')))['artifacts']
    empty=analyze(source(image(rows=[])))
    assert not empty['artifacts'] and empty['coverage']['sources'][0]['status']=='sin_registros'
    raw=image(rows=[ROWS[0],('b'*40,'HomeDomain','../../private',1,b'x'),('c'*40,'HomeDomain','ok',99,b'x')])
    result=analyze(source(raw)); assert len(result['artifacts'])==1
    assert len(result['coverage']['sources'][0]['excluded'])==2
    many=[(f'{i:040x}','HomeDomain',f'Library/{i}',1,b'x') for i in range(5001)]
    assert not analyze(source(image(rows=many)))['artifacts']
    from operia.forensic_engine import sqlite_readers
    monkeypatch.setattr(sqlite_readers,'MAX_VM_STEPS',0)
    assert not analyze(source(image(rows=many[:200])))['artifacts']

def test_cli_standalone_and_original_remains_exact(tmp_path):
    path=tmp_path/'Manifest.db'; original=image(); path.write_bytes(original)
    for format in ('apple-backup-manifest-sqlite','sqlite-schema-catalog'):
        target=tmp_path/(format+'.json')
        subprocess.run([sys.executable,'-S','-m','operia.forensic_engine',str(path),'--platform','ios','--format',format,
                        '--output',str(target)],capture_output=True,timeout=15,check=True)
        result=json.loads(target.read_bytes())
        assert result['engine']['version']==ENGINE_VERSION and result['artifacts']
    assert path.read_bytes()==original and sorted(p.name for p in tmp_path.iterdir())==['Manifest.db','apple-backup-manifest-sqlite.json','sqlite-schema-catalog.json']

@pytest.mark.parametrize('format,platform,expected',[
    ('apple-backup-manifest-sqlite','ios',2),('sqlite-schema-catalog','ios',1),('sqlite-schema-catalog','android',1)])
def test_real_isolated_sqlite_worker_permissions_custody_and_versions(client,admin_headers,format,platform,expected):
    from test_native_mobile_workflow import setup,enqueue,database_factory,native_review
    from test_case_access import analyst,grant
    from operia.forensic_jobs import worker
    original=image()
    root,acquisition,_=setup(client,admin_headers,platform=platform,filename='Manifest.db',format=format,raw=original)
    job=enqueue(client,admin_headers,root,acquisition)
    assert worker.run_once(database_factory(),timeout=15)
    path=root+f"/jobs/{job['id']}"
    detail=client.get(path,headers=admin_headers).json()
    assert detail['job']['state']=='completado_con_limitaciones',detail
    assert len(detail['result']['artifacts'])==expected
    reviewed=client.post(path+'/reviews',headers=admin_headers,json=native_review([a['id'] for a in detail['result']['artifacts']]))
    assert reviewed.status_code==200,reviewed.text
    link=client.post(path+f"/integrations?review_id={reviewed.json()['id']}",headers=admin_headers)
    assert link.status_code==200,link.text
    report_path=f"/api/reports/{link.json()['report_id']}"
    preserved=client.get(report_path,headers=admin_headers).json()['markdown_content']
    assert sha256(original) in preserved
    assert client.put(report_path,headers=admin_headers,json={'title':'overwrite'}).status_code==409
    uid,headers=analyst(client,admin_headers)
    assert client.get(path,headers=headers).status_code==404
    grant(client,admin_headers,acquisition['case_id'],uid,permissions=['read'])
    assert client.get(path,headers=headers).status_code==200
    grant(client,admin_headers,acquisition['case_id'],uid,'revoked')
    assert client.get(path,headers=headers).status_code==404
    assert client.get(root+f"/acquisitions/{acquisition['id']}/original",headers=admin_headers).content==original
    assert client.get(report_path,headers=admin_headers).json()['markdown_content']==preserved
