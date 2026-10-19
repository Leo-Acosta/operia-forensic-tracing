"""Offline scoped recovery bundle. Never restore into an existing tree or execute files."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing

from operia.security.private_files import no_links, protect, assert_private, read_key
from operia.security.dpapi import crypt
from operia.forensic_engine.canonical import read_json, canonical_bytes

MAGIC = b'OPERIA-DPAPI-BACKUP/1\n'
MAX_BYTES = 128 * 1024 * 1024
MAX_FILES = 5000
MAX_FILE_BYTES = 32 * 1024 * 1024
DATA_DIRS = ('evidence','uploads','exports','maps')


def digest(data): return hashlib.sha256(data).hexdigest()


def bounded_read(path, limit=MAX_FILE_BYTES):
    with path.open('rb') as stream: raw=stream.read(limit+1)
    if len(raw)>limit: raise RuntimeError('backup_file_limit')
    return raw


def regular(path, limit=MAX_FILE_BYTES):
    path = no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1: raise RuntimeError('backup_regular_single_link_required')
    if info.st_size > limit: raise RuntimeError('backup_file_limit')
    return path


def private_directory(path):
    path = no_links(path)
    if path.exists(): assert_private(path)
    else:
        path.mkdir(parents=True,exist_ok=False); protect(path)
    return path


def inventory(project, storage, secret):
    files = {}
    for name in DATA_DIRS:
        directory = no_links(storage/name)
        if directory.exists():
            for file in directory.rglob('*'):
                no_links(file)
                if file.is_file(): files['storage/'+name+'/'+file.relative_to(directory).as_posix()] = regular(file)
    vault = no_links(project/'memory_vault')
    if vault.exists():
        for file in vault.rglob('*'):
            no_links(file)
            if file.is_file(): files['memory_vault/'+file.relative_to(vault).as_posix()] = regular(file)
    for name in ('.env','.auth-signing-key'):
        if (project/name).exists(): files['config/'+name] = regular(project/name)
    # Include the effective signing-key file, not process environment or an assumed key.
    read_key(secret)
    files['secrets/auth-signing-key'] = regular(secret)
    fallback = storage/'.auth-signing-key'
    if fallback.exists(): files['storage/.auth-signing-key'] = regular(fallback)
    if len(files)+1 > MAX_FILES: raise RuntimeError('backup_file_count_limit')
    if sum(p.stat().st_size for p in files.values()) > MAX_BYTES: raise RuntimeError('backup_total_limit')
    return files


def create(project, storage, database, destination, secret, *, quiesced=False):
    if not quiesced: raise RuntimeError('backup_requires_stopped_writers_acknowledgement')
    project, storage, database, secret, destination = map(no_links,(project,storage,database,secret,destination))
    if destination.exists(): raise RuntimeError('backup_destination_exists')
    for directory in [storage/name for name in DATA_DIRS]+[project/'memory_vault']:
        if destination.is_relative_to(directory): raise RuntimeError('backup_destination_inside_data')
    regular(database)
    parent = private_directory(destination.parent)
    sources = inventory(project,storage,secret)
    before = {name:digest(bounded_read(path)) for name,path in sources.items()}
    with tempfile.TemporaryDirectory(prefix='operia-backup-',dir=parent) as scratch_name:
        scratch = Path(scratch_name).resolve()
        assert scratch.is_relative_to(parent.resolve())
        protect(scratch)
        copy = scratch/'database.sqlite3'
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(copy)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]: raise RuntimeError('backup_database_integrity')
        regular(copy)
        payloads={'database.sqlite3':bounded_read(copy)}
        for name,path in sources.items():
            raw=bounded_read(path)
            if digest(raw)!=before[name]: raise RuntimeError('backup_source_changed')
            payloads[name]=raw
        after_sources=inventory(project,storage,secret)
        if set(after_sources)!=set(sources) or any(digest(bounded_read(p))!=before[n] for n,p in after_sources.items()):
            raise RuntimeError('backup_source_changed')
        # A second SQLite snapshot detects persisted concurrent database changes.
        check_path=scratch/'check.sqlite3'
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(check_path)) as check:
            src.backup(check)
        if digest(bounded_read(check_path))!=digest(payloads['database.sqlite3']): raise RuntimeError('backup_database_changed')
        if sum(map(len,payloads.values())) > MAX_BYTES: raise RuntimeError('backup_total_limit')
        manifest={'schema':'operia-recovery-bundle/1','encryption':'windows-dpapi-current-user',
                  'scope':'SQLite + evidence/uploads/exports/maps + memory_vault + project config + explicit signing key; no runtimes/models/external references',
                  'writers_stopped_acknowledged':True,
                  'files':{name:{'sha256':digest(raw),'size_bytes':len(raw)} for name,raw in sorted(payloads.items())}}
        memory=io.BytesIO()
        with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('manifest.json',canonical_bytes(manifest))
            for name,raw in sorted(payloads.items()): archive.writestr(name,raw)
        if memory.tell() > MAX_BYTES: raise RuntimeError('backup_total_limit')
        encrypted=MAGIC+crypt(memory.getvalue())
        if len(encrypted)>MAX_BYTES+1024*1024: raise RuntimeError('backup_total_limit')
        with destination.open('xb') as stream:
            protect(destination)
            stream.write(encrypted); stream.flush()
            import os
            os.fsync(stream.fileno())
    return verify(destination)


def safe_name(name):
    path=PurePosixPath(name)
    reserved={'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
    if (not name or str(path)!=name or path.is_absolute() or '\\' in name or ':' in name or
            any(p in ('.','..') or p.endswith((' ','.')) or p.split('.')[0].upper() in reserved or
                any(ord(c)<32 for c in p) for p in name.split('/')) or
            not (name=='database.sqlite3' or path.parts[0] in ('storage','memory_vault','config','secrets'))):
        raise RuntimeError('backup_entry_name_rejected')
    return name


def unpack(source):
    source=regular(source,MAX_BYTES+1024*1024); assert_private(source)
    if source.stat().st_size > MAX_BYTES+1024*1024: raise RuntimeError('backup_total_limit')
    raw=bounded_read(source,MAX_BYTES+1024*1024)
    if not raw.startswith(MAGIC): raise RuntimeError('backup_format_rejected')
    plain=crypt(raw[len(MAGIC):],decrypt=True)
    if len(plain)>MAX_BYTES: raise RuntimeError('backup_total_limit')
    with zipfile.ZipFile(io.BytesIO(plain)) as archive:
        entries=archive.infolist()
        if len(entries)>MAX_FILES+1 or len({i.filename.casefold() for i in entries})!=len(entries): raise RuntimeError('backup_entries_rejected')
        if sum(i.file_size for i in entries)>MAX_BYTES: raise RuntimeError('backup_total_limit')
        for item in entries:
            if (item.compress_type!=zipfile.ZIP_STORED or item.flag_bits & 1 or item.is_dir() or
                    stat.S_IFMT(item.external_attr >> 16) not in (0,stat.S_IFREG) or item.file_size>MAX_FILE_BYTES):
                raise RuntimeError('backup_entry_type_rejected')
            if item.filename!='manifest.json': safe_name(item.filename)
        manifest=read_json(archive.read('manifest.json'),limit=1024*1024)
        if (not isinstance(manifest,dict) or manifest.get('schema')!='operia-recovery-bundle/1' or
                manifest.get('encryption')!='windows-dpapi-current-user' or not isinstance(manifest.get('files'),dict)):
            raise RuntimeError('backup_manifest_rejected')
        files=manifest['files']
        if set(files)!={i.filename for i in entries}-{'manifest.json'} or not {'database.sqlite3','secrets/auth-signing-key'}<=set(files):
            raise RuntimeError('backup_manifest_rejected')
        if any(parent.as_posix() in files for name in files for parent in PurePosixPath(name).parents):
            raise RuntimeError('backup_entry_collision')
        payloads={}
        for name,info in files.items():
            safe_name(name); data=archive.read(name)
            if info!={'sha256':digest(data),'size_bytes':len(data)}: raise RuntimeError('backup_integrity_failed')
            payloads[name]=data
        if len(payloads['secrets/auth-signing-key'])!=32: raise RuntimeError('backup_secret_invalid')
        return manifest,payloads


def verify(source):
    manifest,payloads=unpack(source)
    parent=Path(source).absolute().parent
    assert_private(parent)  # Plaintext scratch must never be created below a shared directory.
    with tempfile.TemporaryDirectory(prefix='operia-verify-',dir=parent) as name:
        scratch=Path(name).resolve(); assert scratch.is_relative_to(parent.resolve()); protect(scratch)
        database=scratch/'database.sqlite3'; database.write_bytes(payloads['database.sqlite3'])
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]: raise RuntimeError('backup_database_integrity')
    return {'schema':'operia-recovery-verification/1','files_verified':len(payloads),'encrypted':True,
            'encryption':'windows-dpapi-current-user','sha256':digest(Path(source).read_bytes()),'database_integrity':'ok'}


def restore(source,destination):
    # Verify the entire bundle and database before creating any restoration tree.
    result=verify(source); manifest,payloads=unpack(source)
    destination=no_links(destination)
    if destination.exists(): raise RuntimeError('backup_restore_destination_exists')
    destination.mkdir(parents=True,exist_ok=False); protect(destination)
    for name,data in payloads.items():
        target=destination/PurePosixPath(name)
        assert target.absolute().is_relative_to(destination)
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream: stream.write(data)
        protect(target)
    return {**result,'restored_to_new_tree':True,'files_restored':len(payloads)}
