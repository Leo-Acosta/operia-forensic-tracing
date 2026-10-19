from pathlib import Path
import sqlite3
import pytest
from pydantic import SecretStr

from operia.core.config import Settings, settings
from operia.identity import security
from operia.security.private_files import protect, assert_private, read_key
from operia.security import production, recovery_bundle as bundle


def test_private_file_real_acl_and_key_size(tmp_path):
    path=tmp_path/'key'; path.write_bytes(b'K'*32); protect(path)
    assert_private(path); assert read_key(path)==b'K'*32
    path.write_bytes(b'bad')
    with pytest.raises(RuntimeError,match='invalid'): read_key(path)


def test_explicit_key_conflict_reload_and_legacy_signature(tmp_path,monkeypatch):
    path=tmp_path/'key'; path.write_bytes(b'K'*32); protect(path)
    monkeypatch.setattr(settings,'auth_signing_key_file',path)
    monkeypatch.setattr(settings,'auth_signing_key',None)
    token,_=security.create_access_token(1,1,'admin')
    assert security.verify_access_token(token)
    path.write_bytes(b'L'*32)
    assert security.verify_access_token(token) is None
    monkeypatch.setattr(settings,'auth_signing_key',SecretStr('X'*32))
    with pytest.raises(RuntimeError,match='conflict'): security._secret()


def production_config(path):
    protect(path.parent)
    return Settings(_env_file=None,env='production',auth_signing_key_file=path,
                    cors_origins=['https://operia.example.invalid'],local_recovery_enabled=False)


def test_production_guard_denies_privileged_inline_missing_and_recovery(tmp_path,monkeypatch):
    path=tmp_path/'key'; path.write_bytes(b'K'*32); protect(path)
    config=production_config(path)
    monkeypatch.setattr(production,'token_info',lambda:{'sid':'synthetic','elevated':False,'system':False})
    assert production.findings(config)==[]
    production.enforce_production(config)
    monkeypatch.setattr(production,'token_info',lambda:{'sid':'synthetic','elevated':True,'system':False})
    with pytest.raises(RuntimeError,match='privileged'): production.enforce_production(config)
    config.local_recovery_enabled=True; config.auth_signing_key=SecretStr('X'*32)
    issues=production.findings(config)
    assert 'production_recovery_must_be_disabled' in issues and 'inline_signing_key_not_allowed' in issues
    config.auth_signing_key_file=None
    assert 'production_secret_file_required' in production.findings(config)
    config.env='prodution'
    with pytest.raises(RuntimeError,match='environment_unknown'): production.enforce_production(config)


def tree(tmp_path):
    root=tmp_path/'project'; root.mkdir()
    storage=root/'storage'
    for name in bundle.DATA_DIRS: (storage/name).mkdir(parents=True)
    (root/'memory_vault').mkdir()
    (root/'memory_vault'/'note.md').write_bytes(b'case-memory-private')
    (storage/'evidence'/'one.bin').write_bytes(b'CASE-EVIDENCE-SECRET')
    (root/'.env').write_bytes(b'OPERIA_TEST_SECRET=CONFIG-PRIVATE')
    key=storage/'.auth-signing-key'; key.write_bytes(b'K'*32); protect(key)
    db=storage/'operia.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE history(value TEXT)')
        con.execute("INSERT INTO history VALUES('ROW-PRIVATE')")
    private=tmp_path/'private'; private.mkdir(); protect(private)
    return root,storage,db,key,private/'data.opb'


def test_real_encrypted_bundle_restore_sqlite_files_secrets_and_no_overwrite(tmp_path):
    root,storage,db,key,dest=tree(tmp_path)
    before={p: p.read_bytes() for p in (db,key,storage/'evidence'/'one.bin',root/'.env')}
    with pytest.raises(RuntimeError,match='stopped_writers'): bundle.create(root,storage,db,dest,key)
    result=bundle.create(root,storage,db,dest,key,quiesced=True)
    assert result['encrypted'] and result['database_integrity']=='ok'
    assert all(marker not in dest.read_bytes() for marker in (b'CASE-EVIDENCE-SECRET',b'CONFIG-PRIVATE',b'ROW-PRIVATE',b'K'*32))
    restored=tmp_path/'restored'
    assert bundle.restore(dest,restored)['restored_to_new_tree']
    assert (restored/'storage/evidence/one.bin').read_bytes()==b'CASE-EVIDENCE-SECRET'
    assert read_key(restored/'secrets/auth-signing-key')==b'K'*32
    with sqlite3.connect(restored/'database.sqlite3') as con:
        assert con.execute('SELECT value FROM history').fetchall()==[('ROW-PRIVATE',)]
    assert all(p.read_bytes()==data for p,data in before.items())
    with pytest.raises(RuntimeError,match='destination_exists'): bundle.create(root,storage,db,dest,key,quiesced=True)
    with pytest.raises(RuntimeError,match='destination_exists'): bundle.restore(dest,restored)
    damaged=dest.parent/'damaged.opb'; damaged.write_bytes(dest.read_bytes()[:-12]+b'bad-tamper!!'); protect(damaged)
    with pytest.raises(Exception): bundle.restore(damaged,tmp_path/'must-not-exist')
    assert not (tmp_path/'must-not-exist').exists()


@pytest.mark.parametrize('name',['../escape','/absolute','C:/drive','storage/a:stream','storage/CON','storage/a/../b','storage/a//b','storage/a.','storage/a\\b'])
def test_restore_names_reject_traversal_alias_and_devices(name):
    with pytest.raises(RuntimeError): bundle.safe_name(name)


def test_key_hardlinks_and_public_acl_rejected(tmp_path):
    import os, subprocess
    path=tmp_path/'private-key'; path.write_bytes(b'K'*32); protect(path)
    alias=tmp_path/'alias'; os.link(path,alias)
    with pytest.raises(RuntimeError,match='link_rejected'): read_key(path)
    alias.unlink()
    subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/icacls.exe'),str(path),'/grant','*S-1-1-0:R'],check=True,capture_output=True)
    with pytest.raises(RuntimeError,match='private_acl_required'): read_key(path)
    protect(path)
    assert read_key(path)==b'K'*32


def test_production_api_rejects_before_schema_or_key_creation(monkeypatch):
    import apps.api.main as main
    from fastapi.testclient import TestClient
    called=[]
    monkeypatch.setattr(settings,'env','production')
    monkeypatch.setattr(settings,'auth_signing_key_file',None)
    monkeypatch.setattr(main,'init_platform_schema',lambda:called.append('schema'))
    with pytest.raises(RuntimeError,match='production_policy_rejected'):
        with TestClient(main.app): pass
    assert called==[]


@pytest.mark.parametrize('mutation',['traversal','case-collision','hash','compression','ancestor'])
def test_encrypted_malformed_bundle_rejected_before_destination(tmp_path,mutation):
    protect(tmp_path)
    import io, zipfile
    from operia.security.dpapi import crypt
    from operia.forensic_engine.canonical import canonical_bytes
    payloads={'database.sqlite3':b'not db','secrets/auth-signing-key':b'K'*32}
    if mutation=='traversal': payloads['storage/../escape']=b'bad'
    if mutation=='case-collision': payloads.update({'storage/a':b'1','storage/A':b'2'})
    if mutation=='ancestor': payloads.update({'storage/a':b'1','storage/a/b':b'2'})
    manifest={'schema':'operia-recovery-bundle/1','encryption':'windows-dpapi-current-user',
              'files':{n:{'sha256':bundle.digest(d),'size_bytes':len(d)} for n,d in payloads.items()}}
    if mutation=='hash': manifest['files']['database.sqlite3']['sha256']='0'*64
    memory=io.BytesIO()
    with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_DEFLATED if mutation=='compression' else zipfile.ZIP_STORED) as archive:
        archive.writestr('manifest.json',canonical_bytes(manifest))
        for n,d in payloads.items(): archive.writestr(n,d)
    source=tmp_path/'bad.opb'; source.write_bytes(bundle.MAGIC+crypt(memory.getvalue())); protect(source)
    target=tmp_path/'absent'
    with pytest.raises(Exception): bundle.restore(source,target)
    assert not target.exists() and not (tmp_path/'escape').exists()


def test_source_mutation_aborts_without_output(tmp_path,monkeypatch):
    root,storage,db,key,dest=tree(tmp_path)
    original=bundle.inventory; calls=0
    def changing(*args):
        nonlocal calls
        calls+=1
        if calls==2: (storage/'evidence'/'one.bin').write_bytes(b'changed')
        return original(*args)
    monkeypatch.setattr(bundle,'inventory',changing)
    with pytest.raises(RuntimeError,match='source_changed'): bundle.create(root,storage,db,dest,key,quiesced=True)
    assert not dest.exists()
