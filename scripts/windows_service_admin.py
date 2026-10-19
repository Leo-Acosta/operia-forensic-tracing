"""Elevated deployment checks and quiesced encrypted recovery; no secret output."""
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

from operia.security.service_control import load, verify_tree, RELEASE, environment
from operia.forensic_engine.canonical import read_json
from operia.security.private_files import no_links, protect


def run(root, action, release_id=None):
    root,config,current,release=load(root,verify=False)
    if action=='verify':
        if not release_id or not RELEASE.fullmatch(release_id): raise RuntimeError('service_release_id_rejected')
        candidate=no_links(root/'releases'/release_id)
        layout=read_json((candidate/'layout.json').read_bytes(),limit=2*1024*1024)
        runtime=read_json((candidate/'runtime-manifest.json').read_bytes(),limit=4*1024*1024)
        if layout.get('schema')!='operia-service-staging/1' or runtime.get('schema')!='operia-service-runtime/1':
            raise RuntimeError('service_release_manifest_rejected')
        verify_tree(candidate/'code',layout['code_files']); verify_tree(candidate/'runtime',runtime['files'])
        return {'release_verified':True,'code_files':len(layout['code_files']),'runtime_files':len(runtime['files'])}
    os.environ.update(environment(root,config))
    if action=='prepare':
        from operia.security.sandbox_runtime import prepare
        from operia.static_lab.runtime import prepare as lab
        prepare(); lab()
        return {'isolated_runtimes_prepared':True}
    if action=='backup':
        from operia.security.recovery_bundle import create, verify
        destination=root/'backups'/('update-'+uuid.uuid4().hex+'.dpapi')
        # The service key ACL necessarily grants the service SID read access. Copy
        # into admin-only scratch for the existing stricter private-key validator.
        # Caller has stopped SCM/writers; never expose the key in stdout or argv.
        with tempfile.TemporaryDirectory(prefix='key-',dir=root/'management') as directory:
            scratch=Path(directory); protect(scratch)
            key=scratch/'key'; key.write_bytes((root/'secrets/synthetic-signing-key.bin').read_bytes()); protect(key)
            create(root/'data',root/'data/storage',root/'data/storage/e7-service-validation.db',destination,key,quiesced=True)
        return verify(destination)
    raise RuntimeError('service_admin_action_rejected')


if __name__=='__main__':
    try: print(json.dumps(run(Path(sys.argv[1]),sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)))
    except Exception as error:
        print(str(error) if isinstance(error,RuntimeError) else type(error).__name__,file=sys.stderr)
        raise SystemExit(17)
