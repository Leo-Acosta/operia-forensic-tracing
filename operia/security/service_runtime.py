"""Offline installation from the operator's installed, pinned dependency closure.

Hashes detect changes relative to installed RECORD metadata; they do not certify
upstream authenticity. Runtime output is new and is protected separately by admin.
"""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import io
import json
import os
from pathlib import Path
import shutil
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from operia.security.private_files import no_links


def resolve_dependencies(lines, available=None):
    available = list(metadata.distributions()) if available is None else available
    installed = {}
    for dist in available:
        name = canonicalize_name(dist.metadata['Name'])
        if name in installed:
            raise RuntimeError('service_duplicate_distribution')
        installed[name] = dist
    queue = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        req = Requirement(line)
        pins = list(req.specifier)
        if req.url or len(pins) != 1 or pins[0].operator != '==' or '*' in pins[0].version:
            raise RuntimeError('service_direct_dependency_not_pinned')
        queue.append(req)
    selected, evaluated = {}, {}
    while queue:
        req = queue.pop()
        name = canonicalize_name(req.name)
        if req.url or name not in installed or installed[name].version not in req.specifier:
            raise RuntimeError('service_dependency_missing_or_incompatible')
        dist = installed[name]
        extras = set(req.extras) | evaluated.get(name, set()) | {''}
        if name in evaluated and extras == evaluated[name]:
            continue
        selected[name], evaluated[name] = dist, extras
        for raw in dist.requires or []:
            child = Requirement(raw)
            if child.marker is None or any(child.marker.evaluate({'extra': extra}) for extra in extras):
                queue.append(child)
    if not selected:
        raise RuntimeError('service_dependencies_empty')
    return selected


def dependency_payload(selected):
    files = {}
    for name, dist in selected.items():
        site = no_links(dist.locate_file('')).resolve()
        record = dist.read_text('RECORD')
        if not record:
            raise RuntimeError('service_distribution_record_missing')
        # Distribution.files can omit absent files; parse the actual RECORD so
        # missing or hostile entries cannot silently disappear from validation.
        for entry, record_hash, record_size in csv.reader(io.StringIO(record)):
            path = no_links(dist.locate_file(entry))
            resolved = path.resolve()
            if not resolved.is_relative_to(site):
                # Console wrappers are unnecessary; launch modules with python -m.
                if resolved.parent == site.parent.parent / 'Scripts' and resolved.suffix in ('.exe', '.py'):
                    continue
                prefix = site.parent.parent
                if not any(resolved.is_relative_to(prefix / part) for part in ('share', 'include')):
                    raise RuntimeError('service_distribution_path_rejected')
                relative = resolved.relative_to(prefix)
            else:
                relative = Path('Lib/site-packages') / resolved.relative_to(site)
            if '__pycache__' in relative.parts or resolved.suffix == '.pyc':
                continue
            if resolved.suffix.lower() == '.pth' or path.stat().st_nlink != 1:
                raise RuntimeError('service_distribution_startup_or_link_rejected')
            raw = path.read_bytes()
            if record_size and int(record_size) != len(raw):
                raise RuntimeError('service_distribution_record_hash_mismatch')
            if record_hash:
                expected = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
                if record_hash != 'sha256=' + expected:
                    raise RuntimeError('service_distribution_record_hash_mismatch')
            elif not (relative.parent.name.endswith('.dist-info') and relative.name == 'RECORD'):
                raise RuntimeError('service_distribution_unsigned_file')
            target = relative.as_posix()
            if target.casefold() in files:
                if files[target.casefold()][1] != raw:
                    raise RuntimeError('service_distribution_file_collision')
            files[target.casefold()] = (target, raw)
    return files


def install(root, requirements, base=None):
    if os.name != 'nt' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('service_runtime_requires_windows_python312')
    root = no_links(root)
    target = no_links(root / 'runtime')
    if not target.is_dir() or any(target.iterdir()):
        raise RuntimeError('service_runtime_requires_empty_destination')
    layout = json.loads((root / 'layout.json').read_text(encoding='utf-8'))
    if layout.get('schema') != 'operia-service-staging/1':
        raise RuntimeError('service_staging_invalid')
    if Path(requirements).read_bytes() != (root / 'code/requirements.txt').read_bytes():
        raise RuntimeError('service_requirements_snapshot_mismatch')
    selected = resolve_dependencies(Path(requirements).read_text().splitlines())
    payload = dependency_payload(selected)  # Validate every selected RECORD first.
    base = no_links(base or sys.base_prefix)
    sources = [base / 'python.exe', base / 'LICENSE.txt', *base.glob('*.dll')]
    excluded = {'site-packages','__pycache__','test','tests','ensurepip','idlelib','tkinter','venv'}
    for directory in ('DLLs', 'Lib'):
        for parent, directories, names in os.walk(base / directory):
            directories[:] = [d for d in directories if d not in excluded]
            for name in directories:
                no_links(Path(parent) / name)
            sources.extend(Path(parent) / name for name in names if not name.endswith('.pyc'))
    for path in sources:
        no_links(path)
        if not path.is_file() or path.stat().st_nlink != 1:
            raise RuntimeError('service_python_source_rejected')
    for path in sources:
        destination = target / path.relative_to(base)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    for relative, raw in payload.values():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    # Isolated search path: no user site, inherited PYTHONPATH or user .pth files.
    (target / 'python312._pth').write_text('Lib\nDLLs\nLib/site-packages\n../code\n', encoding='ascii')
    files = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(target.rglob('*')) if p.is_file()}
    manifest = {'schema': 'operia-service-runtime/1', 'python_version': sys.version,
                'source': 'offline-installed-record-verified-closure',
                'packages': {name: d.version for name, d in sorted(selected.items())}, 'files': files}
    (root / 'runtime-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    layout['runtime_installed'] = True
    (root / 'layout.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')
    return {'packages': len(selected), 'files': len(files), 'python': sys.version.split()[0]}
