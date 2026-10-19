import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

import pytest
from operia.security.service_staging import stage


def source_tree(tmp_path):
    source = tmp_path / 'source'
    (source / 'operia/core').mkdir(parents=True)
    (source / 'operia/core/config.py').write_text('# code')
    (source / 'operia/__pycache__').mkdir()
    (source / 'operia/__pycache__/bad.py').write_text('# excluded')
    for name in ('apps/api', 'migrations', 'scripts'):
        (source / name).mkdir(parents=True)
    (source / '.env').write_text('SENSITIVE')
    (source / 'operia/key.bin').write_bytes(b'SENSITIVE')
    (source / 'storage').mkdir()
    (source / 'storage/historical.db').write_bytes(b'SENSITIVE')
    return source


def test_staging_excludes_data_secrets_and_cache_without_touching_source(tmp_path):
    source = source_tree(tmp_path)
    result = stage(source, tmp_path / 'stage')
    assert result['code_files'] == 2
    assert (source / 'storage/historical.db').read_bytes() == b'SENSITIVE'
    layout = json.loads((tmp_path / 'stage/layout.json').read_text())
    assert layout['operational_secret_copied'] is False
    assert set(layout['code_files']) == {'operia/core/config.py', 'readonly-canary.txt'}
    assert not list((tmp_path / 'stage/data').rglob('*.db'))
    with pytest.raises(RuntimeError, match='destination_exists'):
        stage(source, tmp_path / 'stage')


def test_staging_rejects_overlapping_code_and_link_before_output(tmp_path):
    source = source_tree(tmp_path)
    with pytest.raises(RuntimeError, match='overlaps_code'):
        stage(source, source / 'operia/deployment')
    os.link(source / 'operia/core/config.py', source / 'operia/linked.py')
    with pytest.raises(RuntimeError, match='source_file_rejected'):
        stage(source, tmp_path / 'rejected')
    assert not (tmp_path / 'rejected').exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows operator preparation')
def test_powershell_plan_and_tamper_rejection_without_creating_account(tmp_path):
    source = source_tree(tmp_path)
    destination = tmp_path / 'stage'
    stage(source, destination)
    script = Path(__file__).resolve().parents[1] / 'scripts/prepare-service-account.ps1'
    command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(script), '-DeploymentRoot', str(destination)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['final_account_state'] == 'disabled'
    validated = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-File', str(script),
                                '-DeploymentRoot', str(destination), '-ValidateModule'],
                               capture_output=True, text=True, timeout=45)
    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)['localaccounts_module_validated'] is True
    (destination / 'code/operia/core/config.py').write_text('tampered')
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert result.returncode != 0 and 'service_code_hash_mismatch' in result.stderr


def test_worker_runtimes_follow_external_storage_in_fresh_process(tmp_path):
    env = {**os.environ, 'OPERIA_STORAGE_DIR': str(tmp_path / 'data/storage')}
    code = ('from operia.security.sandbox_runtime import DEFAULT_ROOT as a; '
            'from operia.static_lab.runtime import DEFAULT_ROOT as b; print(a); print(b)')
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [str(tmp_path / 'data/storage/sandbox-runtime'), str(tmp_path / 'data/storage/static-lab-runtime')]
