"""Actual HTTPS client boundary with a private CA and independent role tokens."""
import os
import socket
import subprocess
import sys
import time
import httpx
import pytest


def test_verified_https_and_server_roles_without_disabling_certificate_checks(tmp_path,monkeypatch):
    from ekas_press_intelligence.native.client import EKASNativeClient,NativeAPIError
    cert=tmp_path/'localhost.pem';key=tmp_path/'localhost.key'
    subprocess.run(['/usr/bin/openssl','req','-x509','-newkey','rsa:2048','-nodes',
        '-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost',
        '-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'],check=True,capture_output=True)
    key.chmod(0o600)
    with socket.socket() as connection:connection.bind(('127.0.0.1',0));port=connection.getsockname()[1]
    env=dict(os.environ,EKAS_NATIVE_STATE_DIR=str(tmp_path/'state'),EKAS_NATIVE_LOCAL_ONLY='0',
             EKAS_NATIVE_TOKENS='{"qualification-analyst":"analyst","qualification-admin":"admin"}')
    process=subprocess.Popen([sys.executable,'-m','uvicorn','ekas_press_intelligence.native.api:create_native_app',
        '--factory','--host','127.0.0.1','--port',str(port),'--ssl-certfile',str(cert),'--ssl-keyfile',str(key)],
        env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'https://localhost:{port}'
    try:
        import ssl
        context=ssl.create_default_context(cafile=str(cert))
        for _ in range(150):
            if process.poll() is not None:raise AssertionError(process.stderr.read().decode())
            try:
                if httpx.get(base+'/v2/health',verify=context,headers={'Authorization':'Bearer qualification-analyst'}).status_code==200:break
            except httpx.ConnectError:pass
            time.sleep(.1)
        else:raise AssertionError('TLS service did not start')
        # Untrusted self-signed certificate is rejected by the actual client.
        monkeypatch.delenv('SSL_CERT_FILE',raising=False)
        monkeypatch.delenv('SSL_CERT_DIR',raising=False)
        with EKASNativeClient(base,token='qualification-analyst') as client:
            with pytest.raises(NativeAPIError) as failed:client.health()
            assert failed.value.code=='SERVICE_UNAVAILABLE'
        # Explicit CA trust enables HTTPS; it does not grant administrator rights.
        monkeypatch.setenv('SSL_CERT_FILE',str(cert))
        with EKASNativeClient(base,token='qualification-analyst') as client:
            assert client.health()['status']=='ok'
            assert client.dataset('historianrca')['rows']==5650781
            with pytest.raises(NativeAPIError) as denied:client.submit_job('generate',{})
            assert denied.value.code=='ROLE_FORBIDDEN'
        with EKASNativeClient(base) as client:
            with pytest.raises(NativeAPIError) as denied:client.health()
            assert denied.value.status==401
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
