"""Generate and validate a new Caddyfile without starting a network listener."""
import argparse
from pathlib import Path
import subprocess

from operia.security.ingress import render
from operia.security.private_files import no_links, protect, assert_private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('hostname', 'certificate', 'private-key', 'output', 'caddy'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--upstream-port', type=int, default=8020)
    parser.add_argument('--web-root')
    args = parser.parse_args()
    key=no_links(args.private_key)
    assert_private(key)
    assert_private(key.parent)
    config = render(hostname=args.hostname, certificate=args.certificate, private_key=args.private_key,
                    bind=args.bind, port=args.port, upstream_port=args.upstream_port, web_root=args.web_root)
    output = no_links(args.output)
    if not output.parent.is_dir(): raise RuntimeError('gateway_private_parent_required')
    assert_private(output.parent)
    with output.open('x', encoding='utf-8') as file: file.write(config)
    protect(output)
    subprocess.run([str(no_links(args.caddy).resolve(strict=True)), 'validate', '--config', str(output), '--adapter', 'caddyfile'], check=True)


if __name__ == '__main__': main()
