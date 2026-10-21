"""Deterministic TLS gateway configuration; no credentials or data are copied."""
import ipaddress
from pathlib import Path
import re

from operia.security.private_files import no_links


def quoted_path(value):
    path = no_links(value).resolve(strict=True)
    if any(c in str(path) for c in ('"', '\n', '\r', '{', '}', '`')):
        raise ValueError('gateway_path_rejected')
    return '"' + path.as_posix() + '"'


def render(*, hostname, certificate, private_key, bind='127.0.0.1', port=8443,
           upstream_port=8020, web_root=None):
    if not isinstance(hostname, str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', hostname):
        raise ValueError('gateway_hostname_rejected')
    if any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in hostname.split('.')):
        raise ValueError('gateway_hostname_rejected')
    address = ipaddress.ip_address(bind)
    if address.version != 4 or address.is_unspecified or address.is_multicast:
        raise ValueError('gateway_explicit_ipv4_required')
    if (type(port) is not int or not (port == 443 or 1024 <= port <= 65535)
        or type(upstream_port) is not int or not 1024 <= upstream_port <= 65535 or port == upstream_port):
        raise ValueError('gateway_port_rejected')
    cert, key = quoted_path(certificate), quoted_path(private_key)
    if not Path(certificate).is_file() or not Path(private_key).is_file():
        raise ValueError('gateway_certificate_files_required')
    if any(Path(p).stat().st_nlink != 1 for p in (certificate, private_key)):
        raise ValueError('gateway_certificate_hardlink_rejected')
    frontend = 'respond "Frontend not provisioned" 503'
    if web_root is not None:
        root = no_links(web_root).resolve(strict=True)
        # Only a compiled SPA, never the repository or evidence tree.
        if root.name != 'dist' or not (root/'index.html').is_file():
            raise ValueError('gateway_compiled_frontend_required')
        for path in root.rglob('*'):
            no_links(path)
            if path.is_file() and (path.stat().st_nlink != 1 or path.suffix in ('.db', '.pem', '.key', '.py', '.ps1') or path.name.startswith('.env')):
                raise ValueError('gateway_frontend_file_rejected')
        frontend = f'root * {quoted_path(root)}\n        try_files {{path}} /index.html\n        file_server'
    return f'''{{
    admin off
    persist_config off
    auto_https off
    servers {{
        protocols h1 h2
        strict_sni_host on
        max_header_size 32KB
        timeouts {{
            read_header 10s
            read_body 20s
            write 120s
            idle 30s
        }}
    }}
}}
https://{hostname}:{port} {{
    bind {address}
    tls {cert} {key} {{
        protocols tls1.2 tls1.3
    }}
    header {{
        -Server
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer
        X-Frame-Options SAMEORIGIN
        Cache-Control no-store
    }}
    request_body {{
        max_size 8MB
    }}
    @api path /api /api/*
    handle @api {{
        reverse_proxy 127.0.0.1:{upstream_port} {{
            header_up Host 127.0.0.1:{upstream_port}
            header_up -Forwarded
            header_up -X-Forwarded-For
            header_up -X-Forwarded-Host
            header_up -X-Forwarded-Proto
            header_up -X-Real-IP
            transport http {{
                dial_timeout 3s
                response_header_timeout 90s
            }}
        }}
    }}
    handle {{
        {frontend}
    }}
}}
'''
