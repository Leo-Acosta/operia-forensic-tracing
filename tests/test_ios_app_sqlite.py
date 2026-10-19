import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from operia.forensic_engine.analysis import analyze, capabilities
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_engine.contracts import Source
from operia.forensic_engine.ios_app_sqlite import authorize_safari
from operia.forensic_engine.sqlite_readers import preserved_copy

FORMAT = 'ios-safari-history-sqlite'
SCHEMA = ('CREATE TABLE history_items(id INTEGER PRIMARY KEY,url TEXT,private_blob BLOB)',
          'CREATE TABLE history_visits(id INTEGER PRIMARY KEY,history_item INTEGER,visit_time REAL,title TEXT,origin INTEGER)')
ITEMS = [(1, 'https://benign.invalid/a', b'BLOB-SECRET'), (2, 'https://benign.invalid/unreferenced', b'BLOB-SECRET')]
VISITS = [(10, 1, 42.5, 'Benign <script>text</script>', 1), (11, 1, None, None, 0), (12, 99, 43.0, 'ORPHAN-TITLE-SECRET', 1)]


def image(items=ITEMS, visits=VISITS, schema=SCHEMA, extra=()):
    db = sqlite3.connect(':memory:')
    try:
        for sql in schema:
            db.execute(sql)
        if items:
            db.executemany('INSERT INTO history_items VALUES(?,?,?)', items)
        if visits:
            db.executemany('INSERT INTO history_visits VALUES(?,?,?,?,?)', visits)
        for sql in extra:
            db.execute(sql)
        db.commit()
        return db.serialize()
    finally:
        db.close()


def source(raw):
    return Source('synthetic', 'History.db', 'ios', FORMAT, raw)


def test_safari_oracle_no_epoch_guess_no_secret_columns_and_preserved_file(tmp_path):
    raw = image(extra=('CREATE TABLE private(secret TEXT)', "INSERT INTO private VALUES('OTHER-TABLE-SECRET')"))
    path = tmp_path / 'History.db'; path.write_bytes(raw)
    result = analyze(source(path.read_bytes()))
    assert len(result['artifacts']) == 2 and not result['timeline'] and not result['alerts']
    assert [a['locator'] for a in result['artifacts']] == ['history_visits/id:10', 'history_visits/id:11']
    assert result['artifacts'][0]['normalized'] == {
        'visit_id': 10, 'history_item_id': 1, 'stored_url': 'https://benign.invalid/a',
        'stored_title': 'Benign <script>text</script>', 'stored_visit_time': 42.5, 'stored_visit_time_type': 'float'}
    assert result['artifacts'][1]['normalized']['stored_visit_time_type'] == 'null'
    assert result['source_manifest'][0]['sha256'] == sha256(raw)
    assert all(a['duplicate_of'] is None for a in result['artifacts'])
    for secret in (b'BLOB-SECRET', b'OTHER-TABLE-SECRET', b'ORPHAN-TITLE-SECRET', b'https://benign.invalid/unreferenced'):
        assert secret not in canonical_bytes(result)
    exclusions = result['coverage']['sources'][0]['excluded']
    assert len(exclusions) == 5
    assert path.read_bytes() == raw and not list(tmp_path.glob('History.db-*'))
    assert canonical_bytes(result) == canonical_bytes(analyze(source(raw)))
    assert any(r['format'] == FORMAT for r in capabilities()['readers'])


@pytest.mark.parametrize('sql', [
    'UPDATE history_visits SET title="x"', 'DELETE FROM history_items', 'DROP TABLE history_items',
    "ATTACH DATABASE 'bad.db' AS x", 'PRAGMA writable_schema=ON', 'PRAGMA query_only=OFF',
    'SELECT private_blob FROM history_items', 'SELECT origin FROM history_visits',
    'SELECT secret FROM private', 'SELECT randomblob(1)', "SELECT load_extension('bad')", 'VACUUM',
])
def test_safari_authorizer_denies_writes_functions_attach_and_unselected_columns(sql):
    raw = image(extra=('CREATE TABLE private(secret TEXT)',))
    with preserved_copy(raw, authorizer=authorize_safari) as db:
        with pytest.raises(sqlite3.DatabaseError):
            db.execute(sql).fetchall()
        assert [r[0] for r in db.execute('SELECT id,url FROM history_items ORDER BY id').fetchall()] == [1, 2]
    # The existing catalog/Manifest connection does not gain Safari row permissions.
    with preserved_copy(raw) as db:
        with pytest.raises(sqlite3.DatabaseError):
            db.execute('SELECT url FROM history_items').fetchall()


@pytest.mark.parametrize('extra', [
    ('CREATE VIEW active AS SELECT * FROM history_items',),
    ('CREATE TRIGGER active AFTER INSERT ON history_items BEGIN DELETE FROM history_visits; END',),
    ('CREATE VIRTUAL TABLE active USING fts5(data)',),
    ('CREATE INDEX active ON history_items(length(url))',),
    ('CREATE INDEX active ON history_items(url) WHERE id>1',),
])
def test_safari_active_schema_rejected_without_partial_records(extra):
    result = analyze(source(image(extra=extra)))
    assert not result['artifacts']
    assert result['coverage']['sources'][0]['status'] == 'no_compatible'
    assert result['coverage']['sources'][0]['excluded'][0]['locator'] == 'database'


@pytest.mark.parametrize('mode', ['missing', 'wrong_type', 'composite_key', 'hidden', 'wal', 'truncated', 'encrypted', 'negative_id'])
def test_safari_unsupported_images_or_schema_reject_all_records(mode):
    schema = list(SCHEMA)
    if mode == 'missing': schema = schema[:1]
    if mode == 'wrong_type': schema[0] = schema[0].replace('url TEXT', 'url BLOB')
    if mode == 'composite_key': schema[1] = 'CREATE TABLE history_visits(id INTEGER,history_item INTEGER,visit_time REAL,title TEXT,origin INTEGER,PRIMARY KEY(id,history_item))'
    if mode == 'hidden': schema[1] = schema[1].replace('origin INTEGER', 'origin INTEGER AS (id+1)')
    if mode in ('missing', 'wrong_type', 'composite_key', 'hidden'):
        raw = image(items=(), visits=(), schema=schema)
    elif mode == 'negative_id': raw = image(visits=[(-1, 1, 42, 'bad', 0)])
    else:
        raw = image()
        if mode == 'wal': raw = raw[:18] + b'\x02\x02' + raw[20:]
        if mode == 'truncated': raw = raw[:-1]
        if mode == 'encrypted': raw = b'encrypted-looking synthetic image'
    result = analyze(source(raw))
    assert not result['artifacts'] and not result['timeline']
    assert result['coverage']['sources'][0]['excluded']


@pytest.mark.parametrize('which', ['items', 'visits'])
def test_safari_500_rows_boundary_and_overflow_has_no_prefix(which):
    kwargs = {'items': [(i, 'https://benign.invalid', b'private') for i in range(1, 501)],
              'visits': [(i, 1, float(i), 'same', 0) for i in range(1, 501)]}
    assert len(analyze(source(image(**kwargs)))['artifacts']) == 500
    if which == 'items': kwargs[which].append((501, 'https://benign.invalid', b'private'))
    else: kwargs[which].append((501, 1, 501.0, 'same', 0))
    assert not analyze(source(image(**kwargs)))['artifacts']


@pytest.mark.parametrize('value', [b'BLOB-PRIVATE', 'x' * 2049, 'bad\0control', float('inf')],
                         ids=['blob','length','control','infinite'])
def test_safari_bad_row_values_are_local_exclusions(value):
    result = analyze(source(image(visits=[(10, 1, value if isinstance(value, float) else 42.0,
                                          'safe' if isinstance(value, float) else value, 0),
                                         (11, 1, None, 'valid', 0)])))
    assert [a['normalized']['visit_id'] for a in result['artifacts']] == [11]
    assert any(e['locator'] == 'history_visits/id:10' for e in result['coverage']['sources'][0]['excluded'])


def test_safari_empty_tables_and_equal_values_keep_visit_ids():
    result = analyze(source(image(items=(), visits=(), schema=(SCHEMA[0].replace(',private_blob BLOB', ''), SCHEMA[1].replace(',origin INTEGER', '')))))
    assert not result['artifacts'] and result['coverage']['sources'][0]['status'] == 'sin_registros'
    result = analyze(source(image(visits=[(10, 1, 42, 'equal', 0), (11, 1, 42, 'equal', 0)])))
    assert len(result['artifacts']) == 2 and all(a['duplicate_of'] is None for a in result['artifacts'])


def test_safari_cli_on_explicit_copy_without_sidecars(tmp_path):
    path = tmp_path / 'History.db'; raw = image(); path.write_bytes(raw)
    (tmp_path / 'History.db-wal').write_bytes(b'WAL-DECOY-PRIVATE')
    output = tmp_path / 'result.json'
    command = [sys.executable, '-S', '-m', 'operia.forensic_engine', str(path), '--platform', 'ios', '--format', FORMAT, '--output', str(output)]
    subprocess.run(command, check=True, capture_output=True, timeout=15)
    result = json.loads(output.read_bytes())
    assert len(result['artifacts']) == 2 and b'WAL-DECOY-PRIVATE' not in output.read_bytes()
    assert path.read_bytes() == raw
    assert subprocess.run(command, capture_output=True).returncode != 0


def test_safari_real_worker_case_permissions_custody_and_history(client, admin_headers):
    from test_native_mobile_workflow import setup, enqueue, database_factory, native_review
    from test_case_access import analyst, grant
    from test_security_audit import second_tenant
    from operia.forensic_jobs import worker
    from operia.evidence.models import CustodyLedgerEntry
    raw = image()
    root, acquisition, _ = setup(client, admin_headers, platform='ios', filename='History.db', format=FORMAT, raw=raw)
    job = enqueue(client, admin_headers, root, acquisition)
    assert worker.run_once(database_factory(), timeout=15)
    path = root + f"/jobs/{job['id']}"
    detail = client.get(path, headers=admin_headers).json()
    assert detail['job']['state'] == 'completado_con_limitaciones', detail
    assert len(detail['result']['artifacts']) == 2 and not detail['result']['timeline']
    ids = [a['id'] for a in detail['result']['artifacts']]
    review_response = client.post(path + '/reviews', headers=admin_headers, json=native_review(ids))
    assert review_response.status_code == 200, review_response.text
    exported = client.post(path + '/exports', headers=admin_headers, json={'format': 'json'}).json()
    export_url = path + f"/exports/{exported['id']}"
    original_export = client.get(export_url, headers=admin_headers).content
    integration = client.post(path + f"/integrations?review_id={review_response.json()['id']}", headers=admin_headers)
    assert integration.status_code == 200, integration.text
    link = integration.json()
    with database_factory()() as db:
        ledger = db.query(CustodyLedgerEntry).filter_by(action_id=link['custody_id']).one()
        assert ledger.actor_user_id == 1 and ledger.version == 0
    evidence_url = f"/api/evidence/{link['evidence_id']}"
    assert client.get(evidence_url + '/download', headers=admin_headers).content == raw
    assert client.get(evidence_url + '/integrity', headers=admin_headers).json()['ok']
    report_url = f"/api/reports/{link['report_id']}"
    original_report = client.get(report_url, headers=admin_headers).json()
    assert client.put(report_url, headers=admin_headers, json={'title': 'overwrite'}).status_code == 409
    assert client.post(path + '/reviews', headers=admin_headers,
                       json=native_review(ids, rationale='Segunda revisión sintética')).status_code == 200
    assert client.get(report_url, headers=admin_headers).json() == original_report
    assert client.get(export_url, headers=admin_headers).content == original_export
    uid, reader = analyst(client, admin_headers)
    assert client.get(path, headers=reader).status_code == 404
    grant(client, admin_headers, acquisition['case_id'], uid, permissions=['read'])
    assert client.get(path, headers=reader).status_code == 200
    assert client.post(path + '/reviews', headers=reader, json=native_review(ids)).status_code == 404
    assert len(client.get(path, headers=admin_headers).json()['reviews']) == 2
    another = client.post('/api/cases', headers=admin_headers, json={'case_code': 'SAFARI-OTHER', 'title': 'Otro expediente'}).json()
    foreign_case_path = f"/api/mobile-forensics/native/cases/{another['id']}/jobs/{job['id']}"
    assert client.get(foreign_case_path, headers=admin_headers).status_code == 404
    grant(client, admin_headers, acquisition['case_id'], uid, 'revoked')
    assert client.get(path, headers=reader).status_code == 404
    _, _, foreign = second_tenant(client)
    assert client.get(path, headers=foreign).status_code == 404
    original_url = root + f"/acquisitions/{acquisition['id']}/original"
    assert client.get(original_url, headers=foreign).status_code == 404
    assert client.get(original_url, headers=admin_headers).content == raw


@pytest.mark.parametrize('url', [None, b'PRIVATE-URL-BLOB', '', 'x' * 2049, 'bad\x1burl'],
                         ids=['null','blob','empty','long','control'])
def test_safari_invalid_item_excludes_its_visit_without_publishing_url(url):
    result = analyze(source(image(items=[(1, url, b'private')], visits=[(1, 1, 0, 'TITLE-SECRET', 0)])))
    assert not result['artifacts']
    assert b'TITLE-SECRET' not in canonical_bytes(result)
    locators = {e['locator'] for e in result['coverage']['sources'][0]['excluded']}
    assert {'history_items/id:1', 'history_visits/id:1'} <= locators


def test_safari_vm_budget_failure_does_not_publish_a_prefix(monkeypatch):
    import operia.forensic_engine.sqlite_readers as sqlite_readers
    monkeypatch.setattr(sqlite_readers, 'MAX_VM_STEPS', 0)
    raw = image(visits=[(i, 1, 42, 'valid', 0) for i in range(1, 501)])
    result = analyze(source(raw))
    assert not result['artifacts'] and result['coverage']['sources'][0]['status'] == 'corrupto'


def test_existing_catalog_format_does_not_start_reading_safari_rows():
    result = analyze(Source('synthetic', 'History.db', 'ios', 'sqlite-schema-catalog', image()))
    assert all(a['kind'] == 'sqlite_schema_metadata' for a in result['artifacts'])
    assert b'https://benign.invalid/a' not in canonical_bytes(result)
