import os
import socket
import subprocess
import sys
import time
import httpx
import pytest


@pytest.fixture(scope='module')
def native_http(tmp_path_factory):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    env=dict(os.environ,EKAS_NATIVE_STATE_DIR=str(tmp_path_factory.mktemp('client-http')),EKAS_NATIVE_TOKENS='{}')
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','ekas_press_intelligence.native.api:create_native_app','--factory','--host','127.0.0.1','--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if proc.poll() is not None:raise RuntimeError(proc.stderr.read().decode())
            try:
                if httpx.get(base+'/v2/health').status_code==200:break
            except httpx.ConnectError:pass
            time.sleep(.1)
        else:raise AssertionError('Native HTTP service did not start')
        yield base
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()


def test_ekas_client_uses_separate_native_http_process(native_http):
    from ekas_press_intelligence.native.client import EKASNativeClient,NativeAPIError
    with EKASNativeClient(native_http) as client:
        assert len(client.capabilities()['plants'])==2
        assert client.datasets()[0]['id']=='historianrca'
        info=client.dataset('historianrca');assert len(info['tags'])==90
        assert client.samples('historianrca',['TIC-101.PV'],max_points=3)['rows']
        job=client.submit_job('describe_process',{'plant':'heated_stirred_tank'})
        result=client.wait_for_job(job['id'],timeout=30)
        assert result['state']=='succeeded' and 'TK-101' in result['result']['text']
        files=client.http.get('/v2/jobs/'+job['id']+'/files').json()['files']
        assert files[0]['name']=='PROCESS_DESCRIPTION.md'
        assert 'TK-101' in client.http.get('/v2/jobs/'+job['id']+'/files/PROCESS_DESCRIPTION.md').text
        with pytest.raises(NativeAPIError) as error:client.score('historianrca')
        assert error.value.code=='EXTERNAL_SCORING_REQUIRED'


def test_client_does_not_send_credentials_over_remote_plain_http():
    from ekas_press_intelligence.native.client import EKASNativeClient
    with pytest.raises(ValueError):EKASNativeClient('http://untrusted.example',token='secret')
