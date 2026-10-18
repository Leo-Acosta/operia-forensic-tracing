import base64
import json
import sqlite3
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from operia.forensic_engine.analysis import analyze
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_engine.contracts import Source
from operia.forensic_engine.wal_readers import checksum, pack_set, reconstruct
from test_manifest_sqlite import SCHEMA


def fixture_set(tmp_path, extra=()):
    path = tmp_path / 'generator.db'
    db = sqlite3.connect(path)
    try:
        db.execute(SCHEMA)
        db.execute('INSERT INTO Files VALUES(?,?,?,?,?)', ('a'*40, 'HomeDomain', 'Library/a', 1, b'PRIVATE-BLOB'))
        db.commit()
        assert db.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        db.execute('INSERT INTO Files VALUES(?,?,?,?,?)', ('b'*40, 'HomeDomain', 'Library/b', 1, b'PRIVATE-BLOB'))
        db.commit()
        db.execute('UPDATE Files SET flags=2 WHERE fileID=?', ('a'*40,))
        db.commit()
        for sql in extra:
            db.execute(sql)
            db.commit()
        assert db.execute('SELECT flags FROM Files ORDER BY fileID').fetchall() == [(2,), (1,)]
        return {role: Path(str(path)+suffix).read_bytes() for role, suffix in [('database',''),('wal','-wal'),('shm','-shm')]}
    finally:
        db.close()


def run(parts, format='apple-backup-manifest-wal-set', platform='ios'):
    return analyze(Source('synthetic','set.json',platform,format,pack_set(**parts)))


def test_native_sqlite_oracle_preserved_components_and_determinism(tmp_path):
    parts = fixture_set(tmp_path)
    original = dict(parts)
    result = run(parts)
    assert len(result['artifacts']) == 3 and not result['timeline']
    assert [a['normalized']['flags'] for a in result['artifacts'][1:]] == [2,1]
    info = result['artifacts'][0]['normalized']
    assert info['commits'] == 2 and info['shm']['status'] == 'cabeceras_contrastadas'
    assert info['last_commit_frame'] == info['frames_checked']
    assert all(info['components'][role]['sha256'] == sha256(raw) for role,raw in parts.items())
    assert result['source_manifest'][0]['sha256'] == sha256(pack_set(**parts))
    assert b'PRIVATE-BLOB' not in canonical_bytes(result)
    assert parts == original and canonical_bytes(run(parts)) == canonical_bytes(result)
    derived, _, _ = reconstruct(parts)
    db = sqlite3.connect(':memory:')
    try:
        db.deserialize(derived)
        assert db.execute('SELECT flags FROM Files ORDER BY fileID').fetchall() == [(2,),(1,)]
        assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
    finally: db.close()


@pytest.mark.parametrize('platform',['ios','android'])
def test_catalog_and_shm_absence_are_explicit(tmp_path,platform):
    parts = fixture_set(tmp_path); parts['shm'] = None
    result = run(parts,'sqlite-wal-catalog-set',platform)
    assert len(result['artifacts']) == 2
    assert result['artifacts'][0]['normalized']['shm']['status'] == 'no_aportado'
    assert result['artifacts'][1]['normalized']['name'] == 'Files'


def append_uncommitted(parts):
    result = dict(parts); wal = parts['wal']
    size = int.from_bytes(wal[8:12],'big'); offset = len(wal) - size - 24
    order = '>' if wal[3] & 1 else '<'
    header = wal[offset:offset+4] + b'\0'*4 + wal[16:24]
    page = wal[-size:]
    state = checksum(page,order,checksum(header[:8],order,struct.unpack_from('>II',wal,offset+16)))
    result['wal'] = wal + header + struct.pack('>II',*state) + page
    return result


def test_uncommitted_tail_excluded_and_corrupt_tail_rejected(tmp_path):
    parts = append_uncommitted(fixture_set(tmp_path))
    result = run(parts)
    assert len(result['artifacts']) == 3
    assert len(result['coverage']['sources'][0]['excluded']) == 1
    parts['wal'] = parts['wal'][:-1] + bytes([parts['wal'][-1] ^ 1])
    assert not run(parts)['artifacts']


@pytest.mark.parametrize('component,offset',[
    ('database',18),('database',16),('wal',0),('wal',4),('wal',8),('wal',24),
    ('wal',32),('wal',40),('wal',48),('wal',56),('shm',0),('shm',48),('shm',16),('shm',32),('shm',40)])
def test_corruption_or_mismatch_fails_without_partial_output(tmp_path,component,offset):
    parts = fixture_set(tmp_path)
    raw = bytearray(parts[component]); raw[offset] ^= 1; parts[component] = bytes(raw)
    result = run(parts)
    assert not result['artifacts']
    assert result['coverage']['sources'][0]['status'] in ('no_compatible','corrupto')


@pytest.mark.parametrize('component,mode',[('wal','empty'),('wal','truncated'),('shm','empty'),('shm','truncated'),('wal','no_commit')])
def test_missing_truncated_and_no_commit_inputs(tmp_path,component,mode):
    parts = fixture_set(tmp_path)
    if mode == 'no_commit':
        wal = parts['wal']; size = int.from_bytes(wal[8:12],'big'); order = '>' if wal[3]&1 else '<'
        state = struct.unpack_from('>II',wal,24); out = bytearray(wal[:32])
        for offset in range(32,len(wal),24+size):
            head = wal[offset:offset+4] + b'\0'*4 + wal[offset+8:offset+16]; page = wal[offset+24:offset+24+size]
            state = checksum(page,order,checksum(head[:8],order,state))
            out.extend(head + struct.pack('>II',*state) + page)
        parts['wal'] = bytes(out); parts['shm'] = None
    else: parts[component] = b'' if mode == 'empty' else parts[component][:-1]
    assert not run(parts)['artifacts']


def test_checksums_endianness_and_independent_native_replay(tmp_path):
    assert checksum(struct.pack('<IIII',1,2,3,4),'<') == (7,14)
    assert checksum(struct.pack('>IIII',1,2,3,4),'>') == (7,14)
    parts = fixture_set(tmp_path); wal = parts['wal']; size = int.from_bytes(wal[8:12],'big')
    header = b'\x37\x7f\x06\x83' + wal[4:24]; state = checksum(header,'>')
    out = bytearray(header + struct.pack('>II',*state))
    for offset in range(32,len(wal),24+size):
        head = wal[offset:offset+16]; page = wal[offset+24:offset+24+size]
        state = checksum(page,'>',checksum(head[:8],'>',state))
        out.extend(head + struct.pack('>II',*state) + page)
    parts['wal'] = bytes(out); parts['shm'] = None
    oracle = tmp_path/'oracle.db'; oracle.write_bytes(parts['database'])
    Path(str(oracle)+'-wal').write_bytes(parts['wal'])
    db = sqlite3.connect(oracle)
    try: assert db.execute('SELECT flags FROM Files ORDER BY fileID').fetchall() == [(2,),(1,)]
    finally: db.close()
    assert [a['normalized']['flags'] for a in run(parts)['artifacts'][1:]] == [2,1]


def test_contract_hashes_limits_and_active_schema(tmp_path,monkeypatch):
    parts = fixture_set(tmp_path)
    bad = json.loads(pack_set(**parts)); bad['wal']['sha256'] = '0'*64
    assert not analyze(Source('x','set.json','ios','apple-backup-manifest-wal-set',canonical_bytes(bad)))['artifacts']
    bad['extra_path'] = '../../secret'
    assert not analyze(Source('x','set.json','ios','apple-backup-manifest-wal-set',canonical_bytes(bad)))['artifacts']
    from operia.forensic_engine import wal_readers
    monkeypatch.setattr(wal_readers,'MAX_FRAMES',1)
    assert not run(parts)['artifacts']


@pytest.mark.parametrize('extra',[
    ('CREATE VIEW active AS SELECT * FROM Files',),
    ('CREATE TRIGGER active AFTER INSERT ON Files BEGIN DELETE FROM Files; END',)])
def test_active_schema_in_committed_wal_is_rejected(tmp_path,extra):
    result = run(fixture_set(tmp_path,extra))
    assert not result['artifacts'] and result['coverage']['sources'][0]['status'] == 'no_compatible'


@pytest.mark.parametrize('shrink',[False,True])
def test_native_growth_and_truncation_commit_sizes(tmp_path,shrink):
    extra = ('CREATE TABLE Extra(payload BLOB)','INSERT INTO Extra VALUES(zeroblob(100000))')
    if shrink: extra += ('DROP TABLE Extra','VACUUM')
    parts = fixture_set(tmp_path,extra)
    result = run(parts)
    assert len(result['artifacts']) == 3
    derived,details,_ = reconstruct(parts)
    assert len(derived) == details['database_pages'] * details['page_size']
    assert len(derived) == len(parts['database']) if shrink else len(derived) > len(parts['database'])


def test_shm_big_endian_header_and_uninterpreted_cache(tmp_path):
    parts = fixture_set(tmp_path); raw = parts['shm']
    old = '<' if raw[:4] == struct.pack('<I',3007000) else '>'
    new = '>' if old == '<' else '<'
    head = bytearray(raw[:40])
    for offset in (0,4,8,16,20,24,28):
        head[offset:offset+4] = struct.pack(new+'I',struct.unpack_from(old+'I',raw,offset)[0])
    head[14:16] = struct.pack(new+'H',struct.unpack_from(old+'H',raw,14)[0])
    head.extend(struct.pack(new+'II',*checksum(head,new)))
    changed = bytearray(raw); changed[:48] = head; changed[48:96] = head
    for offset in (96,128):
        changed[offset:offset+4] = struct.pack(new+'I',struct.unpack_from(old+'I',raw,offset)[0])
    changed[200] ^= 1  # Cache table is preserved, deliberately not trusted or interpreted.
    parts['shm'] = bytes(changed)
    result = run(parts)
    assert len(result['artifacts']) == 3
    assert result['artifacts'][0]['normalized']['shm']['byte_order'] == ('big' if new == '>' else 'little')


def test_packaging_cli_never_changes_preserved_files(tmp_path):
    parts = fixture_set(tmp_path)
    paths = {role:tmp_path/(role+'.bin') for role in parts}
    for role,path in paths.items(): path.write_bytes(parts[role])
    package = tmp_path/'set.json'; result_path = tmp_path/'result.json'
    command = [sys.executable,'-S','scripts/preserve_sqlite_set.py']
    for role,path in paths.items(): command += ['--'+role,str(path)]
    subprocess.run(command+['--output',str(package)],check=True,capture_output=True,timeout=15)
    assert package.read_bytes() == pack_set(**parts)
    subprocess.run([sys.executable,'-S','-m','operia.forensic_engine',str(package),'--platform','ios',
                    '--format','apple-backup-manifest-wal-set','--output',str(result_path)],check=True,capture_output=True,timeout=15)
    assert len(json.loads(result_path.read_bytes())['artifacts']) == 3
    assert all(path.read_bytes() == parts[role] for role,path in paths.items())
    assert subprocess.run(command+['--output',str(package)],capture_output=True).returncode != 0


@pytest.mark.parametrize('format,platform,expected',[
    ('apple-backup-manifest-wal-set','ios',3),('sqlite-wal-catalog-set','ios',2),('sqlite-wal-catalog-set','android',2)])
def test_real_wal_worker_scope_review_and_historical_reports(tmp_path,client,admin_headers,format,platform,expected):
    from test_native_mobile_workflow import setup,enqueue,database_factory,native_review
    from test_case_access import analyst,grant
    from test_security_audit import second_tenant
    from operia.forensic_jobs import worker
    parts = fixture_set(tmp_path); raw = pack_set(**parts)
    root,acquisition,_ = setup(client,admin_headers,platform=platform,filename='set.json',format=format,raw=raw)
    job = enqueue(client,admin_headers,root,acquisition)
    assert worker.run_once(database_factory(),timeout=15)
    path = root+f"/jobs/{job['id']}"; detail = client.get(path,headers=admin_headers).json()
    assert detail['job']['state'] == 'completado_con_limitaciones',detail
    assert len(detail['result']['artifacts']) == expected
    ids = [a['id'] for a in detail['result']['artifacts']]
    review = client.post(path+'/reviews',headers=admin_headers,json=native_review(ids)).json()
    export = client.post(path+'/exports',headers=admin_headers,json={'format':'json'}).json()
    exported = client.get(path+f"/exports/{export['id']}",headers=admin_headers).content
    integration = client.post(path+f"/integrations?review_id={review['id']}",headers=admin_headers)
    assert integration.status_code == 200,integration.text
    report_path = f"/api/reports/{integration.json()['report_id']}"
    report = client.get(report_path,headers=admin_headers).json()
    assert client.put(report_path,headers=admin_headers,json={'title':'overwrite'}).status_code == 409
    assert client.post(path+'/reviews',headers=admin_headers,json=native_review(ids,rationale='Revisión posterior sintética')).status_code == 200
    assert client.get(path+f"/exports/{export['id']}",headers=admin_headers).content == exported
    assert client.get(report_path,headers=admin_headers).json() == report
    uid,headers = analyst(client,admin_headers)
    assert client.get(path,headers=headers).status_code == 404
    grant(client,admin_headers,acquisition['case_id'],uid,permissions=['read'])
    assert client.get(path,headers=headers).status_code == 200
    assert client.post(path+'/reviews',headers=headers,json=native_review(ids)).status_code == 404
    assert len(client.get(path,headers=admin_headers).json()['reviews']) == 2
    grant(client,admin_headers,acquisition['case_id'],uid,'revoked')
    assert client.get(path,headers=headers).status_code == 404
    _,_,foreign = second_tenant(client)
    assert client.get(path,headers=foreign).status_code == 404
    assert client.get(root+f"/acquisitions/{acquisition['id']}/original",headers=admin_headers).content == raw
