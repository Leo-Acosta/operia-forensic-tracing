import http.client
import os
from pathlib import Path
import socket
import ssl
import subprocess
import threading
import time

import pytest
import uvicorn

from operia.security.ingress import render


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_reject_gateway_injection_and_wildcard(tmp_path):
    cert=tmp_path/'cert'; cert.write_text('synthetic')
    kwargs=dict(hostname='localhost',certificate=cert,private_key=cert)
    for hostname in ('*.example.org','ok\nadmin on','a..b','-host','host:443'):
        with pytest.raises(ValueError): render(**{**kwargs,'hostname':hostname})
    for bind in ('0.0.0.0','::','example.org'):
        with pytest.raises(ValueError): render(**kwargs,bind=bind)
    with pytest.raises(ValueError): render(**kwargs,web_root=tmp_path)
    with pytest.raises(ValueError): render(**kwargs,port=8020)


def test_production_host_validation(monkeypatch):
    from operia.core.config import settings
    from apps.api.main import create_app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(settings,'env','production')
    monkeypatch.setattr(settings,'cors_origins',['https://operia.example.invalid'])
    # No startup/database operations needed to test the outer host boundary.
    client=TestClient(create_app())
    assert client.get('/',headers={'Host':'attacker.invalid','X-Forwarded-Host':'operia.example.invalid'}).status_code==400
    assert client.get('/',headers={'Host':'127.0.0.1'}).status_code==200


def test_gateway_rejects_sensitive_frontend_and_linked_key(tmp_path):
    cert=tmp_path/'cert'; cert.write_text('synthetic')
    key=tmp_path/'key'; key.write_text('synthetic')
    dist=tmp_path/'dist'; dist.mkdir(); (dist/'index.html').write_text('synthetic frontend')
    (dist/'.env').write_text('synthetic secret marker')
    kwargs=dict(hostname='localhost',certificate=cert,private_key=key)
    with pytest.raises(ValueError,match='frontend_file_rejected'): render(**kwargs,web_root=dist)
    alias=tmp_path/'alias'; os.link(key,alias)
    with pytest.raises(ValueError,match='hardlink_rejected'): render(**kwargs)


def test_gateway_runner_rejects_modified_binary_before_start(tmp_path,monkeypatch):
    from scripts import run_https_gateway as runner
    binary=tmp_path/'caddy.exe'; binary.write_bytes(b'tampered gateway')
    monkeypatch.setattr(runner,'token_info',lambda:dict(elevated=False,system=False,administrator_member=False))
    monkeypatch.setattr('sys.argv',['gateway','--caddy',str(binary),'--config',str(tmp_path/'absent'),'--state-dir',str(tmp_path/'state')])
    with pytest.raises(RuntimeError,match='binary_integrity_failed'): runner.main()


@pytest.mark.skipif(not os.environ.get('OPERIA_TEST_CADDY'),reason='explicit real Caddy binary required')
@pytest.mark.parametrize('with_frontend',[False,True])
def test_real_tls_proxy_to_isolated_api(client,admin_headers,tmp_path,with_frontend):
    from apps.api.main import app
    caddy=Path(os.environ['OPERIA_TEST_CADDY']).resolve(strict=True)
    cert,key=tmp_path/'cert.pem',tmp_path/'key.pem'
    openssl_config=tmp_path/'openssl.cnf'
    openssl_config.write_text('[req]\ndistinguished_name=dn\n[dn]\n')
    subprocess.run(['openssl','req','-config',str(openssl_config),'-x509','-newkey','rsa:2048','-nodes','-days','1',
                    '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost',
                    '-keyout',str(key),'-out',str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    backend,port=free_port(),free_port()
    listener=socket.socket(); listener.bind(('127.0.0.1',backend))
    server=uvicorn.Server(uvicorn.Config(app,lifespan='off',proxy_headers=False,access_log=False,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True)
    thread.start()
    config=tmp_path/'Caddyfile'
    dist=None
    if with_frontend:
        dist=tmp_path/'dist'; dist.mkdir(); (dist/'index.html').write_text('synthetic compiled SPA')
    config.write_text(render(hostname='localhost',certificate=cert,private_key=key,port=port,upstream_port=backend,web_root=dist))
    subprocess.run([str(caddy),'validate','--config',str(config),'--adapter','caddyfile'],check=True,capture_output=True)
    log=(tmp_path/'proxy.log').open('wb')
    proxy=None
    environment={**os.environ,'XDG_DATA_HOME':str(tmp_path/'data'),'XDG_CONFIG_HOME':str(tmp_path/'config')}
    try:
        proxy=subprocess.Popen([str(caddy),'run','--config',str(config),'--adapter','caddyfile'],env=environment,stdout=log,stderr=log)
        context=ssl.create_default_context(cafile=str(cert))
        def request(path,headers=None,context=context):
            connection=http.client.HTTPSConnection('localhost',port,context=context,timeout=10)
            try:
                connection.request('GET',path,headers=headers or {})
                response=connection.getresponse()
                return response.status,dict(response.getheaders()),response.read()
            finally: connection.close()
        deadline=time.monotonic()+15
        while True:
            try:
                status,headers,body=request('/api/health')
                assert status==200
                break
            except (OSError,AssertionError):
                if time.monotonic()>deadline: raise
                time.sleep(.1)
        assert 'max-age' in headers['Strict-Transport-Security']
        assert 'Server' not in headers
        assert request('/api/cases')[0]==401
        assert request('/api/cases',admin_headers)[0]==200
        assert request('/api/cases',{'X-Forwarded-For':'127.0.0.1','X-Forwarded-Proto':'https','Forwarded':'for=127.0.0.1'})[0]==401
        if with_frontend:
            assert request('/')[2]==b'synthetic compiled SPA'
            assert request('/cases/synthetic-case')[2]==b'synthetic compiled SPA'
            assert request('/.env')[2]==b'synthetic compiled SPA'
            assert request('/storage/operia_forensic_tracing.db')[2]==b'synthetic compiled SPA'
        else:
            assert request('/.env')[0]==503
            assert request('/storage/operia_forensic_tracing.db')[0]==503
        assert request('/api/health',{'Host':'attacker.invalid'})[0] in (403,421)
        tls12=ssl.create_default_context(cafile=str(cert)); tls12.maximum_version=ssl.TLSVersion.TLSv1_2
        assert request('/api/health',context=tls12)[0]==200
        with pytest.raises(ssl.SSLCertVerificationError): request('/api/health',context=ssl.create_default_context())
        legacy=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); legacy.check_hostname=False; legacy.verify_mode=ssl.CERT_NONE
        legacy.maximum_version=ssl.TLSVersion.TLSv1_1
        legacy.minimum_version=ssl.TLSVersion.TLSv1
        legacy.set_ciphers('DEFAULT:@SECLEVEL=0')
        with pytest.raises(ssl.SSLError): request('/api/health',context=legacy)
        plain=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        try:
            plain.request('GET','/api/health')
            assert plain.getresponse().status!=200
        finally: plain.close()
        # Kernel-level binding: the API must be unreachable through this host's LAN address.
        for address in set(socket.gethostbyname_ex(socket.gethostname())[2]):
            if not address.startswith('127.'):
                with pytest.raises(OSError): socket.create_connection((address,backend),timeout=1)
    finally:
        if proxy is not None:
            proxy.terminate(); proxy.wait(timeout=10)
        log.close(); server.should_exit=True; thread.join(timeout=10); listener.close()
