"""Prepare a fresh code/data layout; never copy live evidence, DBs or secrets."""
from pathlib import Path
import hashlib
import json
import shutil

from operia.security.private_files import no_links, protect

TREES = ('operia', 'apps/api', 'migrations', 'scripts')
FILES = ('apps/__init__.py', 'alembic.ini', 'requirements.txt', '.env.production.example')


def stage(source, destination):
    source, destination = map(no_links, (source, destination))
    if destination.exists():
        raise RuntimeError('service_destination_exists')
    if source == destination or any(destination.is_relative_to(source / tree) for tree in TREES):
        raise RuntimeError('service_destination_overlaps_code')
    selected = []
    for tree in TREES:
        directory = no_links(source / tree)
        for path in directory.rglob('*'):
            no_links(path)
            if path.is_file() and path.suffix in ('.py', '.ps1') and '__pycache__' not in path.parts:
                selected.append(path)
    selected.extend(source / name for name in FILES if (source / name).is_file())
    # Complete validation before creating an output tree.
    for path in selected:
        no_links(path)
        if path.stat().st_nlink != 1 or path.stat().st_size > 8 * 1024 * 1024:
            raise RuntimeError('service_source_file_rejected')
    if not (source / 'operia/core/config.py') in selected:
        raise RuntimeError('service_source_invalid')
    destination.mkdir(parents=True, exist_ok=False)
    protect(destination)
    manifest = {}
    for path in sorted(selected):
        name = path.relative_to(source).as_posix()
        target = destination / 'code' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        manifest[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    for name in ('storage/evidence', 'storage/uploads', 'storage/exports', 'storage/maps',
                 'storage/temp', 'memory_vault', 'logs', 'temp'):
        (destination / 'data' / name).mkdir(parents=True, exist_ok=True)
    for name in ('secrets', 'runtime'):
        (destination / name).mkdir()
    # Synthetic canary only: no operational signing key or historical data.
    (destination / 'code/readonly-canary.txt').write_text('OPERIA ACL canary\n', encoding='ascii')
    manifest['readonly-canary.txt'] = hashlib.sha256((destination / 'code/readonly-canary.txt').read_bytes()).hexdigest()
    layout = {'schema': 'operia-service-staging/1', 'code_files': manifest,
              'live_data_copied': False, 'operational_secret_copied': False,
              'runtime_installed': False, 'service_activated': False}
    (destination / 'layout.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')
    return {'schema': layout['schema'], 'code_files': len(manifest), 'service_activated': False}
