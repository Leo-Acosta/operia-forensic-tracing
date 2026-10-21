"""Run the pinned gateway without administrative privileges or API control port."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

from operia.security.private_files import assert_private, no_links, token_info

EXECUTABLE_SHA256='5f93a9bd555f3aac9d33af2756ba14b3519d8cca4ffd55256bdaeab444c9db2a'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caddy',required=True)
    parser.add_argument('--config',required=True)
    parser.add_argument('--state-dir',required=True)
    args=parser.parse_args()
    identity=token_info()
    if any(identity[k] for k in ('elevated','system','administrator_member')):
        raise RuntimeError('gateway_unprivileged_account_required')
    executable=no_links(args.caddy).resolve(strict=True)
    if executable.stat().st_nlink!=1 or hashlib.sha256(executable.read_bytes()).hexdigest()!=EXECUTABLE_SHA256:
        raise RuntimeError('gateway_binary_integrity_failed')
    config=no_links(args.config).resolve(strict=True)
    assert_private(config); assert_private(config.parent)
    state=no_links(args.state_dir).resolve(strict=True)
    assert_private(state)
    # Fresh private state directory; never use the application's writable storage.
    if state==config.parent or state.is_relative_to(config.parent):
        raise RuntimeError('gateway_separate_state_directory_required')
    environment={k:os.environ[k] for k in ('SystemRoot','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA') if k in os.environ}
    environment.update(XDG_DATA_HOME=str(state/'data'),XDG_CONFIG_HOME=str(state/'config'))
    subprocess.run([str(executable),'validate','--config',str(config),'--adapter','caddyfile'],env=environment,check=True)
    subprocess.run([str(executable),'run','--config',str(config),'--adapter','caddyfile'],env=environment,check=True)


if __name__=='__main__': main()
